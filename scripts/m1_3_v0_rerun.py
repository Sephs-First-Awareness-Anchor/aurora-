"""
M1.3 -- V0 third run, relation-level scorer (M1.1's corrected design).

Same 16 joints, same predictions on record as V0's first two runs.
Scorer rewritten per Directive M1 + Amendment M1.1-A:
  SUPPORTED = direct (operator, argument) pair has lived history
              (>= DIRECT_THRESHOLD occurrences in relation_pair_log.jsonl),
              OR the operator has region-generalized support for the
              argument's region (>= REGION_COUNT_THRESHOLD instances
              across >= REGION_DIVERSITY_THRESHOLD distinct arguments).
  UNKNOWN    = no history, no counter-evidence. Metaphor's home.
  CONTRADICTED = not used in this run -- no counter-evidence data
              source exists yet (no store of "operator X was tried
              with argument Y and failed"); per M1.1's own semantics
              CONTRADICTED requires positive counter-evidence, which
              this campaign does not yet have a store for. Absence of
              support is UNKNOWN, not CONTRADICTED -- this is itself
              the fix for the inverted S1 result (axis difference is
              no longer even consulted).

Thresholds derived from relation_pair_log.jsonl's own distribution
(991 pairs, all Tier-1 archival as of this run): direct-pair count
median=2, region-key instance_count median=2, region diversity
max=2 (very thin data, honestly reflected in a low bar).
"""
import json
import sys
from collections import defaultdict

import os as _os; sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

DIRECT_THRESHOLD = 2
REGION_COUNT_THRESHOLD = 2
REGION_DIVERSITY_THRESHOLD = 2

pairs = [json.loads(l) for l in open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "aurora_state", "relation_pair_log.jsonl"))]

direct_pairs = defaultdict(int)
region_keys = defaultdict(lambda: {"instance_count": 0, "distinct_arguments": set()})
for p in pairs:
    direct_pairs[(p["operator_relation"], p["argument_word"])] += 1
    if p.get("argument_region"):
        key = (p["operator_relation"], p["argument_region"])
        region_keys[key]["instance_count"] += 1
        region_keys[key]["distinct_arguments"].add(p["argument_word"])


def lexicon_region(word, lexicon):
    entry = lexicon.get(word.lower())
    if not entry:
        return None
    from aurora_internal.aurora_relation_pairs import region_from_entry
    return region_from_entry(word.lower(), entry.get("meaning"), entry.get("noncomp_id"), entry.get("usage_count"))


def score_joint_v2(operator_words, argument_word, lexicon):
    for op in operator_words:
        dc = direct_pairs.get((op, argument_word), 0)
        if dc >= DIRECT_THRESHOLD:
            return "supported", f"direct pair ({op}, {argument_word}) seen {dc}x"

    region = lexicon_region(argument_word, lexicon)
    if region:
        for op in operator_words:
            v = region_keys.get((op, region))
            if v and v["instance_count"] >= REGION_COUNT_THRESHOLD and len(v["distinct_arguments"]) >= REGION_DIVERSITY_THRESHOLD:
                return "supported", (
                    f"region-generalized ({op}, region={region}) "
                    f"{v['instance_count']}x across {len(v['distinct_arguments'])} distinct args: "
                    f"{sorted(v['distinct_arguments'])[:5]}"
                )

    return "unknown", f"no direct pair or region-generalized history (argument_region={region})"


JOINTS = [
    ("category_error", ["square", "root"], "purple"),
    ("category_error", ["divided"], "wednesday"),
    ("category_error", ["authentication", "code"], "archive"),
    ("category_error", ["seventeen", "digit"], "code"),
    ("gibberish", ["threbicultan"], "zqxvornmal"),
    ("gibberish", ["qpwoeiru"], "asdkjfh"),
    ("coherent", ["square", "root"], "144"),
    ("coherent", ["divided"], "2"),
    ("coherent", ["capital"], "france"),
    ("coherent", ["boiling", "point"], "water"),
    ("coherent", ["legs"], "spider"),
    ("coherent", ["population"], "japan"),
    ("coherent", ["chord"], "guitar"),
    ("coherent", ["tell"], "photosynthesis"),
    ("metaphor", ["taste"], "victory"),
    ("metaphor", ["heavy"], "heart"),
    ("metaphor", ["bright"], "idea"),
    ("metaphor", ["weight"], "words"),
]

lexicon = json.load(open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "aurora_state", "lexicon.json")))["entries"]

results = []
for label, ops, arg in JOINTS:
    verdict, reason = score_joint_v2(ops, arg, lexicon)
    results.append({"label": label, "operator": ops, "argument": arg, "verdict": verdict, "reason": reason})
    print(f"[{label:14s}] ({'+'.join(ops):20s}, {arg:12s}) -> {verdict:12s} | {reason}")

print()
from collections import Counter
by_label = {}
for r in results:
    by_label.setdefault(r["label"], Counter())[r["verdict"]] += 1
print("DISTRIBUTIONS:")
for label, counts in by_label.items():
    print(f"  {label:14s}: {dict(counts)}  (n={sum(counts.values())})")

