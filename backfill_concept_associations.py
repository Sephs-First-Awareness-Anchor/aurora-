#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
backfill_concept_associations.py — Crystallize existing vocabulary (FIX-A015).

Words that entered the lexicon before concept association existed have no
noncomp_id — 90%+ of her vocabulary is invisible to constraint-driven word
selection. This script replays the training corpora purely for association:
for every sentence, it extracts the comparison geometry (her own extractor),
and every known lexicon word in that sentence votes for a channel derived
from that geometry + the word's functional role. After the replay, leading
votes are assigned and the lexicon is saved.

This is not labeling — it is the association she would have formed if the
wiring had existed when the words first arrived.

Usage:
    python3 backfill_concept_associations.py ../fast_corpus.json ../batch_corpus.json
    python3 backfill_concept_associations.py            # defaults to all corpora
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

DEFAULT_CORPORA = [
    "aurora_state/fast_corpus.json",
    "aurora_state/batch_corpus.json",
    "aurora_state/intensive_corpus.json",
]


def main(paths):
    import warnings
    warnings.filterwarnings("ignore")

    from aurora_expression_perception import (
        ExpressionPerceptionEngine, infer_word_role, infer_word_valence,
    )
    from corpus_runner import (
        AbsorptionField, derive_noncomp_channel,
    )

    perception = ExpressionPerceptionEngine()
    try:
        loaded = perception.lexicon.load()
        print(f"  Lexicon loaded: {perception.lexicon.size} words "
              f"({loaded} from disk)")
    except Exception:
        print(f"  Lexicon: {perception.lexicon.size} words (seeds only)")

    before = perception.lexicon.concept_coverage()
    print(f"  Coverage before: {before['mapped_words']}/{before['total_words']} "
          f"words across {before['channels_populated']} channels")

    field = AbsorptionField()
    known = set(perception.lexicon.entries.keys())
    votes_cast = 0
    sentences_seen = 0

    for path in paths:
        full = path if os.path.isabs(path) else os.path.join(HERE, path)
        if not os.path.exists(full):
            print(f"  [SKIP] {path} not found")
            continue
        try:
            data = json.load(open(full))
        except Exception as e:
            print(f"  [SKIP] {path}: {e}")
            continue
        print(f"  Replaying {os.path.basename(path)} ({len(data)} pairs)...")
        for item in data:
            if not isinstance(item, dict):
                continue
            for k in ("user", "assistant"):
                text = str(item.get(k, "") or "")
                if len(text.split()) < 3:
                    continue
                sentences_seen += 1
                try:
                    geom = field.extractor.extract(text)
                except Exception:
                    continue
                for w in set(t.strip(".,!?;:'\"").lower()
                             for t in text.split()):
                    if w not in known:
                        continue
                    role = infer_word_role(w)
                    val = infer_word_valence(w, "neutral")
                    ch = derive_noncomp_channel(geom, role, val, w)
                    if ch and perception.lexicon.associate(
                            w, ch,
                            strength=max(0.1, geom.constraint_significance)):
                        votes_cast += 1

    after = perception.lexicon.concept_coverage()
    ok = perception.lexicon.save()
    print(f"\n  Sentences replayed: {sentences_seen}")
    print(f"  Association votes:  {votes_cast}")
    print(f"  Coverage after:     {after['mapped_words']}/{after['total_words']} "
          f"words across {after['channels_populated']} channels "
          f"{'[SAVED]' if ok else '[SAVE FAILED]'}")
    print(f"  Channel families:")
    for ch, n in sorted(after["by_channel"].items(),
                        key=lambda kv: -kv[1])[:12]:
        sample = [e.word for e in perception.lexicon.concept_words(ch)[:5]]
        print(f"    {ch:14s} {n:4d} words   e.g. {', '.join(sample)}")


if __name__ == "__main__":
    args = sys.argv[1:] or DEFAULT_CORPORA
    main(args)
