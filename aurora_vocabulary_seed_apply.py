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
    """Backfill target_path's OETS nodes/relations from seed_path, skipping
    any word the target already has. Returns stats: added/skipped/rejected
    node counts and added relation count. Creates target_path fresh
    (empty nodes/relations/categories) if it doesn't exist yet -- the
    true first-ever-boot case."""
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

    added, skipped_existing, rejected = [], [], []
    for word, node in seed_nodes.items():
        if not _is_real_word(word):
            rejected.append(word)
            continue
        if word in existing_nodes:
            skipped_existing.append(word)
            continue
        if not _worth_keeping(node):
            rejected.append(word)
            continue
        existing_nodes[word] = node
        added.append(word)

    added_set = set(added)
    new_rel_count = 0
    for rel_id, rel in seed_rels.items():
        if rel_id in existing_rels:
            continue
        src = rel.get("source_word", "")
        tgt = rel.get("target_word", "")
        if src in added_set or tgt in added_set:
            existing_rels[rel_id] = rel
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

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return {
        "added": len(added),
        "skipped_existing": len(skipped_existing),
        "rejected": len(rejected),
        "relations_added": new_rel_count,
        "total_nodes": len(existing_nodes),
        "backup_path": str(backup_path) if backup_path else None,
    }
