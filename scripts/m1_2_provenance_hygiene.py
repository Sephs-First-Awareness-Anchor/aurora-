#!/usr/bin/env python3
"""
Directive M1.2 -- Provenance hygiene for blind-era lexicon entries.

Identifies entries created by ingest_interaction()'s blind auto-learn
path (aurora_expression_perception.py) STRUCTURALLY -- the same
signature D2's Condition-2 fix already uses to cap their relevance
score (meaning == "learned:<word>", the literal placeholder the blind
absorb-and-guess path stamps, never overwritten once set). This is
"identified by creation provenance ... not by guessing at individual
entries": one mechanical predicate over all ~1770 entries, not manual
eyeballing.

Re-tags matching entries' `lineage` field as "legacy-unverified:
<original_lineage>" -- prepended, not overwritten, so the original
provenance (which i-state/process created it) stays visible. Nothing
deleted.

Does NOT change scoring: SentenceComposer._score_composer_candidate's
existing cap already keys off the SAME meaning=="learned:<word>"
signature directly, independent of this tag, so already-graduated
entries (usage_count >= _UNVERIFIED_VOCAB_USAGE_FLOOR) keep scoring at
full trust exactly as before. This script is a visibility/audit pass,
not a new scoring mechanism -- the earn-trust mechanism it references
was already ratified and already runs.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEXICON_PATH = REPO_ROOT / "aurora_state" / "lexicon.json"
BACKUP_PATH = LEXICON_PATH.with_suffix(".json.pre_m1_2_backup")

_TAG_PREFIX = "legacy-unverified:"


def main():
    with open(LEXICON_PATH) as f:
        data = json.load(f)
    with open(BACKUP_PATH, "w") as f:
        json.dump(data, f)

    entries = data.get("entries", {})
    retagged = []
    already_tagged = []
    for word, entry in entries.items():
        meaning = str(entry.get("meaning", "") or "")
        if meaning != f"learned:{word}":
            continue
        lineage = str(entry.get("lineage", "") or "")
        if lineage.startswith(_TAG_PREFIX):
            already_tagged.append(word)
            continue
        entry["lineage"] = f"{_TAG_PREFIX}{lineage}"
        retagged.append(word)

    data["entries"] = entries
    with open(LEXICON_PATH, "w") as f:
        json.dump(data, f)

    print(f"[M1.2] {len(entries)} total lexicon entries scanned")
    print(f"[M1.2] {len(retagged)} entries re-tagged legacy-unverified")
    print(f"[M1.2] {len(already_tagged)} already tagged (idempotent re-run)")

    v0_words = ["water", "france", "japan", "guitar", "photosynthesis"]
    print()
    print("[M1.2] V0 control-word check (per the directive's own report requirement):")
    for w in v0_words:
        entry = entries.get(w)
        if entry is None:
            print(f"    {w:16s} -> NOT IN LEXICON")
            continue
        tagged = str(entry.get("lineage", "")).startswith(_TAG_PREFIX)
        print(f"    {w:16s} -> lineage={entry.get('lineage')!r:45s} "
              f"legacy-unverified={tagged} meaning={entry.get('meaning')!r}")


if __name__ == "__main__":
    main()
