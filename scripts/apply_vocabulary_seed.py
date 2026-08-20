#!/usr/bin/env python3
"""
CLI wrapper for aurora_vocabulary_seed_apply.apply_seed() -- manual,
repo-side application of a corpus-trained vocabulary seed into a target
aurora_oets_web.json. See aurora_vocabulary_seed_apply.py for the merge
contract (backfill only, never overwrites an existing word) and why the
actual logic lives at repo root rather than here.

Usage:
    python3 scripts/apply_vocabulary_seed.py \
        --seed aurora_state/corpora/vocabulary_seed.json \
        --target aurora_state/aurora_oets_web.json
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aurora_vocabulary_seed_apply import apply_seed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", required=True, help="Path to the corpus-trained seed OETS json")
    ap.add_argument("--target", default="aurora_state/aurora_oets_web.json",
                     help="Path to the target aurora_oets_web.json to backfill (default: aurora_state/aurora_oets_web.json)")
    args = ap.parse_args()

    stats = apply_seed(Path(args.seed), Path(args.target))
    print(f"Added {stats['added']} words, skipped {stats['skipped_existing']} (already known), "
          f"rejected {stats['rejected']} (junk/low-value)")
    print(f"Added {stats['relations_added']} relations")
    print(f"Target now has {stats['total_nodes']} nodes total")
    if stats["backup_path"]:
        print(f"Backup written to {stats['backup_path']}")


if __name__ == "__main__":
    main()
