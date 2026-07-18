"""
Directive B1.1 -- Boundary Envelope shadow scoring.

Shadow deployment: computes per-joint envelope verdicts on every real
received turn and logs them, with ZERO behavioral effect. Read-only
observer, same contract as the Tier-2 relation-pair logger it rides
beside (aurora_relation_pairs.py).

Scorer is M1.3's relation-level design, unchanged in mechanism (the
first-principles review found the mechanism sound -- the flaw was
static-exam gate epistemology, not the scorer):
  SUPPORTED = a direct (operator, argument) pair, or a region-
              generalized (operator, region) key, clears thresholds
              derived from relation_pair_log.jsonl's own distribution.
  UNKNOWN   = no history, no counter-evidence. Metaphor's home.
  (CONTRADICTED is not produced -- no counter-evidence store exists;
  per M1.1's own semantics, absence of support is UNKNOWN by
  construction.)

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json
import os
import time
from collections import Counter, defaultdict

from aurora_internal.aurora_relation_pairs import extract_joints, region_from_entry

DIRECT_THRESHOLD = 2
REGION_COUNT_THRESHOLD = 2
REGION_DIVERSITY_THRESHOLD = 2


def build_pair_index(pairs):
    """pairs: list of relation_pair_log.jsonl records (dicts). Returns
    (direct_pairs, region_keys) -- the same shape M1.3's rescorer used."""
    direct_pairs = defaultdict(int)
    region_keys = defaultdict(lambda: {"instance_count": 0, "distinct_arguments": set()})
    for p in pairs:
        direct_pairs[(p["operator_relation"], p["argument_word"])] += 1
        if p.get("argument_region"):
            key = (p["operator_relation"], p["argument_region"])
            region_keys[key]["instance_count"] += 1
            region_keys[key]["distinct_arguments"].add(p["argument_word"])
    return direct_pairs, region_keys


def _lexicon_region(word, lexicon_entries):
    entry = lexicon_entries.get(word.lower())
    if not entry:
        return None
    return region_from_entry(
        word.lower(), entry.get("meaning"), entry.get("noncomp_id"), entry.get("usage_count"),
    )


def score_joint(operator_words, argument_word, lexicon_entries, direct_pairs, region_keys):
    """Returns (verdict, reason, evidence) where evidence is a dict
    suitable for logging: which pairs/keys backed the verdict, and
    their provenance-source mix."""
    for op in operator_words:
        dc = direct_pairs.get((op, argument_word), 0)
        if dc >= DIRECT_THRESHOLD:
            return "supported", f"direct pair ({op}, {argument_word}) seen {dc}x", {
                "match_kind": "direct_pair", "operator": op, "count": dc,
            }

    region = _lexicon_region(argument_word, lexicon_entries)
    if region:
        for op in operator_words:
            v = region_keys.get((op, region))
            if v and v["instance_count"] >= REGION_COUNT_THRESHOLD and len(v["distinct_arguments"]) >= REGION_DIVERSITY_THRESHOLD:
                return "supported", (
                    f"region-generalized ({op}, region={region}) "
                    f"{v['instance_count']}x across {len(v['distinct_arguments'])} distinct args"
                ), {
                    "match_kind": "region_generalized", "operator": op, "region": region,
                    "instance_count": v["instance_count"],
                    "distinct_arguments": sorted(v["distinct_arguments"])[:10],
                }

    return "unknown", f"no direct pair or region-generalized history (argument_region={region})", {
        "match_kind": "none", "argument_region": region,
    }


def log_envelope_shadow(user_text, systems, turn_id):
    """B1.1 hook: extract joints from RECEIVED text, score each against
    the CURRENT relation_pair_log.jsonl, append verdicts to
    envelope_shadow_log.jsonl. Read-only observer -- any failure here
    must never affect the turn; the caller (aurora.py) wraps this in
    its own try/except, and this function is defensive internally too
    so a partial failure (e.g. one bad joint) doesn't lose the rest."""
    perception = systems.get("perception") if isinstance(systems, dict) else None
    lexicon = getattr(perception, "lexicon", None)
    if lexicon is None or not hasattr(lexicon, "entries"):
        return 0

    import aurora_expression_perception as aep

    joints = extract_joints(user_text, aep.infer_word_role)
    if not joints:
        return 0

    state_dir = str((systems or {}).get("state_dir") or "aurora_state")
    pair_log_path = os.path.join(state_dir, "relation_pair_log.jsonl")
    pairs = []
    if os.path.exists(pair_log_path):
        try:
            with open(pair_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pairs.append(json.loads(line))
                    except Exception:
                        continue
        except Exception:
            pairs = []

    direct_pairs, region_keys = build_pair_index(pairs)

    lexicon_entries = {}
    for w, entry in lexicon.entries.items():
        lexicon_entries[w] = {
            "meaning": getattr(entry, "meaning", None),
            "noncomp_id": getattr(entry, "noncomp_id", None),
            "usage_count": getattr(entry, "usage_count", 0),
        }

    provenance_mix = dict(Counter(str(p.get("source", "unknown")) for p in pairs))

    out_path = os.path.join(state_dir, "envelope_shadow_log.jsonl")
    lines = []
    written = 0
    for operator, argument, pattern in joints:
        try:
            verdict, reason, evidence = score_joint(
                [operator], argument, lexicon_entries, direct_pairs, region_keys,
            )
        except Exception:
            continue
        lines.append(json.dumps({
            "operator_relation": operator,
            "argument_word": argument,
            "pattern": pattern,
            "verdict": verdict,
            "reason": reason,
            "evidence": evidence,
            "provenance_mix": provenance_mix,
            "turn_id": str(turn_id),
            "timestamp": time.time(),
        }))
        written += 1

    if lines:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return written
