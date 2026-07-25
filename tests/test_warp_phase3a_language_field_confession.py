# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
WARP Universalization Directive, Phase 3a (2026-07-25, ratified priority
#1 of 4: LanguageField comparison judgments).

LanguageField._infer_comparison_type() classifies a ProtoLanguage's
comparison_type through a chain of explicit rules, falling all the way
through to a bare "assertion" default when nothing -- not even a
WARP-derived comparison type -- matches. That silent default is exactly
the directive's candidate #3 moment: "I can compare these but I'm not
confident in the comparison." It now confesses through the real,
universal WarpField (NO_LANGUAGE_FORM) instead of guessing behind a
plausible-looking label, without changing what comparison_type actually
ends up being (still "assertion" -- this is purely an honest signal
alongside the existing fallback).

_infer_comparison_type() itself now returns (comparison_type, matched)
so the caller (extract_proto_language) knows whether the classification
was a real rule hit or a bare guess.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_language_field as alf  # noqa: E402
from aurora_warp_protocol import WarpTrigger  # noqa: E402


class _FakeIdentityField:
    def __init__(self, topo):
        self._topo = topo

    def status(self):
        return {"pressure_topology": dict(self._topo)}


_UNIFORM_LOW_TOPO = {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}


def _lf(topo=None):
    return alf.LanguageField(identity_field=_FakeIdentityField(topo or _UNIFORM_LOW_TOPO))


def _real_shaped_warp_guard_spy(calls):
    """Mirrors warp_guard's real signature exactly -- a call shaped
    differently would raise TypeError here the same way a wrong-shaped
    call would against the real function."""
    def _spy(
        source: str, layer: str, trigger: str, *,
        unresolved_text: str = "", expected=None, actual=None,
        participants=None, profile=None, local_attempts=None,
        severity: float = 0.5, persistence_key: str = "",
    ):
        calls.append({
            "source": source, "layer": layer, "trigger": trigger,
            "unresolved_text": unresolved_text, "profile": profile,
            "severity": severity, "persistence_key": persistence_key,
        })
        return None
    return _spy


# ---- _infer_comparison_type: matched vs unmatched ----

def test_explicit_rule_match_reports_matched_true():
    lf = _lf()
    ctype, matched = lf._infer_comparison_type(
        ["X"], a=0.1, t=0.1, b=0.1,
        reasoning_level=0.0, reflection_level=0.0, emotion_level=0.0,
        text="is this a question?",
    )
    assert ctype == "question"
    assert matched is True


def test_no_rule_match_falls_back_to_assertion_unmatched():
    lf = _lf()
    ctype, matched = lf._infer_comparison_type(
        ["N"], a=0.0, t=0.0, b=0.0,
        reasoning_level=0.0, reflection_level=0.0, emotion_level=0.0,
        text="",
    )
    assert ctype == "assertion"
    assert matched is False


def test_warp_derived_comparison_type_match_reports_matched_true():
    lf = _lf()
    alf.LanguageField._warp_comparison_types["custom_type"] = ["N"]
    try:
        ctype, matched = lf._infer_comparison_type(
            ["N"], a=0.0, t=0.0, b=0.0,
            reasoning_level=0.0, reflection_level=0.0, emotion_level=0.0,
            text="",
        )
        assert ctype == "custom_type"
        assert matched is True
    finally:
        alf.LanguageField._warp_comparison_types.pop("custom_type", None)


# ---- extract_proto_language: confession wiring ----

def test_extract_proto_language_confesses_on_unmatched_fallback(monkeypatch):
    calls = []
    monkeypatch.setattr(alf, "warp_guard", _real_shaped_warp_guard_spy(calls))
    lf = _lf()

    proto = lf.extract_proto_language(user_text="hello there")

    assert proto.comparison_type == "assertion"
    assert len(calls) == 1
    call = calls[0]
    assert call["source"] == "language_field"
    assert call["layer"] == "infer_comparison_type"
    assert call["trigger"] == WarpTrigger.NO_LANGUAGE_FORM
    assert call["unresolved_text"] == "hello there"
    assert call["profile"] == {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}
    assert call["persistence_key"] == "comparison_type:X"


def test_extract_proto_language_does_not_confess_when_matched(monkeypatch):
    calls = []
    monkeypatch.setattr(alf, "warp_guard", _real_shaped_warp_guard_spy(calls))
    lf = _lf()

    proto = lf.extract_proto_language(user_text="what is happening?")

    assert proto.comparison_type == "question"
    assert calls == []


def test_confess_comparison_uncertainty_exceptions_are_swallowed(monkeypatch):
    def _always_raises(*a, **kw):
        raise RuntimeError("warp field unavailable")
    monkeypatch.setattr(alf, "warp_guard", _always_raises)
    lf = _lf()

    # Must not raise -- confession-path failures never break extraction.
    proto = lf.extract_proto_language(user_text="hello there")
    assert proto.comparison_type == "assertion"


def test_confess_comparison_uncertainty_noop_when_warp_unavailable(monkeypatch):
    calls = []
    monkeypatch.setattr(alf, "warp_guard", _real_shaped_warp_guard_spy(calls))
    monkeypatch.setattr(alf, "_WARP_AVAILABLE", False)
    lf = _lf()

    proto = lf.extract_proto_language(user_text="hello there")
    assert proto.comparison_type == "assertion"
    assert calls == []
