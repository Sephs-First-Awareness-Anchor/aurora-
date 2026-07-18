# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive M1.1, Amendment M1.1-A: shared relation-pair extraction
(aurora_internal/aurora_relation_pairs.py) and its two consumers --
Tier-1's offline archival backfill and Tier-2's live comprehension-
stage logger.
"""
import json
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_relation_pairs import (  # noqa: E402
    extract_joints, region_from_entry, log_relation_pairs_from_turn,
)
import aurora_expression_perception as aep  # noqa: E402


def test_extract_joints_of_by_pattern():
    joints = extract_joints("the boiling point of water", aep.infer_word_role)
    pairs = [(o, a) for o, a, p in joints if p == "X_of_Y"]
    assert ("point", "water") in pairs


def test_extract_joints_by_pattern():
    joints = extract_joints("caused by pressure", aep.infer_word_role)
    pairs = [(o, a) for o, a, p in joints if p == "X_by_Y"]
    assert ("caused", "pressure") in pairs


def test_extract_joints_adjective_noun_adjacency():
    joints = extract_joints("I create beautiful things", aep.infer_word_role)
    assert ("beautiful", "things", "adjective_noun_adjacent") in joints


def test_extract_joints_short_text_returns_empty():
    assert extract_joints("hi", aep.infer_word_role) == []


def test_region_from_entry_fail_closed_on_placeholder_low_usage():
    """Matches D2 Condition-2 doctrine exactly: a blind same-turn guess
    (meaning == 'learned:<word>') with low usage_count gets no region."""
    region = region_from_entry("zqxvornmal", "learned:zqxvornmal", "X:POLARITY", 1)
    assert region is None


def test_region_from_entry_graduates_past_usage_floor():
    region = region_from_entry("weight", "learned:weight", "N:MAGNITUDE", 774)
    assert region == "N"


def test_region_from_entry_real_definition_never_capped():
    region = region_from_entry("purple", "a color -- a perceptual attribute", "X:MAGNITUDE", 0)
    assert region == "X"


def test_region_from_entry_no_noncomp_id_is_none():
    assert region_from_entry("mystery", "learned:mystery", None, 50) is None


def test_log_relation_pairs_from_turn_writes_scoped_to_state_dir():
    """Live test: a real lexicon-backed systems dict, scratch state_dir --
    confirms the logger writes to state_dir/relation_pair_log.jsonl (not
    a hardcoded repo path) and stamps source/turn_id/origin correctly."""
    scratch = tempfile.mkdtemp(prefix="aurora_m1_1a_test_")
    try:
        lexicon = aep.LexicalMemory()
        systems = {"perception": type("P", (), {"lexicon": lexicon})(), "state_dir": scratch}

        n = log_relation_pairs_from_turn(
            "the boiling point of water", systems, turn_id=7, source="input",
        )
        assert n > 0

        out_path = os.path.join(scratch, "relation_pair_log.jsonl")
        assert os.path.exists(out_path)
        with open(out_path) as f:
            rows = [json.loads(l) for l in f if l.strip()]
        assert rows
        assert all(r["source"] == "input" for r in rows)
        assert all(r["turn_id"] == "7" for r in rows)
        assert all(r["origin"] == "live_comprehension" for r in rows)
        assert any(r["operator_relation"] == "point" and r["argument_word"] == "water" for r in rows)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_log_relation_pairs_from_turn_degrades_gracefully_without_perception():
    """Read-only observer doctrine: missing/broken perception must not
    raise -- just report zero pairs written."""
    n = log_relation_pairs_from_turn("anything at all", {}, turn_id=1)
    assert n == 0


def test_chain_down5_understanding_calls_tier2_logger():
    """Structural confirmation of the wiring in aurora.py: the Tier-2
    logger fires at the comprehension stage's entry point."""
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index("def _chain_down5_understanding(user_text: str, systems: dict, state: Any,")
    block = source[idx:idx + 1200]
    assert "log_relation_pairs_from_turn" in block
    assert 'source="input"' in block


def test_live_turn_appends_to_relation_pair_log():
    """End-to-end: a real boot + real turn through process_external_user_turn
    appends Tier-2 entries to the scratch state_dir's relation_pair_log.jsonl."""
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_m1_1a_live_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        log_path = os.path.join(scratch_state, "relation_pair_log.jsonl")
        before = 0
        if os.path.exists(log_path):
            with open(log_path) as f:
                before = sum(1 for l in f if l.strip())

        A.process_external_user_turn(systems, "What is the boiling point of water?")

        assert os.path.exists(log_path), "Tier-2 logger never wrote relation_pair_log.jsonl"
        with open(log_path) as f:
            rows = [json.loads(l) for l in f if l.strip()]
        assert len(rows) > before
        new_rows = rows[before:]
        assert all(r["source"] == "input" for r in new_rows)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
