# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The measuring instruments for the genealogy redistribution (PR #252 review).

Codex found two ways the Stage 1 baseline could mislead:
  * a read made BEFORE an observe in the same turn was counted as made after it (the turn's final call count
    was compared, not the revision at the read);
  * a collision-record-only change was reported as a change to abilities or links, i.e. to what live code reads.
Both are pinned here with harness cases, plus the content-versus-size distinction the diff mode now relies on.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


B = _load("baseline_genealogy")
A = _load("audit_genealogy")


class _G:
    def __init__(self, abilities=None, links=None, promoted=None, collisions=None):
        self.abilities = abilities if abilities is not None else {}
        self.links = links if links is not None else {}
        self.links_promoted = promoted if promoted is not None else {}
        self._representation_collisions = collisions if collisions is not None else {}


# -- ordering: the revision AT the read, not the turn's final call count -----------------------------------

def test_a_select_before_an_observe_in_the_same_turn_is_not_counted_as_after_it():
    # turn 0 starts at rev 0; she selects (rev 0), THEN observe runs (rev becomes 1)
    readers = [{"rev": 0, "in_turn": True, "turn": 0}]
    assert B.reads_after_same_turn_observe(readers, {0: 0}) == 0


def test_a_select_after_an_observe_in_the_same_turn_is_counted():
    readers = [{"rev": 0, "in_turn": True, "turn": 0}, {"rev": 1, "in_turn": True, "turn": 0}]
    assert B.reads_after_same_turn_observe(readers, {0: 0}) == 1


def test_an_observe_in_an_earlier_turn_does_not_make_a_later_turns_first_read_count():
    # turn 1 starts at rev 3 (three observes happened during turn 0): a read at rev 3 saw all of that, none "same turn"
    readers = [{"rev": 3, "in_turn": True, "turn": 1}, {"rev": 4, "in_turn": True, "turn": 1}]
    assert B.reads_after_same_turn_observe(readers, {0: 0, 1: 3}) == 1


def test_reads_outside_a_turn_are_not_counted():
    assert B.reads_after_same_turn_observe([{"rev": 9, "in_turn": False, "turn": 0}], {0: 0}) == 0


# -- what an observe call changed: kept apart --------------------------------------------------------------

def test_a_collision_only_change_is_not_a_change_to_what_live_code_reads():
    before = B.collect(_G(), deep=True)
    after = B.collect(_G(collisions={"RC:1": {"status": "unresolved"}}), deep=True)
    change = B.diff_state(before, after)
    assert B.touches_collisions(change) and not B.touches_live_reads(change)


def test_a_new_ability_is_a_change_to_what_live_code_reads():
    before = B.collect(_G(), deep=True)
    after = B.collect(_G(abilities={"a1": {"axis": "X"}}), deep=True)
    change = B.diff_state(before, after)
    assert B.touches_live_reads(change) and change["abilities_size"] == 1 and not B.touches_collisions(change)


def test_an_in_place_edit_with_no_size_change_is_seen_by_content_not_by_size():
    g1 = _G(abilities={"a1": {"axis": "X", "relief": 0.1}})
    g2 = _G(abilities={"a1": {"axis": "X", "relief": 0.2}})
    change = B.diff_state(B.collect(g1, deep=True), B.collect(g2, deep=True))
    assert change == {"abilities_content": True, "abilities_fields": {"relief": 1}}     # and WHICH field
    assert B.touches_live_reads(change)
    # shallow collection (timing mode) cannot see it, which is why timing mode makes no claim about state
    assert B.diff_state(B.collect(g1, deep=False), B.collect(g2, deep=False)) == {}


def test_nothing_changed_is_nothing_changed_whatever_the_key_order():
    a = _G(abilities={"a1": {"x": 1, "y": 2}, "a2": {"z": 3}})
    b = _G(abilities={"a2": {"z": 3}, "a1": {"y": 2, "x": 1}})
    assert B.diff_state(B.collect(a, deep=True), B.collect(b, deep=True)) == {}


def test_a_links_promoted_change_counts_as_live_state():
    change = B.diff_state(B.collect(_G(), deep=True), B.collect(_G(promoted={"p": 1}), deep=True))
    assert B.touches_live_reads(change)


# -- the audit: reads are found in the syntax tree, with the receiver ---------------------------------------

def test_the_audit_finds_getattr_string_reads_and_classifies_the_receiver(tmp_path, monkeypatch):
    mod = tmp_path / "consumer.py"
    mod.write_text(
        "def status(genealogy, other):\n"
        "    a = getattr(genealogy, 'abilities', {})\n"
        "    b = other.abilities\n"
        "    return a, b\n")
    monkeypatch.setattr(A, "ROOT", tmp_path)
    monkeypatch.setattr(A, "GEN", tmp_path / "constraint_genealogy.py")
    refs = A.outside_references({"abilities"}, set())["abilities"]
    by_via = {(r["via"], r["class"]) for r in refs}
    assert ("getattr", "named") in by_via and ("attribute", "unnamed") in by_via


def test_a_method_that_reaches_observe_is_the_write_path_not_a_consumer():
    import ast
    src = ("class G:\n"
           "    def observe(self): return self._observe_impl()\n"
           "    def _observe_impl(self): self.links = {}\n"
           "    def summary(self): return len(self.links)\n"
           "    def register_x(self): self.observe(); return len(self.links)\n")
    cls = ast.parse(src).body[0]
    facts = {n.name: A.method_facts(n) for n in cls.body}
    assert A.public_readers({"links"}, facts) == {"links": ["summary"]}


def test_a_frozen_record_replaced_with_one_field_changed_is_reported_by_field():
    import dataclasses

    @dataclasses.dataclass(frozen=True)
    class Ability:
        id: str
        axis: str
        consequence_profile: tuple = ()

    a = Ability("x", "X")
    g1, g2 = _G(abilities={"x": a}), _G(abilities={"x": dataclasses.replace(a, consequence_profile=(1, 2))})
    change = B.diff_state(B.collect(g1, deep=True), B.collect(g2, deep=True))
    assert change["abilities_fields"] == {"consequence_profile": 1} and "abilities_size" not in change
