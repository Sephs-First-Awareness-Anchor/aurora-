# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Genealogy redistribution, Stage 2 step 1: the representation index only re-sorts what changed.

`_representation_index` was re-sorting EVERY bucket (68,670 key evaluations over 129 buckets per call on the
full profile) on every call whose stamp moved, i.e. nearly every observe.  It now re-sorts only the buckets in
which a member was added or a member's (last tick, count) changed.  A bucket's order is a pure function of its
members' activity and ids, so every other bucket is already in the order a full re-sort would give it.

This file holds the proof of that claim:
  * `_scratch` is the oracle: the index built from nothing for the state as it stands (a full rebuild).
  * `_legacy_index` is the previous implementation, kept here verbatim as the comparison baseline.
  * after every step of a mixed sequence (growth, reordered activity, new ids, an identity change) the new
    index equals the oracle, and so does the legacy one, and where the two loggers hold the same state the new
    index equals the legacy one.
"""
from __future__ import annotations

import os
import random
import sys
import tempfile
import types
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_evolution_stack import ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem  # noqa: E402
from aurora_internal.constraint_genealogy import PairStats  # noqa: E402


def _logger():
    return ConstraintGenealogyLogger(run_id="t", config=GenealogyConfig(), output_dir=tempfile.mkdtemp())


def _feed(g, n, seed=3, start=0, width=3):
    rng = random.Random(seed)
    base = {"X": 0.9, "T": 0.1, "N": 0.5, "B": 0.7, "A": 0.3}
    for i in range(start, start + n):
        b = {k: min(1.0, max(0.0, v + rng.uniform(-0.05, 0.05))) for k, v in base.items()}
        a = {k: max(0.0, v - 0.15) for k, v in b.items()}
        # the genealogy's own seed abilities, so the pairs they form are between ids that are INDEXED
        # (an id the genealogy does not hold is not eligible, and a bucket of unpaired ids cannot reorder)
        pool = sorted(g.abilities)
        trace = [TraceItem(kind="ABILITY", id=pool[(i * 3 + j * 5 + rng.randrange(4)) % len(pool)])
                 for j in range(1 + i % width)]
        g.observe(PressureVec(**b), trace, PressureVec(**a), notes={})


def _scratch(g) -> Dict[str, List[str]]:
    """The oracle: a full rebuild from nothing, for the state as it stands."""
    observed, activity = g._representation_observed_and_activity()
    index: Dict[str, List[str]] = defaultdict(list)
    for iid in sorted(observed):
        if g.representation_is_eligible(iid):
            index[g._collision_signature_for_item(iid)].append(iid)
    for bucket in index.values():
        bucket.sort(key=lambda iid: (-activity[iid][0], -activity[iid][1], iid))
    return {k: list(v) for k, v in index.items()}


def _legacy_index(self, active_ids: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """The implementation before Repair O, verbatim (it re-sorts every bucket on every rebuild)."""
    stamp = (
        len(self.links), len(self.abilities), len(self._pair_stats),
        self._representation_index_dirty_counter,
        self._representation_identity_dirty_counter,
    )
    if self._representation_index_stamp != stamp:
        prev_stamp = self._representation_index_stamp
        needs_full_rebuild = (
            prev_stamp is None
            or prev_stamp[4] != stamp[4]
            or stamp[0] < prev_stamp[0]
            or stamp[1] < prev_stamp[1]
            or stamp[2] < prev_stamp[2]
            or not self._representation_index_cache
        )
        observed_ids = set(self.links.keys()) | set(self.abilities.keys())
        activity: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
        for (left_id, right_id), pair_stats in self._pair_stats.items():
            observed_ids.add(str(left_id))
            observed_ids.add(str(right_id))
            for iid in (str(left_id), str(right_id)):
                prev_tick, prev_count = activity[iid]
                activity[iid] = (
                    max(int(prev_tick), int(pair_stats.last_seen_tick or 0)),
                    max(int(prev_count), int(pair_stats.count or 0)),
                )
        for iid, link in self.links.items():
            prev_tick, prev_count = activity[str(iid)]
            activity[str(iid)] = (
                max(int(prev_tick), int(link.created_at_tick or 0)),
                max(int(prev_count), int(link.count or 0)),
            )
        if needs_full_rebuild:
            scan_ids = sorted(observed_ids)
            index: Dict[str, List[str]] = defaultdict(list)
        else:
            scan_ids = sorted(observed_ids - self._representation_index_known_ids)
            index = defaultdict(list, {sig: list(ids) for sig, ids in self._representation_index_cache.items()})
        for iid in scan_ids:
            if self.representation_is_eligible(iid):
                index[self._collision_signature_for_item(iid)].append(iid)
        for bucket in index.values():
            bucket.sort(key=lambda iid: (-activity[iid][0], -activity[iid][1], iid))
        self._representation_index_cache = dict(index)
        self._representation_index_known_ids = set(observed_ids)
        self._representation_index_stamp = stamp
    index = {sig: list(ids) for sig, ids in self._representation_index_cache.items()}
    for iid in list(active_ids or []):
        iid = str(iid)
        if not self.representation_is_eligible(iid):
            continue
        sig = self._collision_signature_for_item(iid)
        bucket = index.setdefault(sig, [])
        if iid not in bucket:
            bucket.append(iid)
    return index


def _pair(g, a, b, count=1, tick=1):
    ps = PairStats(left_id=a, right_id=b)
    ps.count, ps.last_seen_tick = count, tick
    g._pair_stats[(a, b)] = ps



def _promote_last_active(g, per_bucket=1):
    """Make an indexed id in each bucket the most active one, by moving the pair records it is in -- the change a
    stale ordering would miss.  Returns how many ids were moved."""
    g._representation_index()
    in_pairs = defaultdict(list)
    for key in g._pair_stats:
        for x in key:
            in_pairs[str(x)].append(key)
    moved = 0
    for sig, ids in list(g._representation_index_cache.items()):
        cands = [i for i in reversed(ids) if i in in_pairs]
        for victim in cands[:per_bucket]:
            for key in in_pairs[victim]:
                g._pair_stats[key].last_seen_tick += 100000 + moved
                g._pair_stats[key].count += 100000
            moved += 1
    return moved


def _same(g):
    return {k: list(v) for k, v in g._representation_index().items()}


def _twin_pair():
    new, old = _logger(), _logger()
    old._representation_index = types.MethodType(_legacy_index, old)
    return new, old


def _check(new, old):
    assert _same(new) == _scratch(new), "change-aware index differs from a full rebuild"
    assert _same(old) == _scratch(old), "(the legacy implementation also agrees with the oracle)"
    if set(new.abilities) | set(new.links) == set(old.abilities) | set(old.links):
        assert _same(new) == _same(old), "change-aware index differs from the previous implementation"


# -- equivalence ----------------------------------------------------------------------------------------------

def test_growth_only_gives_the_same_index_as_a_full_rebuild_and_as_the_previous_code():
    new, old = _twin_pair()
    for step in range(6):
        for g in (new, old):
            _feed(g, 25, seed=step, start=step * 25)
        _check(new, old)


def test_changed_activity_reorders_exactly_the_buckets_a_full_rebuild_would():
    new, old = _twin_pair()
    for g in (new, old):
        _feed(g, 80)
    _check(new, old)
    for g in (new, old):
        assert _promote_last_active(g) >= 1                     # ids already indexed become the most active
        _pair(g, "__new_left", "__new_right", count=2, tick=999)      # the real stamp change: a new pair
    _check(new, old)
    assert new._representation_index_profile["resorted"] >= 1


def test_a_link_count_moving_with_a_stamp_change_reorders_like_a_full_rebuild():
    new, old = _twin_pair()
    for g in (new, old):
        _feed(g, 120, width=4)
    _check(new, old)
    for g in (new, old):
        for link in list(g.links.values())[:5]:
            link.count += 9
        _pair(g, "__a", "__b")
    _check(new, old)


def test_a_new_id_is_filed_in_order_among_existing_members():
    new, old = _twin_pair()
    for g in (new, old):
        _feed(g, 60)
    _check(new, old)
    for g in (new, old):
        _feed(g, 40, seed=7, start=60, width=5)       # new abilities, existing pairs seen again
    _check(new, old)


def test_an_identity_change_still_forces_a_full_rebuild():
    g = _logger()
    _feed(g, 60)
    _same(g)
    g._representation_index_stamp = g._representation_index_stamp          # unchanged: no rebuild
    g.mark_representation_identity_dirty()
    _same(g)
    assert g._representation_index_profile["mode"] == "full"
    assert _same(g) == _scratch(g)


def test_a_mixed_sequence_never_leaves_the_index_different_from_a_full_rebuild():
    rng = random.Random(11)
    new, old = _twin_pair()
    for g in (new, old):
        _feed(g, 80)                    # enough paired members per bucket for an order to be able to change
    seed = 0
    resorted_total = 0
    reordered = 0
    for step in range(30):
        cycle = ["grow", "bump", "pair", "bump", "link", "bump", "identity"]
        op = cycle[step % len(cycle)] if step < 14 else rng.choice(["grow", "bump", "pair", "identity", "link"])
        order_before = _scratch(new) if op == "bump" else None
        for g in (new, old):
            if op == "grow":
                _feed(g, 8, seed=seed, start=step * 8)
            elif op == "bump":
                _promote_last_active(g, per_bucket=2)
                _pair(g, f"__x{step}", f"__y{step}", count=step, tick=step)
            elif op == "pair":
                _pair(g, f"__p{step}", f"__q{step}", count=step % 5, tick=step * 2)
            elif op == "identity":
                g.mark_representation_identity_dirty()
            elif op == "link":
                for link in list(g.links.values())[::3]:
                    link.count += 1
                _pair(g, f"__l{step}", f"__m{step}")
        seed += 1
        if op == "bump":
            reordered += int(_scratch(new) != order_before)
        _check(new, old)
        resorted_total += new._representation_index_profile.get("resorted", 0)
    assert resorted_total > 0 and reordered > 0, "the sequence never moved an order, so it proved nothing"


# -- the point of it: it does less ------------------------------------------------------------------------------

def test_a_new_unrelated_pair_re_sorts_no_bucket():
    g = _logger()
    _feed(g, 120)
    _same(g)
    _pair(g, "__a", "__b", count=1, tick=1)               # ids the genealogy does not hold: not eligible, nothing indexed
    assert _same(g) == _scratch(g)
    prof = g._representation_index_profile
    assert prof["mode"] == "incremental" and prof["resorted"] == 0


def test_it_re_sorts_exactly_the_buckets_that_hold_an_id_whose_activity_moved():
    g = _logger()
    _feed(g, 200, width=4)
    _same(g)
    index = g._representation_index_cache
    assert len(index) >= 3, "the test needs several buckets"
    _, act_before = g._representation_observed_and_activity()
    act_before = dict(act_before)
    in_pairs = {str(x) for key in g._pair_stats for x in key}
    victim = next(i for ids in index.values() for i in ids if i in in_pairs)
    for (l, r), ps in g._pair_stats.items():
        if victim in (str(l), str(r)):
            ps.last_seen_tick += 100000
            ps.count += 100000
    _pair(g, "__a", "__b")
    _, act_after = g._representation_observed_and_activity()
    moved = {i for i in set(act_before) | set(act_after) if act_before.get(i, (0, 0)) != act_after.get(i, (0, 0))}
    expected = {g._representation_index_sig_of[i] for i in moved if i in g._representation_index_sig_of}
    assert victim in moved and expected
    assert _same(g) == _scratch(g)
    assert g._representation_index_profile["resorted"] == len(expected)
    assert len(expected) < len(g._representation_index_cache), "every bucket moved: this proves nothing about skipping"


def test_an_unchanged_stamp_does_no_work():
    g = _logger()
    _feed(g, 60)
    _same(g)
    prof = dict(g._representation_index_profile)
    _same(g)
    assert g._representation_index_profile == prof


def test_the_returned_index_is_a_copy_the_caller_may_change():
    g = _logger()
    _feed(g, 60)
    got = g._representation_index()
    for ids in got.values():
        ids.append("__scribble")
    got.clear()
    assert _same(g) == _scratch(g)
