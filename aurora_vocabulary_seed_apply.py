"""
Merge a corpus-trained OETS vocabulary seed into a target aurora_oets_web.json,
backfilling only -- never overwriting a word Aurora already has her own
comprehension of. Same merge contract as scripts/seed_oets_aurora_vocabulary.py
(backup first, skip existing words, recompute checksum the same way), but
generalized to a bulk seed produced by running corpus_runner.py against a
fresh state rather than a hand-written NEW_NODES dict.

Lives at repo root (not scripts/) because flutter_app's Chaquopy gradle task
excludes scripts/** from the bundled Python sources but copies root-level
*.py unconditionally -- this module is imported both by
scripts/apply_vocabulary_seed.py (manual repo-side runs) and by
aurora_bridge.py (the on-device first-boot backfill).
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

# A seed word only carries real value if it has something Aurora can
# actually draw on -- a definition, a usage example, or research history.
# Bare geometry-extraction placeholders (comprehension_confidence at the
# 0.1 dataclass default, nothing else) would just be noise.
MIN_CONFIDENCE = 0.15


def _is_real_word(word: str) -> bool:
    w = (word or "").strip()
    if len(w) < 2 or len(w) > 40:
        return False
    return w.replace("_", "").replace("-", "").replace("'", "").isalpha()


def _worth_keeping(node: Dict[str, Any]) -> bool:
    if not isinstance(node, dict):
        return False
    if node.get("definitions"):
        return True
    if node.get("usage_examples"):
        return True
    if float(node.get("comprehension_confidence", 0.0) or 0.0) >= MIN_CONFIDENCE:
        return True
    return False


def apply_seed(seed_path: Path, target_path: Path) -> Dict[str, Any]:
    """Backfill target_path's OETS nodes/relations from seed_path.

    Two kinds of real signal come out of an actual corpus_runner.py run,
    and both are merged:
      1. Brand-new words the target doesn't have at all -- added outright
         (never overwrites an existing word).
      2. Words the target ALREADY has (its own baseline vocabulary) that
         the corpus run actually encountered -- confirmed live: running
         corpus_runner.py's observer pass over a real transcript raised
         times_encountered/comprehension_confidence for words like
         "accountability"/"credit"/"radical" that appear in it, well
         above the 0.1 dataclass default other baseline words sit at,
         with NO new definition attached. A node-only merge would throw
         this away entirely on any device, since every fresh install
         already ships the same baseline vocabulary the seed's word list
         mostly overlaps with. Boosted via max(), matching
         SemanticNode._update_comprehension_confidence's own "only ever
         grows, never erodes" contract -- never lowers what a device
         already earned on its own.
    Relations are merged for any word this seed run actually touched
    (new or boosted), deduped by (source, target, type) rather than the
    seed's random relation_id, since two independent runs assign
    different ids to what is logically the same edge.

    Returns stats: added/skipped/rejected/boosted node counts and added
    relation count. Creates target_path fresh (empty nodes/relations/
    categories) if it doesn't exist yet -- the true first-ever-boot case.
    """
    seed_path = Path(seed_path)
    target_path = Path(target_path)

    with open(seed_path, "r", encoding="utf-8") as f:
        seed = json.load(f)
    seed_nodes = seed.get("nodes", {}) or {}
    seed_rels  = seed.get("relations", {}) or {}

    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        backup_path = target_path.with_suffix(".json.pre_seed_backup")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    else:
        data = {"nodes": {}, "relations": {}, "categories": {}}
        backup_path = None

    existing_nodes = data.get("nodes", {}) or {}
    existing_rels  = data.get("relations", {}) or {}

    added, skipped_existing, rejected, boosted = [], [], [], []
    for word, node in seed_nodes.items():
        if not _is_real_word(word):
            rejected.append(word)
            continue
        if word in existing_nodes:
            target_node = existing_nodes[word]
            seed_conf   = float(node.get("comprehension_confidence", 0.0) or 0.0)
            target_conf = float(target_node.get("comprehension_confidence", 0.0) or 0.0)
            seed_enc    = int(node.get("times_encountered", 0) or 0)
            target_enc  = int(target_node.get("times_encountered", 0) or 0)
            if seed_conf > target_conf or seed_enc > target_enc:
                target_node["comprehension_confidence"] = max(seed_conf, target_conf)
                target_node["times_encountered"] = max(seed_enc, target_enc)
                boosted.append(word)
            else:
                skipped_existing.append(word)
            continue
        if not _worth_keeping(node):
            rejected.append(word)
            continue
        existing_nodes[word] = node
        added.append(word)

    touched_set = set(added) | set(boosted)
    existing_rel_keys = {
        (r.get("source_word", ""), r.get("target_word", ""), r.get("relation_type", ""))
        for r in existing_rels.values()
    }
    new_rel_count = 0
    for rel_id, rel in seed_rels.items():
        src = rel.get("source_word", "")
        tgt = rel.get("target_word", "")
        rtype = rel.get("relation_type", "")
        if (src, tgt, rtype) in existing_rel_keys:
            continue
        # Codex review, PR #169: a relation touching a word this run added
        # or boosted is only real once BOTH endpoints actually resolve to a
        # node in the merged file -- the other endpoint may have been
        # rejected by _is_real_word()/_worth_keeping() and never made it
        # into existing_nodes. OETSPersistence.load_web() silently drops
        # any relation with a missing endpoint, so keeping those here would
        # just inflate the file with unloadable records.
        if (src in touched_set or tgt in touched_set) and src in existing_nodes and tgt in existing_nodes:
            existing_rels[rel_id] = rel
            existing_rel_keys.add((src, tgt, rtype))
            new_rel_count += 1

    cats = data.get("categories", {}) or {}
    for word in added:
        role = seed_nodes[word].get("role", "unknown")
        cats.setdefault(role, [])
        if word not in cats[role]:
            cats[role].append(word)

    data["nodes"]      = existing_nodes
    data["relations"]  = existing_rels
    data["categories"] = cats
    data["timestamp"]  = time.time()

    checksum_payload = {k: v for k, v in data.items() if k != "_checksum"}
    content = json.dumps(checksum_payload, sort_keys=True, default=str)
    data["_checksum"] = hashlib.md5(content.encode()).hexdigest()[:12]

    # Codex review, PR #169: write-then-rename instead of writing target_path
    # directly. A direct write left mid-flight (process killed, storage
    # full) truncates the canonical file in place; OETSPersistence.load_web()
    # doesn't know about .pre_seed_backup, so a device's own learned
    # vocabulary would not be recoverable on the next boot. os.replace() is
    # atomic on both POSIX and Android's filesystem.
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, target_path)

    return {
        "added": len(added),
        "boosted": len(boosted),
        "skipped_existing": len(skipped_existing),
        "rejected": len(rejected),
        "relations_added": new_rel_count,
        "total_nodes": len(existing_nodes),
        "backup_path": str(backup_path) if backup_path else None,
    }
