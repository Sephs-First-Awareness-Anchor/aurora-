"""
Directive P1 Track CP -- Contradiction perception via pair collision.

Detector: on each received turn, the turn's freshly extracted relation
pairs (Tier-2 relation_pair_log, live since M1.1-A) are checked
against a recent window of prior received pairs for collisions --
same operator_relation ("subject+relation"), incompatible
argument_word ("value"). A collision feeds the EXISTING, previously-
starved ContradictionLedger through its real .record() entry point
(aurora_ivm.py) -- no rival ledger built.

Three incompatibility sources, narrow and honest (fail-quiet
elsewhere -- an UNKNOWN-compatibility pair never fires; a false
contradiction accusation is worse than a miss at this stage):
  1. Explicit negation: the SAME (operator, argument) pair recurs, but
     one occurrence is negated and the other is not (Tier-2's
     `negated` field, proximity-based, matching this module family's
     existing extraction honesty level -- not a real parser).
  2. Mutually exclusive closed value sets: two DIFFERENT argument_words
     for the same operator_relation both belong to one closed set
     (currently: day-of-week) -- e.g. "Tuesday" vs "Thursday".
  3. Antonym pairs via OETS "opposite_of" relations: two DIFFERENT
     argument_words for the same operator_relation are directly
     connected by an opposite_of-type relation in aurora_oets_web.json
     (either direction) -- e.g. S1.2's guarantee<->uncertain. (Named
     "opposite_of" -- the live RelationType enum's real antonym value,
     aurora_internal/aurora_ontological_scaffolding.py -- not
     "contradicts", which S1.2's original seed script mistakenly used;
     that string isn't a recognized relation_type, so it was silently
     reclassified to RELATED_TO on the very next boot_aurora() load/
     resave cycle. Corrected in scripts/seed_abstract_regions_s1.py and
     in the live aurora_oets_web.json data, 2026-07-19.)

Window: 6 turns. Derived from classroom_log.jsonl's own fixed lesson
length (602/602 lessons all exactly 6 turns -- the only concrete real
"conversation length" distribution available; the probe battery's own
turns are far shorter -- median 1, max 2 -- and not representative of
a sustained exchange where a stated fact could plausibly be revisited).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json
import os

from aurora_internal.aurora_relation_pairs import extract_joints, is_negated_near

WINDOW_TURNS = 6

WEEKDAYS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}
CLOSED_VALUE_SETS = [WEEKDAYS]


def _closed_set_conflict(a, b):
    if a == b:
        return False
    for s in CLOSED_VALUE_SETS:
        if a in s and b in s:
            return True
    return False


def _oets_antonym_conflict(a, b, contradicts_pairs):
    return frozenset((a, b)) in contradicts_pairs


def _load_contradicts_pairs(state_dir):
    """Read aurora_oets_web.json's opposite_of-type relations once per
    call, as unordered word-pairs. Fails quiet (empty set) if the file
    is missing/malformed -- source 3 simply contributes nothing, the
    other two sources are unaffected."""
    path = os.path.join(state_dir, "aurora_oets_web.json")
    pairs = set()
    if not os.path.exists(path):
        return pairs
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for rel in data.get("relations", {}).values():
            if rel.get("relation_type") != "opposite_of":
                continue
            src, tgt = rel.get("source_word"), rel.get("target_word")
            if src and tgt:
                pairs.add(frozenset((src, tgt)))
    except Exception:
        return set()
    return pairs


def _recent_window_pairs(pair_log_path, current_turn_id, window_turns):
    """Read relation_pair_log.jsonl, return records from the
    `window_turns` most recent DISTINCT turn_ids strictly before
    current_turn_id (never including the current turn -- collisions
    are always against prior, already-received claims)."""
    if not os.path.exists(pair_log_path):
        return []
    records = []
    try:
        with open(pair_log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []

    prior = [r for r in records if str(r.get("turn_id")) != str(current_turn_id)]
    try:
        cur = int(current_turn_id)
        prior = [r for r in prior if _safe_int(r.get("turn_id")) is not None and _safe_int(r.get("turn_id")) < cur]
    except (TypeError, ValueError):
        pass

    distinct_turn_ids = sorted({r.get("turn_id") for r in prior}, key=lambda t: _safe_int(t) if _safe_int(t) is not None else -1)
    window_ids = set(distinct_turn_ids[-window_turns:]) if distinct_turn_ids else set()
    return [r for r in prior if r.get("turn_id") in window_ids]


def _safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def find_collisions(new_pairs, window_pairs, contradicts_pairs):
    """new_pairs: list of dicts with operator_relation/argument_word/
    negated, for the CURRENT turn. window_pairs: same shape, for prior
    turns in the window. Returns (new_pair, prior_pair, reason)
    tuples for genuine collisions only."""
    collisions = []
    for np_ in new_pairs:
        op, arg, neg = np_["operator_relation"], np_["argument_word"], bool(np_.get("negated"))
        for wp in window_pairs:
            if wp.get("operator_relation") != op:
                continue
            w_arg, w_neg = wp.get("argument_word"), bool(wp.get("negated"))
            if arg == w_arg:
                if neg != w_neg:
                    collisions.append((np_, wp, "negation_flip"))
                continue
            if _closed_set_conflict(arg, w_arg):
                collisions.append((np_, wp, "closed_set_conflict"))
                continue
            if _oets_antonym_conflict(arg, w_arg, contradicts_pairs):
                collisions.append((np_, wp, "oets_antonym"))
    return collisions


def _claim_text(pair):
    return f"{pair.get('operator_relation')} {pair.get('argument_word')}"


def perceive_contradictions(user_text, systems, turn_id):
    """Live hook: fail-quiet. Extracts the CURRENT turn's joints,
    compares them against the recent window already on disk (written
    by the Tier-2 logger, which must run BEFORE this hook so the
    window read below reflects prior turns only -- this turn's own
    pairs are excluded by turn_id), and on genuine collisions, feeds
    the real ContradictionLedger.record() entry point. Returns the
    number of ledger entries created (0 on any degraded path)."""
    if not isinstance(systems, dict):
        return 0
    perception = systems.get("perception")
    lexicon = getattr(perception, "lexicon", None)
    ledger = systems.get("contradiction_ledger")
    if lexicon is None or not hasattr(lexicon, "entries") or ledger is None:
        return 0

    import aurora_expression_perception as aep

    joints = extract_joints(user_text, aep.infer_word_role)
    if not joints:
        return 0

    text_low = user_text.lower()
    new_pairs = [
        {
            "operator_relation": operator,
            "argument_word": argument,
            "negated": is_negated_near(text_low, argument.lower()),
        }
        for operator, argument, _pattern in joints
    ]

    state_dir = str((systems or {}).get("state_dir") or "aurora_state")
    pair_log_path = os.path.join(state_dir, "relation_pair_log.jsonl")
    window_pairs = _recent_window_pairs(pair_log_path, turn_id, WINDOW_TURNS)
    if not window_pairs:
        return 0

    contradicts_pairs = _load_contradicts_pairs(state_dir)
    collisions = find_collisions(new_pairs, window_pairs, contradicts_pairs)

    fired = 0
    for np_, wp, reason in collisions:
        try:
            ledger.record(
                _claim_text(wp), _claim_text(np_),
                source_a=f"turn_{wp.get('turn_id', '?')}",
                source_b=f"turn_{turn_id}",
            )
            fired += 1
        except Exception:
            continue
    return fired
