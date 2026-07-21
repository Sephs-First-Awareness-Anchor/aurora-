"""
Directive M1.1, Amendment M1.1-A -- shared relation-pair extraction.

Both Tier-1 (scripts/m1_1a_tier1_backfill.py, offline archival
backfill) and Tier-2 (the live logger wired into aurora.py's
comprehension stage) import from here, so the extraction/region logic
exists in exactly one place -- "invent nothing parallel" applies to
this campaign's own new code, not just to reusing pre-existing Aurora
machinery.

Extraction patterns (regex over POS-tagged tokens, not a full parser
-- no generic relation extractor previously existed in this codebase,
confirmed before building):
  A. "<X> of <Y>"        -- e.g. "boiling point of water"
  B. "<X> by <Y>"        -- e.g. "caused by pressure"
  C. verb + adjacent noun (simple VO)
  D. adjective + adjacent noun

Region = a word's dominant axis (X/T/N/B/A), read from its lexicon
noncomp_id -- fail-closed the same way D2's Condition-2 fix already
established: a placeholder ("learned:<word>") meaning with low
usage_count carries no real region, matching the campaign's earn-
trust doctrine (third application: relevance scoring, then vocabulary
trust, now envelope region support).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import re

STOPWORDS = {
    "the", "a", "an", "this", "that", "these", "those", "my", "your",
    "his", "her", "its", "our", "their", "and", "or", "but", "if",
    "is", "are", "was", "were", "be", "been", "being", "to", "for",
    "with", "in", "on", "at", "as", "it", "you", "i", "we", "they",
}

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z']{2,}")
_RAW_TOKEN_RE = re.compile(r"[a-zA-Z']+")

_UNVERIFIED_USAGE_FLOOR = 3  # matches SentenceComposer._UNVERIFIED_VOCAB_USAGE_FLOOR

_NEGATION_RE = re.compile(r"\b(not|n't|never|no|isn't|wasn't|won't|doesn't|didn't|can't|cannot|aren't)\b")
_NEGATION_PROXIMITY_CHARS = 40


def is_negated_near(text_low, word):
    """Rough proximity check (not a parser, matching this module's own
    extraction honesty level): does a negation marker appear in the
    span immediately before `word`'s first occurrence in text_low?
    Used by Directive P1 Track CP to detect negation-flip collisions
    without needing a real dependency parse."""
    idx = text_low.find(word)
    if idx == -1:
        return False
    span = text_low[max(0, idx - _NEGATION_PROXIMITY_CHARS):idx]
    return bool(_NEGATION_RE.search(span))


def extract_joints(text, infer_word_role):
    """Pure text -> list of (operator, argument, pattern). `infer_word_role`
    is passed in (from aurora_expression_perception) rather than imported
    at module level, so this module has no hard dependency on the
    composer -- callers that already have it (live pipeline, offline
    scripts) just pass their own reference."""
    joints = []
    text_low = text.lower()
    words = WORD_RE.findall(text_low)
    words = [w for w in words if w not in STOPWORDS]
    if len(words) < 2:
        return joints

    raw_tokens = _RAW_TOKEN_RE.findall(text_low)

    # Pattern A/B: "<X> of|by <Y>"
    for i, tok in enumerate(raw_tokens):
        if tok in ("of", "by") and 0 < i < len(raw_tokens) - 1:
            left = raw_tokens[i - 1]
            right = raw_tokens[i + 1]
            if len(left) >= 3 and len(right) >= 3 and left not in STOPWORDS and right not in STOPWORDS:
                joints.append((left, right, f"X_{tok}_Y"))

    # Pattern C/D: verb/adjective + adjacent noun
    for i in range(len(raw_tokens) - 1):
        w1, w2 = raw_tokens[i], raw_tokens[i + 1]
        if w1 in STOPWORDS or w2 in STOPWORDS or len(w1) < 3 or len(w2) < 3:
            continue
        r1 = infer_word_role(w1)
        r2 = infer_word_role(w2)
        if r1 in ("verb", "adjective") and r2 == "noun":
            joints.append((w1, w2, f"{r1}_noun_adjacent"))

    return joints


def region_from_entry(word, meaning, noncomp_id, usage_count):
    """Pure function: given a lexicon entry's fields, return its axis
    region (X/T/N/B/A) or None if there's no real lived data yet."""
    if not noncomp_id:
        return None
    is_placeholder = str(meaning or "") == f"learned:{word}"
    if not is_placeholder or int(usage_count or 0) >= _UNVERIFIED_USAGE_FLOOR:
        return str(noncomp_id).split(":")[0]
    return None


def log_relation_pairs_from_turn(user_text, systems, turn_id, source="input"):
    """Tier-2 (M1.1-A): live logger on the comprehension stage. Extracts
    joints from RECEIVED text only (never a generated response -- that
    is Tier-3, capped, out of scope here) and appends region-tagged
    pairs to the SAME store/schema Tier-1's offline backfill wrote to.

    Read-only observer of comprehension: any failure here is swallowed
    by the caller (aurora.py wraps this call in its own try/except) so
    a broken logger can never affect the turn being processed.

    Respects `state_dir` explicitly -- writes beside whatever aurora_
    state directory this boot is actually using, not a hardcoded
    __file__-relative path (the isolation-gap pollution pattern this
    campaign has hit and fixed repeatedly elsewhere)."""
    import json
    import os
    import time

    perception = systems.get("perception") if isinstance(systems, dict) else None
    lexicon = getattr(perception, "lexicon", None)
    if lexicon is None or not hasattr(lexicon, "entries"):
        return 0

    import aurora_expression_perception as aep

    joints = extract_joints(user_text, aep.infer_word_role)
    if not joints:
        return 0

    state_dir = str((systems or {}).get("state_dir") or "aurora_state")
    out_path = os.path.join(state_dir, "relation_pair_log.jsonl")

    text_low = user_text.lower()

    written = 0
    lines = []
    for operator, argument, pattern in joints:
        entry = lexicon.entries.get(argument.lower())
        region = None
        if entry is not None:
            region = region_from_entry(
                argument.lower(),
                getattr(entry, "meaning", None),
                getattr(entry, "noncomp_id", None),
                getattr(entry, "usage_count", 0),
            )
        lines.append(json.dumps({
            "operator_relation": operator,
            "argument_word": argument,
            "pattern": pattern,
            "source": source,
            "origin": "live_comprehension",
            "argument_region": region,
            "negated": is_negated_near(text_low, argument.lower()),
            "turn_id": str(turn_id),
            "timestamp": time.time(),
        }))
        written += 1

    if lines:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return written
