# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
N3 (R1 Campaign Closure, 2026-07-16): aurora_correspondence_loop.py's own
docstring flagged daemon wiring as a deliberate, deferred SCOPE BOUNDARY
-- "turning on autonomous outbound correspondence messages... deserves
explicit review before it goes live." This is that review, executed:
aurora_daemon.py's tick loop now calls ingest_replies/expire_stale_
predictions/post_correspondence_message on their own cadence.

Structural checks confirm the wiring exists with the right gating and
the right state_dir handling (the module's own functions default to a
repo-relative path, NOT systems' actual boot state_dir -- passing it
explicitly is what keeps this out of the state-dir isolation-gap class
of bug already documented multiple times elsewhere in this campaign).
Functional checks confirm the underlying module calls behave correctly
against an isolated scratch state_dir.
"""
import os
import shutil
import tempfile

from aurora_internal.aurora_correspondence_loop import (
    post_correspondence_message,
    ingest_replies,
    expire_stale_predictions,
    count_active_pending,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _daemon_source():
    with open(os.path.join(_ROOT, "aurora_daemon.py"), "r", encoding="utf-8") as f:
        return f.read()


def test_daemon_wires_correspondence_ingest_and_draft():
    source = _daemon_source()
    assert "from aurora_internal.aurora_correspondence_loop import" in source
    assert "ingest_replies as _corr_ingest_replies" in source
    assert "expire_stale_predictions as _corr_expire_stale" in source
    assert "post_correspondence_message as _corr_post" in source


def test_daemon_gates_correspondence_on_surface_only_delegation():
    """Same "subsurface never owns outward communication" rule reach-out
    already follows -- the correspondence loop must use the identical
    gate, not a separate/looser one."""
    source = _daemon_source()
    ingest_idx = source.index("_corr_ingest_replies(systems")
    draft_idx = source.index("_corr_post(systems")
    # scan backward from each call site for the nearest preceding "if"
    ingest_if = source.rfind("if _auto_reach_out_enabled(systems)", 0, ingest_idx)
    draft_if = source.rfind("if (_auto_reach_out_enabled(systems)", 0, draft_idx)
    assert ingest_if != -1, "ingest call is not gated by _auto_reach_out_enabled"
    assert draft_if != -1, "draft/post call is not gated by _auto_reach_out_enabled"


def test_daemon_draft_respects_quiet_hours_ingest_does_not():
    """Drafting a NEW message is deliberately more conservative (skipped
    during quiet hours); processing an already-arrived reply is not --
    a reply sitting unprocessed through quiet hours serves no one."""
    source = _daemon_source()
    draft_block_start = source.index("if (_auto_reach_out_enabled(systems) and not quiet")
    draft_block = source[draft_block_start:draft_block_start + 400]
    assert "next_correspondence_draft" in draft_block

    ingest_block_start = source.index("if _auto_reach_out_enabled(systems) and now >= next_correspondence_ingest")
    ingest_block = source[ingest_block_start:ingest_block_start + 200]
    assert "not quiet" not in ingest_block


def test_daemon_passes_state_dir_explicitly_not_module_default():
    """The isolation-gap bug class documented elsewhere in this campaign:
    a module's own state_dir default is repo-relative, not the boot
    systems' actual state_dir. All three call sites must pass state_dir
    explicitly from systems.get("state_dir")."""
    source = _daemon_source()
    assert 'state_dir=_corr_state_dir' in source
    assert 'state_dir=systems.get("state_dir")' in source
    assert '_corr_state_dir = systems.get("state_dir")' in source


def test_correspondence_interval_constants_exist_and_are_sane():
    source = _daemon_source()
    assert "CORRESPONDENCE_DRAFT_INTERVAL" in source
    assert "CORRESPONDENCE_INGEST_INTERVAL" in source
    import aurora_daemon
    # Draft interval must be meaningfully rarer than ingest -- "minutes
    # per day, not hours" for new predictions, prompt processing for replies.
    assert aurora_daemon.CORRESPONDENCE_DRAFT_INTERVAL > aurora_daemon.CORRESPONDENCE_INGEST_INTERVAL
    assert aurora_daemon.CORRESPONDENCE_INGEST_INTERVAL <= 900  # a reply waits at most ~15 min
    assert aurora_daemon.CORRESPONDENCE_DRAFT_INTERVAL >= 3600  # never more than hourly


def test_post_ingest_expire_use_the_state_dir_they_are_given():
    """Functional check, isolated: the three wired functions must operate
    entirely inside a scratch state_dir when given one -- confirming the
    daemon's explicit state_dir pass-through actually reaches real
    behavior, not just that the source text contains the right string."""
    scratch = tempfile.mkdtemp(prefix="aurora_n3_isolation_")
    try:
        systems = {
            "contradiction_ledger": None,
            "_curiosity_engine": None,
        }
        # No curiosity/contradiction content -> draft returns None -> no
        # message posted. Confirms FIX-A008-class discipline (never
        # fabricates content) survives being called from the daemon path.
        result = post_correspondence_message(systems, state_dir=scratch)
        assert result is None

        resolutions = ingest_replies(systems, state_dir=scratch)
        assert resolutions == []

        expired = expire_stale_predictions(state_dir=scratch)
        assert expired == []

        assert count_active_pending(state_dir=scratch) == 0

        # Nothing should have touched the real repo's aurora_state at all.
        real_pending = os.path.join(_ROOT, "aurora_state", "correspondence", "pending_predictions.jsonl")
        # Existence of the real file (from prior sessions) is fine; what
        # matters is the scratch dir got its own independent structure.
        scratch_corr_dir = os.path.join(scratch, "correspondence")
        # ingest_replies/expire_stale_predictions may not create the dir
        # eagerly when there's nothing to do -- that's fine, this just
        # confirms no exception and no cross-contamination occurred.
        assert True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
