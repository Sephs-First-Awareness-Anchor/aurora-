#!/usr/bin/env python3
"""
AURORA SEMANTIC PROBE BATTERY — held-out competence instrument
==============================================================
Phase R0 of the Semantic Plateau Remediation Directive (2026-07-15).

Twelve days of classroom lessons produced a flat experiential signal
(i_state pair identical in 472/472 lessons, divergence_score 0.0 in
100% of lessons) while dev_index kept climbing on wisdom_shards
accumulation alone. dev_index measures accretion, not competence, and
the directive demotes it to telemetry: "No further classroom lessons
are scored by dev_index. Competence = probe score."

This module is the gauge. It does NOT introduce a parallel scorer --
every dimension score comes from aurora_internal.aurora_conversation_
rubric_engine.ConversationRubricEngine, the same scoring path already
used to generate training pressure. The only new logic here is:
  1. loading the fixed, held-out probe manifest (aurora_state/
     probe_battery/probes.json),
  2. driving each probe's turns through the canonical
     boot_aurora()/process_external_user_turn() response path,
  3. checking each probe's expected_properties against the resulting
     transcript (mostly by thresholding rubric dimension_scores, plus
     reuse of the rubric engine's own private marker detectors), and
  4. is_seed_excluded(), the hash-based guard that keeps this battery
     out of the classroom's own lesson-seed pool -- a probe that ever
     became training content would stop being held-out.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aurora_internal.aurora_conversation_rubric_engine import (
    ConversationRubricEngine,
    _contradiction_markers,
    _hedging_score,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(REPO_ROOT, "aurora_state")
PROBE_BATTERY_DIR = os.path.join(STATE_DIR, "probe_battery")
PROBES_PATH = os.path.join(PROBE_BATTERY_DIR, "probes.json")
RESULTS_DIR = os.path.join(PROBE_BATTERY_DIR, "results")

# Dimensions the rubric engine already tracks; used to threshold expected
# properties that reuse a RUBRIC_DIMENSIONS score directly.
_CONTEXT_CARRYOVER_THRESHOLD = 0.35
_CONTRADICTION_ACK_THRESHOLD = 0.34   # ~1 marker hit on the shared detector
_HEDGE_THRESHOLD = 0.34               # ~1 marker hit on the shared detector
_BOUNDARY_CALIBRATION_THRESHOLD = 0.45


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _hash_text(text: str) -> str:
    """Canonical hash for exclusion matching -- normalized, not raw bytes."""
    normalized = " ".join(str(text or "").strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ============================================================================
# PROBE MANIFEST LOADING
# ============================================================================

@dataclass
class Probe:
    probe_id: str
    dimension: str
    turns: List[str]
    expected_properties: List[str] = field(default_factory=list)
    referent_keywords: List[str] = field(default_factory=list)


def _load_manifest(probes_path: str = PROBES_PATH) -> Dict[str, Any]:
    with open(probes_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_probes(probes_path: str = PROBES_PATH) -> List[Probe]:
    """Load the held-out probe battery. Raises on missing/malformed manifest --
    callers that need graceful degradation (e.g. classroom exclusion) should
    use is_seed_excluded(), which never raises."""
    manifest = _load_manifest(probes_path)
    probes: List[Probe] = []
    for entry in manifest.get("probes", []) or []:
        probes.append(Probe(
            probe_id=str(entry.get("probe_id") or ""),
            dimension=str(entry.get("dimension") or ""),
            turns=[str(t) for t in (entry.get("turns") or [])],
            expected_properties=[str(p) for p in (entry.get("expected_properties") or [])],
            referent_keywords=[str(k) for k in (entry.get("referent_keywords") or [])],
        ))
    return probes


_exclusion_cache: Optional[Tuple[float, set]] = None


def _excluded_hash_set(probes_path: str = PROBES_PATH) -> set:
    """Cached set of hashes for every probe turn, keyed off manifest mtime
    so classroom callers don't re-read/re-hash the file on every seed pick."""
    global _exclusion_cache
    try:
        mtime = os.path.getmtime(probes_path)
    except OSError:
        return set()
    if _exclusion_cache is not None and _exclusion_cache[0] == mtime:
        return _exclusion_cache[1]
    try:
        manifest = _load_manifest(probes_path)
        hashes = set()
        for entry in manifest.get("probes", []) or []:
            for turn in entry.get("turns", []) or []:
                hashes.add(_hash_text(turn))
        _exclusion_cache = (mtime, hashes)
        return hashes
    except Exception:
        return set()


