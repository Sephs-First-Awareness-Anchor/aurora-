# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive D2.4 (2026-07-17): the stratified probe battery must measure
the UNIFIED DEVICE-DELIVERED FIELD -- resp_A, the field D1 proved every
real device surface actually reads.

Found while preparing D2.4's acceptance run: run_probe_battery.py's
_process() function read response.get("response_text"), a key
process_external_user_turn()'s result dict never populates (its real
keys are resp_A/resp_B/src/...). That miss was silent: it always fell
through to a SEPARATE call, aurora_gateway.speak_to_aurora(turn_text)
-- a fresh, independent invocation of the same underlying composer
machinery, not literally the turn's own resp_A/resp_B. Every probe-
battery score from R0 through R1.9.4 was therefore measuring that
separate call, not the field D1 proved actually reaches a device.

Fixed via a shared helper, _extract_delivered_response_text(), used at
both call sites (the main battery runner and --trace mode). This test
pins the correct extraction so it cannot silently regress back to the
non-existent "response_text" key.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import run_probe_battery as RPB


class _FakeRespA:
    def __init__(self, content):
        self.content = content


class _FakeGatewayResponse:
    def __init__(self, content):
        self.content = content


class _FakeAuroraGateway:
    def __init__(self, content):
        self._content = content
        self.called_with = None

    def speak_to_aurora(self, turn_text):
        self.called_with = turn_text
        return _FakeGatewayResponse(self._content)


def test_extracts_resp_a_content_directly_without_gateway_fallback():
    response = {"resp_A": _FakeRespA("I understand what you mean.")}
    gateway = _FakeAuroraGateway("SHOULD NOT BE USED")
    text = RPB._extract_delivered_response_text(response, "hello", gateway)
    assert text == "I understand what you mean."
    assert gateway.called_with is None, (
        "gateway fallback fired even though resp_A had real content -- "
        "the battery is no longer measuring the unified device-delivered "
        "field by default"
    )


def test_falls_back_to_gateway_only_when_resp_a_is_empty():
    response = {"resp_A": _FakeRespA("")}
    gateway = _FakeAuroraGateway("fallback content")
    text = RPB._extract_delivered_response_text(response, "hello", gateway)
    assert text == "fallback content"
    assert gateway.called_with == "hello"
    assert response.get("response_src") == "gateway_fallback"


def test_falls_back_when_resp_a_is_missing_entirely():
    response = {}
    gateway = _FakeAuroraGateway("fallback content")
    text = RPB._extract_delivered_response_text(response, "hello", gateway)
    assert text == "fallback content"


def test_does_not_reference_nonexistent_response_text_key():
    """Regression pin: process_external_user_turn()'s result dict never
    contains "response_text" -- confirm the extraction function does not
    depend on that key being present."""
    response = {"resp_A": _FakeRespA("Real composer content here."), "src": "composer_unified"}
    assert "response_text" not in response
    text = RPB._extract_delivered_response_text(response, "hello", None)
    assert text == "Real composer content here."


def test_gateway_none_does_not_crash_when_resp_a_empty():
    response = {"resp_A": _FakeRespA("")}
    text = RPB._extract_delivered_response_text(response, "hello", None)
    assert text == ""
