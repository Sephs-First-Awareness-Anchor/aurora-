# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Phase R2 of the Semantic Plateau Remediation Directive (2026-07-15):
aurora_internal/aurora_correspondence_loop.py.

"The one experience class no simulation supplies: consequence from a
real mind." Aurora commits a structured prediction about what a reply
will look like BEFORE the reply exists; when Sunni replies (via
reply_aurora.py, asynchronously, on his own schedule), the gap between
prediction and reality becomes a real-entry experiential event -- scored
via the SAME _structured_mismatch machinery aurora_internal.dual_strata.
prediction_field.build_prediction_signal() already uses for live turns,
routed through the SAME re-entry loop (systems['noncomp_reflexive_
interpreter'].interpret()) every other user/response text already goes
through.

R2.5's own test list: retro-prediction impossible, hash verification at
resolution, expiry path produces unresolved with cost and no exception,
end-to-end synthetic message -> prediction -> reply -> PredictionSignal
-> re-entry event.
"""
import json
import time

import pytest

from aurora_internal.aurora_correspondence_loop import (
    MAX_PENDING,
    EXPIRY_SECONDS,
    GENESIS_PREV_HASH,
    CommittedPrediction,
    CorrespondenceCapReachedError,
    CorrespondenceChainFrozenError,
    RetroPredictionError,
    _PENDING_FILE,
    _append_jsonl,
    _canonical_json,
    _correspondence_dir,
    _load_pending_chain,
    _sha256,
    commit_prediction,
    count_active_pending,
    draft_correspondence_message,
    expire_stale_predictions,
    ingest_replies,
    pending_by_message_id,
    post_correspondence_message,
    verify_correspondence_loop,
)


def test_builtin_self_verification_all_pass():
    outcome = verify_correspondence_loop()
    failed = [c for c in outcome["checks"] if not c["passed"]]
    assert not failed, failed


def test_commit_prediction_chains_from_genesis(tmp_path):
    entry = commit_prediction("m1", topic="t", state_dir=tmp_path)
    assert entry.prev_hash == GENESIS_PREV_HASH
    assert entry.entry_hash == entry.recomputed_hash()


def test_commit_prediction_chains_to_previous_entry(tmp_path):
    e1 = commit_prediction("m1", state_dir=tmp_path)
    e2 = commit_prediction("m2", state_dir=tmp_path)
    assert e2.prev_hash == e1.entry_hash


def test_retro_prediction_is_impossible(tmp_path):
    """A reply must never be able to exist before its own prediction."""
    _append_jsonl(_correspondence_dir(tmp_path) / "from_sunni.jsonl", {
        "reply_to": "already_replied", "text": "yes", "time": time.time(),
    })
    with pytest.raises(RetroPredictionError):
        commit_prediction("already_replied", state_dir=tmp_path)
    # And nothing was persisted.
    entries, _frozen = _load_pending_chain(tmp_path)
    assert not any(e.message_id == "already_replied" for e in entries)


def test_cadence_cap_enforced(tmp_path):
    for i in range(MAX_PENDING):
        commit_prediction(f"m{i}", state_dir=tmp_path)
    assert count_active_pending(tmp_path) == MAX_PENDING
    with pytest.raises(CorrespondenceCapReachedError):
        commit_prediction("over_cap", state_dir=tmp_path)


def test_cadence_cap_frees_up_after_resolution(tmp_path):
    for i in range(MAX_PENDING):
        commit_prediction(f"m{i}", state_dir=tmp_path)
    _append_jsonl(_correspondence_dir(tmp_path) / "from_sunni.jsonl", {
        "reply_to": "m0", "text": "sounds good", "time": time.time(),
    })
    ingest_replies(systems={}, state_dir=tmp_path)
    assert count_active_pending(tmp_path) == MAX_PENDING - 1
    commit_prediction("newly_allowed", state_dir=tmp_path)  # must not raise


def test_hash_verification_at_resolution_time(tmp_path):
    commit_prediction("m1", topic="dinner", state_dir=tmp_path)
    # Tamper with the persisted chain after commit.
    chain_path = _correspondence_dir(tmp_path) / _PENDING_FILE
    entries = [json.loads(l) for l in chain_path.read_text(encoding="utf-8").splitlines()]
    entries[0]["topic"] = "tampered"  # entry_hash now stale for this content
    chain_path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

    _append_jsonl(_correspondence_dir(tmp_path) / "from_sunni.jsonl", {
        "reply_to": "m1", "text": "yes", "time": time.time(),
    })
    resolutions = ingest_replies(systems={}, state_dir=tmp_path)
    # Tampering freezes the whole chain on load -- nothing resolves.
    assert resolutions == []


def test_expiry_produces_unresolved_with_cost_and_no_exception(tmp_path):
    entry = commit_prediction("stale", state_dir=tmp_path)
    chain_path = _correspondence_dir(tmp_path) / _PENDING_FILE
    backdated = entry.to_dict()
    backdated["committed_at"] = time.time() - EXPIRY_SECONDS - 1
    payload = dict(backdated)
    payload.pop("entry_hash", None)
    backdated["entry_hash"] = _sha256(_canonical_json(payload))
    chain_path.write_text(json.dumps(backdated) + "\n", encoding="utf-8")

    expired = expire_stale_predictions(tmp_path)  # must not raise
    assert len(expired) == 1
    assert expired[0]["resolution"] == "unresolved"
    assert expired[0]["cost"] > 0
    assert expired[0]["message_id"] == "stale"


def test_expiry_ignores_predictions_still_within_window(tmp_path):
    commit_prediction("fresh", state_dir=tmp_path)
    assert expire_stale_predictions(tmp_path) == []


def test_expiry_ignores_already_resolved_predictions(tmp_path):
    entry = commit_prediction("m1", state_dir=tmp_path)
    chain_path = _correspondence_dir(tmp_path) / _PENDING_FILE
    backdated = entry.to_dict()
    backdated["committed_at"] = time.time() - EXPIRY_SECONDS - 1
    payload = dict(backdated)
    payload.pop("entry_hash", None)
    backdated["entry_hash"] = _sha256(_canonical_json(payload))
    chain_path.write_text(json.dumps(backdated) + "\n", encoding="utf-8")

    _append_jsonl(_correspondence_dir(tmp_path) / "from_sunni.jsonl", {
        "reply_to": "m1", "text": "answered anyway", "time": time.time(),
    })
    ingest_replies(systems={}, state_dir=tmp_path)
    assert expire_stale_predictions(tmp_path) == []


def test_corrupt_chain_line_freezes_rather_than_discards(tmp_path):
    commit_prediction("m1", state_dir=tmp_path)
    chain_path = _correspondence_dir(tmp_path) / _PENDING_FILE
    with open(chain_path, "a", encoding="utf-8") as f:
        f.write("this is not json\n")
    entries, frozen = _load_pending_chain(tmp_path)
    assert frozen is True
    assert len(entries) == 1  # the one good entry survives, not discarded


def test_commits_refused_while_chain_frozen(tmp_path):
    commit_prediction("m1", state_dir=tmp_path)
    chain_path = _correspondence_dir(tmp_path) / _PENDING_FILE
    with open(chain_path, "a", encoding="utf-8") as f:
        f.write("garbage\n")
    with pytest.raises(CorrespondenceChainFrozenError):
        commit_prediction("m2", state_dir=tmp_path)


def test_draft_never_fabricates_content_with_no_real_source():
    assert draft_correspondence_message({}) is None


def test_draft_uses_real_contradiction_ledger_content():
    class _Rec:
        claim_a = "the meeting is Tuesday"
        claim_b = "the meeting is Wednesday"

    class _Ledger:
        def unresolved(self):
            return [_Rec()]

    draft = draft_correspondence_message({"contradiction_ledger": _Ledger()})
    assert draft is not None
    assert "Tuesday" in draft["text"] and "Wednesday" in draft["text"]
    assert draft["intent_type"] == "clarification"


def test_end_to_end_message_prediction_reply_signal_reentry(tmp_path):
    """R2.5's end-to-end requirement: synthetic message -> prediction ->
    reply -> PredictionSignal -> re-entry event, using a real (fake)
    reflexive interpreter to confirm the re-entry call actually happens."""
    class _Rec:
        claim_a = "she is awake"
        claim_b = "she is asleep"

    class _Ledger:
        def unresolved(self):
            return [_Rec()]

    interpret_calls = []

    class _FakeInterpreter:
        def interpret(self, text):
            interpret_calls.append(text)
            class _US:
                reached_understanding = True
            return _US()

    axis_calls = []

    class _FakeIdentityField:
        def ingest_internal_signal(self, kind, magnitude, source_axis):
            axis_calls.append((kind, magnitude, source_axis))

    systems = {
        "contradiction_ledger": _Ledger(),
        "noncomp_reflexive_interpreter": _FakeInterpreter(),
        "identity_field": _FakeIdentityField(),
    }

    posted = post_correspondence_message(systems, state_dir=tmp_path)
    assert posted is not None
    message_id = posted["message_id"]
    assert pending_by_message_id(message_id, tmp_path) is not None

    _append_jsonl(_correspondence_dir(tmp_path) / "from_sunni.jsonl", {
        "reply_to": message_id, "text": "She's awake, just got up.", "time": time.time(),
    })

    resolutions = ingest_replies(systems, state_dir=tmp_path)
    assert len(resolutions) == 1
    assert resolutions[0]["message_id"] == message_id
    assert 0.0 <= resolutions[0]["mismatch"] <= 1.0

    # Re-entry actually happened through the standard interpreter call site.
    assert interpret_calls == ["She's awake, just got up."]
    # Axis pressure was fed somewhere (mismatch or match branch, either is fine).
    assert len(axis_calls) == 1
    assert axis_calls[0][2]  # source_axis non-empty


def test_ingest_replies_never_raises_on_malformed_inbound_entries(tmp_path):
    commit_prediction("m1", state_dir=tmp_path)
    _append_jsonl(_correspondence_dir(tmp_path) / "from_sunni.jsonl", {"garbage": True})
    resolutions = ingest_replies(systems={}, state_dir=tmp_path)  # must not raise
    assert resolutions == []


def test_post_correspondence_message_respects_cadence_cap(tmp_path):
    class _Rec:
        claim_a = "a"
        claim_b = "b"

    class _Ledger:
        def unresolved(self):
            return [_Rec()]

    systems = {"contradiction_ledger": _Ledger()}
    for _ in range(MAX_PENDING):
        posted = post_correspondence_message(systems, state_dir=tmp_path)
        assert posted is not None
    # Cap reached -- further posts return None rather than raising.
    assert post_correspondence_message(systems, state_dir=tmp_path) is None
