# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive P1 Track CP: contradiction perception via pair collision.
Feeds the EXISTING starved ContradictionLedger through its real
.record() entry point on genuine pair collisions only -- fail-quiet
on unknown compatibility. Acceptance: 12-probe contradiction set +
10 no-contradiction controls, zero false fires on controls.
"""
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_contradiction_perception import (  # noqa: E402
    find_collisions, _closed_set_conflict, _oets_antonym_conflict,
    _recent_window_pairs, perceive_contradictions, WINDOW_TURNS,
)


def _pair(op, arg, negated=False, turn_id="0"):
    return {"operator_relation": op, "argument_word": arg, "negated": negated, "turn_id": turn_id}


# ── Pure-logic unit tests ───────────────────────────────────────────────

def test_negation_flip_collision():
    new = [_pair("point", "mercury", negated=True, turn_id="2")]
    window = [_pair("point", "mercury", negated=False, turn_id="1")]
    collisions = find_collisions(new, window, set())
    assert len(collisions) == 1
    assert collisions[0][2] == "negation_flip"


def test_same_pair_same_negation_no_collision():
    new = [_pair("point", "mercury", negated=False, turn_id="2")]
    window = [_pair("point", "mercury", negated=False, turn_id="1")]
    assert find_collisions(new, window, set()) == []


def test_closed_set_weekday_collision():
    assert _closed_set_conflict("tuesday", "thursday") is True
    assert _closed_set_conflict("tuesday", "tuesday") is False
    new = [_pair("start", "thursday", turn_id="2")]
    window = [_pair("start", "tuesday", turn_id="1")]
    collisions = find_collisions(new, window, set())
    assert len(collisions) == 1
    assert collisions[0][2] == "closed_set_conflict"


def test_oets_antonym_collision():
    contradicts = {frozenset(("guarantee", "uncertain"))}
    assert _oets_antonym_conflict("guarantee", "uncertain", contradicts) is True
    assert _oets_antonym_conflict("uncertain", "guarantee", contradicts) is True
    new = [_pair("level", "uncertain", turn_id="2")]
    window = [_pair("level", "guarantee", turn_id="1")]
    collisions = find_collisions(new, window, contradicts)
    assert len(collisions) == 1
    assert collisions[0][2] == "oets_antonym"


def test_different_operator_never_collides():
    new = [_pair("weight", "box", turn_id="2")]
    window = [_pair("color", "box", turn_id="1")]
    assert find_collisions(new, window, {frozenset(("box", "box"))}) == []


def test_unknown_compatibility_fails_quiet():
    """Same operator, different args, no closed-set/antonym evidence --
    this is exactly the fail-quiet doctrine: unknown never accuses."""
    new = [_pair("type", "art", turn_id="2")]
    window = [_pair("type", "music", turn_id="1")]
    assert find_collisions(new, window, set()) == []


def test_recent_window_excludes_current_turn_and_caps_at_window_turns():
    scratch = tempfile.mkdtemp(prefix="aurora_cp_window_")
    try:
        import json
        path = os.path.join(scratch, "relation_pair_log.jsonl")
        with open(path, "w") as f:
            for t in range(10):
                f.write(json.dumps({"operator_relation": "op", "argument_word": f"a{t}", "turn_id": str(t)}) + "\n")
        window = _recent_window_pairs(path, current_turn_id="9", window_turns=WINDOW_TURNS)
        turn_ids = {r["turn_id"] for r in window}
        assert "9" not in turn_ids
        assert len(turn_ids) == WINDOW_TURNS
        assert turn_ids == {"3", "4", "5", "6", "7", "8"}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_perceive_contradictions_degrades_gracefully():
    assert perceive_contradictions("anything", {}, turn_id=1) == 0


def test_chain_down5_understanding_wires_track_cp_detector():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index("def _chain_down5_understanding(user_text: str, systems: dict, state: Any,")
    block = source[idx:idx + 3000]
    assert "perceive_contradictions" in block
    assert "aurora_contradiction_perception" in block


# ── Live acceptance battery: 12 contradiction probes + 10 controls ─────

CONTRADICTION_PROBES = [
    # negation flip (4)
    ("boiling point of mercury", "there is no boiling point of mercury"),
    ("cause of confusion", "definitely not the cause of confusion"),
    ("reason of trouble", "no reason of trouble"),
    ("source of leak", "not the source of leak"),
    # mutually exclusive closed set: day-of-week (4)
    ("start of tuesday", "start of thursday"),
    ("end of monday", "end of friday"),
    ("middle of wednesday", "middle of saturday"),
    ("date of sunday", "date of tuesday"),
    # OETS antonym relations, seeded S1.2 (4)
    ("level of guarantee", "level of uncertain"),
    ("degree of hedge", "degree of guarantee"),
    ("amount of guarantee", "amount of uncertain"),
    ("measure of hedge", "measure of guarantee"),
]

NO_CONTRADICTION_CONTROLS = [
    # exact repeat, no negation change -- not a contradiction
    ("topic of water", "topic of water"),
    ("focus of practice", "focus of practice"),
    # different operator entirely -- never comparable
    ("shape of cloud", "flavor of soup"),
    ("origin of story", "ending of story"),
    ("weight of box", "color of box"),
    # same operator, different but UNKNOWN-compatibility args -- fail-quiet
    ("type of music", "type of art"),
    ("kind of animal", "kind of plant"),
    ("style of writing", "style of painting"),
    ("version of software", "version of hardware"),
    ("form of energy", "form of matter"),
]


def test_track_cp_acceptance_battery_live():
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_cp_live_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)
        ledger = systems["contradiction_ledger"]

        results = {}
        for label, (t1, t2) in list(zip(
            [f"contra_{i}" for i in range(len(CONTRADICTION_PROBES))], CONTRADICTION_PROBES
        )) + list(zip(
            [f"control_{i}" for i in range(len(NO_CONTRADICTION_CONTROLS))], NO_CONTRADICTION_CONTROLS
        )):
            before = ledger.unresolved_count()
            A.process_external_user_turn(systems, t1)
            A.process_external_user_turn(systems, t2)
            after = ledger.unresolved_count()
            results[label] = after - before

        contra_fired = sum(1 for k, v in results.items() if k.startswith("contra_") and v >= 1)
        control_false_fires = sum(1 for k, v in results.items() if k.startswith("control_") and v >= 1)

        print("\nTrack CP acceptance battery:")
        for k, v in results.items():
            print(f"  {k}: ledger delta={v}")
        print(f"  contradiction probes fired: {contra_fired}/{len(CONTRADICTION_PROBES)}")
        print(f"  control false fires: {control_false_fires}/{len(NO_CONTRADICTION_CONTROLS)}")

        assert control_false_fires == 0, "fail-quiet doctrine violated: a no-contradiction control fired"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
