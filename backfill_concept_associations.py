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
    from corpus_runner import AbsorptionField
    from aurora_concept_derivation import assign_batch

    perception = ExpressionPerceptionEngine()
    try:
        loaded = perception.lexicon.load()
        print(f"  Lexicon loaded: {perception.lexicon.size} words "
              f"({loaded} from disk)")
    except Exception:
        print(f"  Lexicon: {perception.lexicon.size} words (seeds only)")

    # Load OETS web if available so new concepts get ontological nodes too.
    oets = None
    oets_persist = None
    try:
        from aurora_internal.aurora_ontological_scaffolding import (
            OntologicalScaffoldingEngine,
        )
        from aurora_internal.aurora_identity_persistence import OETSPersistence
        oets = OntologicalScaffoldingEngine()
        oets_persist = OETSPersistence(state_dir=os.path.join(HERE, "aurora_state"))
        oets_persist.load_web(oets)
        print(f"  OETS loaded: {len(getattr(oets.web, 'nodes', {}) or {})} concept nodes")
    except Exception as e:
        print(f"  OETS unavailable ({e}) — channels only, no concept nodes")
        oets = None

    before = perception.lexicon.concept_coverage()
    print(f"  Coverage before: {before['mapped_words']}/{before['total_words']} "
          f"words across {before['channels_populated']} channels")

    field = AbsorptionField()
    sentences_seen = 0
    words_assigned = 0

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
            for role_key, i_state in (("user", "i_do"), ("assistant", "i_did")):
                text = str(item.get(role_key, "") or "")
                if len(text.split()) < 3:
                    continue
                sentences_seen += 1

                # Build the word batch for this sentence
                batch = []
                for raw in set(t.strip(".,!?;:'\"").lower() for t in text.split()):
                    if raw not in perception.lexicon.entries:
                        continue
                    r = infer_word_role(raw)
                    v = infer_word_valence(raw, "neutral")
                    if r in ("verb", "noun", "adjective", "adverb"):
                        batch.append((raw, r, v))

                if not batch:
                    continue

                assigned = assign_batch(
                    batch, text, perception.lexicon,
                    oets=oets,
                    i_state=i_state,
                    perception=perception,
                )
                words_assigned += len(assigned)

    after = perception.lexicon.concept_coverage()
    ok = perception.lexicon.save()

    # Save OETS with new concept nodes if we created any
    if oets is not None and oets_persist is not None:
        try:
            ok = oets_persist.save_web(oets)
            node_count = len(getattr(oets.web, 'nodes', {}) or {})
            print(f"  OETS saved: {node_count} concept nodes {'[OK]' if ok else '[FAILED]'}")
        except Exception as e:
            print(f"  OETS save error: {e}")

    print(f"\n  Sentences replayed: {sentences_seen}")
    print(f"  Words assigned:     {words_assigned}")
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
