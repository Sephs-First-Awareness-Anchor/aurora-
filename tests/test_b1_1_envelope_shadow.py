# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive B1.1: Boundary Envelope shadow deployment. Computes per-joint
envelope verdicts on real received turns and logs them, with ZERO
behavioral effect -- read-only observer, same contract as the Tier-2
relation-pair logger it rides beside.
"""
import json
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_boundary_envelope import (  # noqa: E402
    build_pair_index, score_joint, log_envelope_shadow,
    DIRECT_THRESHOLD, REGION_COUNT_THRESHOLD, REGION_DIVERSITY_THRESHOLD,
)


def _entries(**kw):
    """word -> {meaning, noncomp_id, usage_count} dict, matching what
    log_envelope_shadow builds from live LexicalEntry objects."""
    return kw


def test_build_pair_index_counts_direct_and_region():
    pairs = [
        {"operator_relation": "boiling", "argument_word": "water", "argument_region": "N"},
        {"operator_relation": "boiling", "argument_word": "water", "argument_region": "N"},
        {"operator_relation": "boiling", "argument_word": "oil", "argument_region": "N"},
    ]
    direct, region = build_pair_index(pairs)
    assert direct[("boiling", "water")] == 2
    key = ("boiling", "N")
    assert region[key]["instance_count"] == 3
    assert region[key]["distinct_arguments"] == {"water", "oil"}


def test_score_joint_direct_pair_support():
    direct = {("point", "water"): DIRECT_THRESHOLD}
    region = {}
    lex = {"water": _entries(meaning="a substance", noncomp_id="X:MAGNITUDE", usage_count=5)}
    verdict, reason, evidence = score_joint(["point"], "water", lex, direct, region)
    assert verdict == "supported"
    assert evidence["match_kind"] == "direct_pair"


def test_score_joint_region_generalized_support():
    direct = {}
    distinct_args = {f"substance_{i}" for i in range(REGION_DIVERSITY_THRESHOLD)}
    region = {("boiling", "N"): {
        "instance_count": REGION_COUNT_THRESHOLD,
        "distinct_arguments": distinct_args,
    }}
    lex = {"mercury": _entries(meaning="a metal", noncomp_id="N:MAGNITUDE", usage_count=5)}
    verdict, reason, evidence = score_joint(["boiling"], "mercury", lex, direct, region)
    assert verdict == "supported"
    assert evidence["match_kind"] == "region_generalized"


def test_score_joint_unknown_with_no_history():
    verdict, reason, evidence = score_joint(["square"], "purple", {"purple": _entries(meaning="a color", noncomp_id="X:MAGNITUDE", usage_count=5)}, {}, {})
    assert verdict == "unknown"
    assert evidence["match_kind"] == "none"


def test_score_joint_never_returns_contradicted():
    """M1.3's own design: no counter-evidence store exists, so absence
    of support must always be 'unknown', never 'contradicted' -- this
    is the fix for S1's inversion, permanent invariant."""
    import random
    random.seed(0)
    words = ["purple", "wednesday", "victory", "heart", "code", "archive"]
    for w in words:
        verdict, _, _ = score_joint(["some_operator"], w, {}, {}, {})
        assert verdict != "contradicted"


def test_log_envelope_shadow_writes_scoped_to_state_dir():
    scratch = tempfile.mkdtemp(prefix="aurora_b1_1_test_")
    try:
        import aurora_expression_perception as aep
        lexicon = aep.LexicalMemory()
        systems = {"perception": type("P", (), {"lexicon": lexicon})(), "state_dir": scratch}

        n = log_envelope_shadow("the boiling point of water", systems, turn_id=3)
        assert n > 0

        out_path = os.path.join(scratch, "envelope_shadow_log.jsonl")
        assert os.path.exists(out_path)
        with open(out_path) as f:
            rows = [json.loads(l) for l in f if l.strip()]
        assert rows
        assert all(r["turn_id"] == "3" for r in rows)
        assert all(r["verdict"] in ("supported", "unknown") for r in rows)
        assert all("provenance_mix" in r for r in rows)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_log_envelope_shadow_degrades_gracefully():
    n = log_envelope_shadow("anything", {}, turn_id=1)
    assert n == 0


def test_chain_down5_understanding_wires_b1_1_shadow_logger():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index("def _chain_down5_understanding(user_text: str, systems: dict, state: Any,")
    block = source[idx:idx + 3000]
    assert "log_envelope_shadow" in block
    assert "aurora_boundary_envelope" in block


def test_live_turn_appends_to_envelope_shadow_log():
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_b1_1_live_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        log_path = os.path.join(scratch_state, "envelope_shadow_log.jsonl")
        before = 0
        if os.path.exists(log_path):
            with open(log_path) as f:
                before = sum(1 for l in f if l.strip())

        A.process_external_user_turn(systems, "What is the boiling point of water?")

        assert os.path.exists(log_path), "B1.1 shadow logger never wrote envelope_shadow_log.jsonl"
        with open(log_path) as f:
            rows = [json.loads(l) for l in f if l.strip()]
        assert len(rows) > before
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
