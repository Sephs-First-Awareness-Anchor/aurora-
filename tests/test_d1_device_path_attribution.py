# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive D1 (Device-Path Attribution, 2026-07-17): backward-attribution
proof for the device/app-delivered text, same standard as
test_governance_liveness.py::test_delivered_output_attribution_traces_to_
sentence_composer (which proves resp_B's attribution to SentenceComposer).

Trigger: post-campaign finding that live device/app-delivered text
diverges on every traced turn from the campaign-verified path (gateway ->
composer -> resp_B). This is the third attribution incident of this class
(boot-comment lie; probe-field near-miss) -- the governing rule is
backward-attribution: trace from the delivered artifact, never from
design intent or import graphs.

Delivery-surface enumeration rule (this directive's own registry
addition): attribution work must enumerate ALL user-facing delivery
surfaces and byte-attribute each -- verifying one surface says nothing
about its siblings. Two real device surfaces were traced:

  1. aurora_daemon.py's production entry (`return result.get("resp_A")`,
     ~line 5575) -- the embedded/hardware daemon path.
  2. flutter_app/android/app/src/main/python/aurora_bridge.py's
     handle_message() -- called by AuroraService.kt via Chaquopy for the
     Flutter mobile app. Traced further into the Dart layer
     (home_screen.dart's _sendMessage()): the SAME reply string is both
     rendered as a chat bubble AND passed verbatim to
     AuroraBridge.speak() -> 'speak' method channel -> nativeSpeak() ->
     Android TextToSpeech.speak() -- chat text and TTS voice are
     byte-identical on the Flutter side, no separate divergence there.

This file proves surface 2 (the one directly testable from this Python
test suite) byte-for-byte. Surface 1 (aurora_daemon.py) shares the
identical `result.get("resp_A")` extraction pattern -- confirmed by
direct source read, not separately live-traced here (out of this file's
scope; the daemon requires its own long-running process harness).
"""
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")


def _aurora_daemon_source():
    with open(os.path.join(REPO_ROOT, "aurora_daemon.py"), "r", encoding="utf-8") as f:
        return f.read()


def _aurora_bridge_source():
    with open(os.path.join(ANDROID_PY_DIR, "aurora_bridge.py"), "r", encoding="utf-8") as f:
        return f.read()


def test_aurora_daemon_production_entry_reads_resp_a():
    """Structural confirmation of surface 1 (embedded/hardware daemon).
    Unchanged since N4's pre-flight trace (2026-07-16); re-asserted here
    as part of D1's enumerated-surfaces requirement."""
    source = _aurora_daemon_source()
    assert 'return result.get("resp_A") if isinstance(result, dict) else None' in source


def test_aurora_bridge_extract_response_reads_resp_a():
    """Structural confirmation: the Flutter bridge's own extraction
    function reads result["resp_A"], not resp_B -- the same field the
    daemon reads. Both real device surfaces converge on resp_A."""
    source = _aurora_bridge_source()
    idx = source.index("def _extract_response(result) -> str:")
    body = source[idx:idx + 1000]
    assert 'result.get("resp_A")' in body
    assert 'getattr(resp_a, "content", None)' in body


def test_aurora_bridge_handle_message_calls_process_external_user_turn():
    source = _aurora_bridge_source()
    assert "_aurora.process_external_user_turn(" in source
    assert "response = _sanitize_response(_extract_response(result), text)" in source


def test_device_delivered_text_byte_attributes_to_resp_a_live():
    """Backward-attribution proof, live: boots a real (throwaway-copy-
    isolated) Aurora instance through the ACTUAL Android bridge entry
    point (aurora_bridge.handle_message(), the same function
    AuroraService.kt calls via Chaquopy), captures every
    process_external_user_turn() call handle_message() makes internally,
    and asserts the returned device text matches
    _sanitize_response(_extract_response(...)) of AT LEAST ONE captured
    call's result -- same "matches any call, not necessarily the first"
    standard test_delivered_output_attribution_traces_to_sentence_
    composer already established for resp_B, since handle_message() is
    confirmed (this directive's own finding) to make MULTIPLE internal
    process_external_user_turn() calls per user turn (background study-
    cycle prompts fire synchronously inside it -- see known_fixes_
    registry.md's D1 entry for that separate finding)."""
    sys.path.insert(0, REPO_ROOT)
    sys.path.insert(0, ANDROID_PY_DIR)

    import aurora as A

    captured = []
    orig_peut = A.process_external_user_turn

    def _patched(systems, user_text, **kwargs):
        result = orig_peut(systems, user_text, **kwargs)
        captured.append(result)
        return result

    A.process_external_user_turn = _patched
    scratch = tempfile.mkdtemp(prefix="aurora_d1_attribution_")
    try:
        shutil.copytree(
            os.path.join(REPO_ROOT, "aurora_state"),
            os.path.join(scratch, "aurora_state"),
        )
        import aurora_bridge

        init_result = aurora_bridge.initialize(state_dir=os.path.join(scratch, "aurora_state"))
        assert isinstance(init_result, str) and init_result.startswith("ready"), (
            f"aurora_bridge.initialize() did not report ready: {init_result!r}"
        )

        device_text = aurora_bridge.handle_message("Hi Aurora, how are you today?")
        assert captured, "handle_message() never called process_external_user_turn()"

        recomputed_candidates = [
            aurora_bridge._sanitize_response(
                aurora_bridge._extract_response(r), "Hi Aurora, how are you today?"
            )
            for r in captured
        ]
        assert device_text in recomputed_candidates, (
            f"device_delivered_text matched none of {len(captured)} captured "
            f"process_external_user_turn() call(s) -- the device-path "
            f"attribution to resp_A no longer holds and needs "
            f"re-verification. device_text={device_text!r} "
            f"candidates={recomputed_candidates!r}"
        )
    finally:
        A.process_external_user_turn = orig_peut
        shutil.rmtree(scratch, ignore_errors=True)