def is_seed_excluded(text: str, probes_path: str = PROBES_PATH) -> bool:
    """True if `text` matches a held-out probe turn and must never be offered
    as classroom/lesson seed content. Degrades to False (never blocks the
    classroom) on any load failure -- same failure-isolation discipline as
    every other guard in this codebase."""
    try:
        if not text or not str(text).strip():
            return False
        return _hash_text(text) in _excluded_hash_set(probes_path)
    except Exception:
        return False


# ============================================================================
# EXPECTED-PROPERTY PREDICATES
# ============================================================================

def _mentions_referent(response_text: str, referent_keywords: List[str]) -> bool:
    if not referent_keywords:
        return True
    lower = response_text.lower()
    return any(kw.lower() in lower for kw in referent_keywords)


def _acknowledges_contradiction(response_text: str, dimension_scores: Dict[str, float]) -> bool:
    direct = _contradiction_markers(response_text) >= _CONTRADICTION_ACK_THRESHOLD
    rubric = dimension_scores.get("contradiction_handling", 0.0) >= _CONTRADICTION_ACK_THRESHOLD
    return bool(direct or rubric)


def _hedges(response_text: str, dimension_scores: Dict[str, float]) -> bool:
    direct = _hedging_score(response_text) >= _HEDGE_THRESHOLD
    rubric = dimension_scores.get("uncertainty_signaling", 0.0) >= _HEDGE_THRESHOLD
    return bool(direct or rubric)


def _appropriately_scaled(dimension_scores: Dict[str, float]) -> bool:
    return dimension_scores.get("boundary_calibration", 0.0) >= _BOUNDARY_CALIBRATION_THRESHOLD


_WORD_RE = re.compile(r"[A-Za-z']+")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")

# Real English sentences of any length almost always carry at least one of
# these -- an article, preposition, conjunction, or copula. Sentences built
# entirely from bare content words ("Something deep need gentle") are the
# structural signature of the audit's cited failure case even though every
# individual token is a real word.
_FUNCTION_WORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "with", "by", "from",
    "and", "or", "but", "nor", "so", "yet", "is", "are", "was", "were", "am",
    "be", "been", "being", "that", "this", "these", "those", "as", "than",
}


def _parseable(response_text: str) -> bool:
    """Lightweight wellformedness heuristic -- no NLP library assumed
    available, matches the regex/wordlist heuristic style already used
    throughout aurora_conversation_rubric_engine.py.

    Checks: non-empty, has recognizable word tokens, isn't dominated by a
    single repeated fragment, has a plausible word-to-character ratio, and
    (for any sentence long enough to expect grammatical scaffolding) carries
    at least one function word -- catches word-salad / garbled output like
    the audit's cited failure: "Something deep need gentle -- I wonder it."
    """
    text = str(response_text or "").strip()
    if not text:
        return False
    words = _WORD_RE.findall(text)
    if len(words) < 2:
        return False
    lower_words = [w.lower() for w in words]
    distinct_ratio = len(set(lower_words)) / len(lower_words)
    if distinct_ratio < 0.4:
        return False
    avg_word_len = sum(len(w) for w in words) / len(words)
    if avg_word_len < 1.5 or avg_word_len > 14:
        return False
    alpha_chars = sum(1 for c in text if c.isalpha())
    if alpha_chars / max(len(text), 1) < 0.35:
        return False

    for sentence in _SENTENCE_SPLIT_RE.split(text):
        sentence_words = [w.lower() for w in _WORD_RE.findall(sentence)]
        if len(sentence_words) >= 6 and not any(w in _FUNCTION_WORDS for w in sentence_words):
            return False
    return True


def _mentions_referent_property(referent_keywords: List[str]):
    return lambda resp, dims: _mentions_referent(resp, referent_keywords)


_PREDICATES = {
    "acknowledges_contradiction": lambda resp, dims: _acknowledges_contradiction(resp, dims),
    "hedges": lambda resp, dims: _hedges(resp, dims),
    "appropriately_scaled": lambda resp, dims: _appropriately_scaled(dims),
    "parseable": lambda resp, dims: _parseable(resp),
}


def check_expected_properties(
    probe: Probe,
    response_text: str,
    dimension_scores: Dict[str, float],
) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    for prop in probe.expected_properties:
        if prop == "mentions_referent":
            results[prop] = _mentions_referent(response_text, probe.referent_keywords)
        elif prop in _PREDICATES:
            results[prop] = _PREDICATES[prop](response_text, dimension_scores)
        else:
            results[prop] = False
    return results


