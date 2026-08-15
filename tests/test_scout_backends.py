#!/usr/bin/env python3
"""
Regression coverage for aurora_internal/scouting/backends.py (Aurora
Build 694, step 7): the ScoutBackend abstraction that replaced the
Scout worker's hardcoded, Room-only, pgrep-dependent retrieval path.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.backends import (
    ScoutBackend,
    PoedexRoomBackend,
    LocalLessonsBackend,
    TestBackend,
    RemoteSearchBackend,
    RemoteModelBackend,
    resolve_backend_chain,
    DEFAULT_BACKEND_NAMES,
)
from aurora_internal.scouting.contracts import ScoutRequest


def test_poedex_room_backend_unavailable_when_no_room_process_exists(tmp_path):
    # No aurora_room.py process is running in this test environment --
    # this is the exact condition that makes the worker's OLD hardcoded
    # path structurally unusable on Android (pgrep can never find a
    # match there).
    backend = PoedexRoomBackend()
    assert backend.is_available() is False


def test_local_lessons_backend_is_always_available():
    # No pgrep, no second process, no network call -- a local file read
    # is always attemptable regardless of platform.
    backend = LocalLessonsBackend()
    assert backend.is_available() is True


def test_local_lessons_backend_returns_empty_when_no_lessons_file_exists(tmp_path):
    backend = LocalLessonsBackend()
    req = ScoutRequest(turn_id="t1", inquiry="what is a guitar chord")
    assert backend.retrieve(req, state_dir=tmp_path) == ""


def test_local_lessons_backend_finds_a_matching_bound_lesson(tmp_path):
    (tmp_path / "poedex_lessons.json").write_text(json.dumps([
        {"question": "what is a guitar chord", "lesson": "A guitar chord is three or more notes played together."},
    ]), encoding="utf-8")
    backend = LocalLessonsBackend()
    req = ScoutRequest(turn_id="t1", inquiry="what is a guitar chord")
    result = backend.retrieve(req, state_dir=tmp_path)
    assert "three or more notes" in result


def test_local_lessons_backend_matches_by_keyword_overlap_not_just_exact_text(tmp_path):
    (tmp_path / "poedex_lessons.json").write_text(json.dumps([
        {"question": "define chord theory basics", "lesson": "Chord theory studies how notes combine into harmony."},
    ]), encoding="utf-8")
    backend = LocalLessonsBackend()
    req = ScoutRequest(turn_id="t1", inquiry="chord theory basics explained")
    result = backend.retrieve(req, state_dir=tmp_path)
    assert "harmony" in result


def test_local_lessons_backend_ignores_short_low_value_lessons(tmp_path):
    (tmp_path / "poedex_lessons.json").write_text(json.dumps([
        {"question": "guitar chord", "lesson": "yes"},  # too short to be real evidence
    ]), encoding="utf-8")
    backend = LocalLessonsBackend()
    req = ScoutRequest(turn_id="t1", inquiry="guitar chord")
    assert backend.retrieve(req, state_dir=tmp_path) == ""


def test_test_backend_returns_its_canned_result_regardless_of_request(tmp_path):
    backend = TestBackend(canned_result="always this")
    req = ScoutRequest(turn_id="t1", inquiry="anything at all")
    assert backend.retrieve(req, state_dir=tmp_path) == "always this"
    assert backend.is_available() is True


def test_test_backend_can_be_constructed_as_unavailable(tmp_path):
    backend = TestBackend(canned_result="unreachable", available=False)
    assert backend.is_available() is False


def test_remote_search_backend_unavailable_when_unconfigured():
    backend = RemoteSearchBackend()  # no fetch_fn supplied
    assert backend.is_available() is False


def test_remote_search_backend_uses_operator_supplied_fetch_fn(tmp_path):
    def _fetch(inquiry):
        return f"result for: {inquiry}"
    backend = RemoteSearchBackend(fetch_fn=_fetch)
    assert backend.is_available() is True
    req = ScoutRequest(turn_id="t1", inquiry="test query")
    assert backend.retrieve(req, state_dir=tmp_path) == "result for: test query"


def test_remote_search_backend_degrades_honestly_on_fetch_fn_exception(tmp_path):
    def _broken_fetch(inquiry):
        raise RuntimeError("network failure")
    backend = RemoteSearchBackend(fetch_fn=_broken_fetch)
    req = ScoutRequest(turn_id="t1", inquiry="q")
    assert backend.retrieve(req, state_dir=tmp_path) == ""


def test_remote_model_backend_unavailable_when_unconfigured():
    backend = RemoteModelBackend()
    assert backend.is_available() is False


def test_remote_model_backend_uses_operator_supplied_query_fn(tmp_path):
    def _query(inquiry, interpreted_input):
        return f"{inquiry}|{interpreted_input}"
    backend = RemoteModelBackend(query_fn=_query)
    req = ScoutRequest(turn_id="t1", inquiry="q", interpreted_input="ctx")
    assert backend.retrieve(req, state_dir=tmp_path) == "q|ctx"


def test_no_backend_is_hardwired_to_a_specific_commercial_provider():
    # Spec section 7: "Do not hardcode a specific commercial provider
    # into Aurora's cognitive architecture." Neither remote backend
    # constructs a provider internally -- both require the operator to
    # supply the actual function, structurally (no default argument
    # pointing at any real endpoint).
    import inspect
    assert inspect.signature(RemoteSearchBackend.__init__).parameters["fetch_fn"].default is None
    assert inspect.signature(RemoteModelBackend.__init__).parameters["query_fn"].default is None


def test_resolve_backend_chain_default_is_android_capable_out_of_the_box():
    chain = resolve_backend_chain()
    names = [b.name for b in chain]
    assert names == list(DEFAULT_BACKEND_NAMES)
    # At least one backend in the default chain must be available with
    # zero external configuration and no Room process -- LocalLessonsBackend.
    assert any(b.is_available() for b in chain)


def test_resolve_backend_chain_respects_explicit_names():
    chain = resolve_backend_chain(["local_lessons"])
    assert len(chain) == 1
    assert isinstance(chain[0], LocalLessonsBackend)


def test_resolve_backend_chain_reads_env_var_when_names_not_supplied(monkeypatch):
    monkeypatch.setenv("SCOUT_BACKENDS", "local_lessons,test")
    chain = resolve_backend_chain()
    assert [b.name for b in chain] == ["local_lessons", "test"]


def test_resolve_backend_chain_skips_unknown_names_without_crashing():
    chain = resolve_backend_chain(["local_lessons", "not_a_real_backend", "test"])
    assert [b.name for b in chain] == ["local_lessons", "test"]


def test_scout_backend_base_class_methods_are_not_implemented():
    backend = ScoutBackend()
    import pytest
    with pytest.raises(NotImplementedError):
        backend.is_available()
    with pytest.raises(NotImplementedError):
        backend.retrieve(ScoutRequest(turn_id="t1"), state_dir="/tmp")
