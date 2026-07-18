#!/usr/bin/env python3
"""
Directive M1.1, Amendment M1.1-A -- Tier-1 archival backfill.

Minimal operator-argument joint extractor, built from existing POS-
tagging machinery (infer_word_role, the same function ingest_
interaction()/the composer already use), since no generic relation
extractor previously existed in this codebase (confirmed before
building -- UtteranceParser only produces a flat topic_words bag, and
V0's own joints were hand-authored, not machine-extracted).

Received-text grounding rule (this amendment's own addition): sources
RECEIVED text only --
  - aurora_state/classroom_log.jsonl's non-empty seed_prompt fields
    (lesson content Aurora was given, not what she said back)
  - aurora_state/fail_points.json's examples[].user_turns (real
    logged user-turn text from past conversations)
Deliberately excludes assistant_turns / generated content -- that is
Tier-3 (self-generated), capped and out of scope for this backfill.

Extraction patterns (regex over POS-tagged tokens, not a full parser):
  A. "<X> of <Y>"        -- e.g. "boiling point of water"
  B. "<X> by <Y>"        -- e.g. "caused by pressure"
  C. verb + adjacent noun (simple VO)
  D. adjective + adjacent noun
Each hit becomes one (operator_relation, argument_word) pair, tagged
source="archival-input".

Region = the argument word's dominant axis (X/T/N/B/A), read from
lexicon noncomp_id if present, else OETS node lookup -- the SAME axis
vocabulary already used everywhere else in this codebase, not an
invented region taxonomy.

Generalization engine: grammar-motif promotion shape, reused verbatim
in spirit (aurora_grammar_engine.py's StructuralMotif/should_promote).
Abstract key = (operator_relation, argument_region). Accumulate
instance_count + distinct argument words seen (region diversity,
contexts_seen analog). Thresholds are DERIVED from this run's own
data distribution below, not copied from grammar's 5/3/0.30.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import aurora_expression_perception as aep  # noqa: E402
from aurora_internal.aurora_relation_pairs import extract_joints, region_from_entry  # noqa: E402

CLASSROOM_LOG = REPO_ROOT / "aurora_state" / "classroom_log.jsonl"
FAIL_POINTS = REPO_ROOT / "aurora_state" / "fail_points.json"
LEXICON_PATH = REPO_ROOT / "aurora_state" / "lexicon.json"
OETS_PATH = REPO_ROOT / "aurora_state" / "aurora_oets_web.json"
OUT_PATH = REPO_ROOT / "aurora_state" / "relation_pair_log.jsonl"


def load_lexicon():
    with open(LEXICON_PATH) as f:
        return json.load(f)["entries"]


def load_oets():
    with open(OETS_PATH) as f:
        return json.load(f)["nodes"]


def word_region(word, lexicon, oets_nodes):
    """Dominant axis for a word, via the shared region_from_entry() --
    lexicon lookup only (OETS nodes in this schema don't carry a
    noncomp_id, so there is no second axis-bearing source to fall back
    to; oets_nodes is accepted for signature symmetry with earlier
    callers but unused)."""
    entry = lexicon.get(word.lower())
    if not entry:
        return None
    return region_from_entry(word.lower(), entry.get("meaning"), entry.get("noncomp_id"), entry.get("usage_count"))


def collect_received_text():
    texts = []
    if CLASSROOM_LOG.exists():
        with open(CLASSROOM_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                sp = str(d.get("seed_prompt", "") or "").strip()
                if sp:
                    texts.append((sp, "classroom_log:seed_prompt"))
    if FAIL_POINTS.exists():
        with open(FAIL_POINTS) as f:
            fp = json.load(f)
        for dim, rec in (fp.get("records") or {}).items():
            for ex in (rec.get("examples") or []):
                for ut in (ex.get("user_turns") or []):
                    ut = str(ut or "").strip()
                    if ut:
                        texts.append((ut, f"fail_points:{dim}"))
    return texts


def main():
    lexicon = load_lexicon()
    oets_nodes = load_oets()
    texts = collect_received_text()
    print(f"[TIER-1] {len(texts)} received-text sources "
          f"(classroom seed_prompts + fail_points user_turns)")

    all_pairs = []
    for text, src in texts:
        for operator, argument, pattern in extract_joints(text, aep.infer_word_role):
            all_pairs.append({
                "operator_relation": operator,
                "argument_word": argument,
                "pattern": pattern,
                "source": "archival-input",
                "origin": src,
            })

    print(f"[TIER-1] {len(all_pairs)} raw joint instances extracted")

    # Region-tag each pair's argument
    region_tagged = 0
    for p in all_pairs:
        region = word_region(p["argument_word"], lexicon, oets_nodes)
        p["argument_region"] = region
        if region:
            region_tagged += 1
    print(f"[TIER-1] {region_tagged}/{len(all_pairs)} pairs have a real "
          f"lived-axis region for their argument")

    # Accumulate under (operator_relation, argument_region) key --
    # motif-promotion shape: instance_count + distinct-argument diversity.
    accum = defaultdict(lambda: {"instance_count": 0, "distinct_arguments": set()})
    for p in all_pairs:
        if not p["argument_region"]:
            continue
        key = (p["operator_relation"], p["argument_region"])
        accum[key]["instance_count"] += 1
        accum[key]["distinct_arguments"].add(p["argument_word"])

    # Derive promotion thresholds from this run's own data distribution
    # (per the amendment: "calibrate constants from the actual data
    # distributions in the Tier-1 backfill, not by copying grammar's
    # 5/3/0.30 blindly").
    counts = sorted(v["instance_count"] for v in accum.values())
    diversities = sorted(len(v["distinct_arguments"]) for v in accum.values())
    if counts:
        median_count = counts[len(counts) // 2]
        median_diversity = diversities[len(diversities) // 2]
    else:
        median_count = median_diversity = 0

    print(f"[TIER-1] {len(accum)} distinct (operator_relation, region) keys accumulated")
    print(f"[TIER-1] instance_count distribution: min={min(counts) if counts else 0} "
          f"median={median_count} max={max(counts) if counts else 0}")
    print(f"[TIER-1] distinct_arguments distribution: min={min(diversities) if diversities else 0} "
          f"median={median_diversity} max={max(diversities) if diversities else 0}")

    print()
    print("[TIER-1] top 20 (operator_relation, region) keys by instance_count:")
    for key, v in sorted(accum.items(), key=lambda kv: -kv[1]["instance_count"])[:20]:
        print(f"    {key[0]:20s} region={key[1]:3s} "
              f"instances={v['instance_count']:4d} "
              f"distinct_args={len(v['distinct_arguments']):3d} "
              f"e.g.={sorted(v['distinct_arguments'])[:5]}")

    # Write the pair log (matches the new store's future Tier-2 schema:
    # operator_relation, argument_word, argument_region, source).
    with open(OUT_PATH, "w") as f:
        for p in all_pairs:
            f.write(json.dumps(p) + "\n")
    print()
    print(f"[TIER-1] wrote {len(all_pairs)} pair records to {OUT_PATH}")


if __name__ == "__main__":
    main()