# ============================================================================
# BATTERY RUN
# ============================================================================

@dataclass
class ProbeResult:
    probe_id: str
    dimension: str
    status: str  # "ok" | "blocked"
    reason: str = ""
    transcript: List[Dict[str, str]] = field(default_factory=list)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    property_results: Dict[str, bool] = field(default_factory=dict)
    passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "dimension": self.dimension,
            "status": self.status,
            "reason": self.reason,
            "transcript": self.transcript,
            "dimension_scores": self.dimension_scores,
            "property_results": self.property_results,
            "passed": self.passed,
        }


def run_probe(
    probe: Probe,
    process_turn_fn,
    rubric_engine: ConversationRubricEngine,
) -> ProbeResult:
    """Drive one probe's turns through `process_turn_fn` (expected to be a
    closure over process_external_user_turn(systems, text, session_id=...)
    with a probe-unique session_id already bound), score the resulting
    transcript via the shared rubric engine, and check expected_properties.

    Never raises -- a blocked probe is reported blocked, never silently
    dropped (modality-honest reporting, matching run_full_competency_
    gauntlet.py's own doctrine).
    """
    messages: List[Tuple[str, str]] = []
    transcript: List[Dict[str, str]] = []
    last_response_text = ""
    try:
        for turn_text in probe.turns:
            messages.append(("user", turn_text))
            transcript.append({"role": "user", "text": turn_text})
            raw = process_turn_fn(turn_text) or {}
            response_text = str(raw.get("response_text") or "").strip()
            last_response_text = response_text
            messages.append(("assistant", response_text))
            transcript.append({"role": "assistant", "text": response_text})
    except Exception as exc:
        return ProbeResult(
            probe_id=probe.probe_id,
            dimension=probe.dimension,
            status="blocked",
            reason=f"exception during probe turns: {exc}",
            transcript=transcript,
        )

    if not last_response_text:
        return ProbeResult(
            probe_id=probe.probe_id,
            dimension=probe.dimension,
            status="blocked",
            reason="no response_text produced",
            transcript=transcript,
        )

    try:
        score = rubric_engine.score_conversation(probe.probe_id, messages)
        dimension_scores = dict(score.dimension_scores)
    except Exception as exc:
        return ProbeResult(
            probe_id=probe.probe_id,
            dimension=probe.dimension,
            status="blocked",
            reason=f"rubric scoring failed: {exc}",
            transcript=transcript,
        )

    property_results = check_expected_properties(probe, last_response_text, dimension_scores)
    passed = bool(property_results) and all(property_results.values())

    return ProbeResult(
        probe_id=probe.probe_id,
        dimension=probe.dimension,
        status="ok",
        transcript=transcript,
        dimension_scores=dimension_scores,
        property_results=property_results,
        passed=passed,
    )


@dataclass
class BatteryReport:
    run_id: str
    timestamp: float
    probe_results: List[ProbeResult] = field(default_factory=list)

    def per_dimension_summary(self) -> Dict[str, Dict[str, Any]]:
        """Pass rate is measured against every LOADED probe for the
        dimension, not just the ones that happened to score. A blocked
        probe is an unknown/failed measurement for this competence
        instrument -- it counts against the score, never gets excluded
        from the denominator (a run that blocks 59/60 probes and passes
        the 1 it scored must not report 100%)."""
        by_dim: Dict[str, List[ProbeResult]] = {}
        for r in self.probe_results:
            by_dim.setdefault(r.dimension, []).append(r)
        summary: Dict[str, Dict[str, Any]] = {}
        for dim, results in by_dim.items():
            scored = [r for r in results if r.status == "ok"]
            blocked = [r for r in results if r.status != "ok"]
            passed = [r for r in scored if r.passed]
            summary[dim] = {
                "probe_count": len(results),
                "scored_count": len(scored),
                "blocked_count": len(blocked),
                "pass_count": len(passed),
                "pass_rate": (len(passed) / len(results)) if results else 0.0,
            }
        return summary

    def overall_pass_rate(self) -> float:
        """Denominator is every loaded probe, blocked or not -- see
        per_dimension_summary()'s docstring for why."""
        if not self.probe_results:
            return 0.0
        return sum(1 for r in self.probe_results if r.passed) / len(self.probe_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "overall_pass_rate": self.overall_pass_rate(),
            "per_dimension": self.per_dimension_summary(),
            "probe_results": [r.to_dict() for r in self.probe_results],
        }


def run_battery(
    process_turn_fn_factory,
    run_id: str,
    probes_path: str = PROBES_PATH,
) -> BatteryReport:
    """`process_turn_fn_factory(probe: Probe) -> callable(turn_text) -> dict`
    lets the caller bind a fresh, probe-unique session_id per probe while
    this module stays decoupled from boot_aurora()'s systems dict."""
    probes = load_probes(probes_path)
    rubric_engine = ConversationRubricEngine()
    results: List[ProbeResult] = []
    for probe in probes:
        process_turn_fn = process_turn_fn_factory(probe)
        results.append(run_probe(probe, process_turn_fn, rubric_engine))
    return BatteryReport(run_id=run_id, timestamp=time.time(), probe_results=results)


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_semantic_probe_battery() -> Dict[str, Any]:
    results = []

    def check(name: str, cond: bool, detail: str = ""):
        results.append({"test": name, "passed": bool(cond), "detail": detail})

    probes = load_probes()
    check("probe manifest loads", len(probes) > 0, f"{len(probes)} probes")
    check("~60 probes present", 50 <= len(probes) <= 80, f"{len(probes)} probes")

    dims = {p.dimension for p in probes}
    expected_dims = {
        "context_carryover", "contradiction_handling", "uncertainty_signaling",
        "boundary_calibration", "semantic_wellformedness",
    }
    check("all 5 required dimensions present", expected_dims.issubset(dims), f"got {dims}")

    # is_seed_excluded: a probe turn must be excluded, an unrelated string must not.
    sample_turn = probes[0].turns[0]
    check("is_seed_excluded matches a real probe turn", is_seed_excluded(sample_turn))
    check(
        "is_seed_excluded does not match unrelated text",
        not is_seed_excluded("this text was never in any probe manifest, purely novel"),
    )
    check(
        "is_seed_excluded degrades gracefully on missing manifest",
        is_seed_excluded(sample_turn, probes_path="/nonexistent/path/probes.json") is False,
    )

    # parseable heuristic
    check("parseable rejects garbled output", not _parseable("Something deep need gentle -- I wonder it."))
    check("parseable accepts an ordinary sentence", _parseable("It's nice to meet you, Sunni."))
    check("parseable rejects empty text", not _parseable(""))
    check("parseable rejects repeated-fragment word salad", not _parseable("go go go go go go go go"))

    # expected-property predicates
    ctx_probe = next(p for p in probes if p.dimension == "context_carryover")
    props = check_expected_properties(
        ctx_probe,
        f"Sure, keeping in mind the {ctx_probe.referent_keywords[0]} you mentioned.",
        {},
    )
    check("mentions_referent predicate fires on referent match", props.get("mentions_referent") is True)

    contra_probe = next(p for p in probes if p.dimension == "contradiction_handling")
    props2 = check_expected_properties(
        contra_probe,
        "That sounds contradictory -- however, both things can be true at once.",
        {},
    )
    check("acknowledges_contradiction predicate fires on marker text", props2.get("acknowledges_contradiction") is True)

    uncertainty_probe = next(p for p in probes if p.dimension == "uncertainty_signaling")
    props3 = check_expected_properties(
        uncertainty_probe,
        "I'm not sure, it's hard to say, it could go either way.",
        {},
    )
    check("hedges predicate fires on hedging text", props3.get("hedges") is True)

    # run_probe / run_battery wiring with a stub response function
    def stub_factory(probe: Probe):
        def _stub(turn_text: str) -> Dict[str, Any]:
            return {"response_text": f"Noted, regarding {' '.join(probe.referent_keywords[:1])}: however that could be true."}
        return _stub

    report = run_battery(stub_factory, run_id="self_test")
    check("run_battery produces one result per probe", len(report.probe_results) == len(probes))
    check("battery report has per-dimension summary", len(report.per_dimension_summary()) > 0)

    return {"checks": results, "total": len(results), "passed": sum(1 for r in results if r["passed"])}


if __name__ == "__main__":
    print("=" * 70)
    print("AURORA SEMANTIC PROBE BATTERY — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    outcome = verify_semantic_probe_battery()
    for c in outcome["checks"]:
        status = "OK" if c["passed"] else "FAIL"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  [{status}] {c['test']}{detail}")
    print(f"\n{outcome['passed']}/{outcome['total']} checks passed.")
    print("=" * 70)
