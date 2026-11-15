#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Weave every store in a state directory into facets and typed links, and report what the links would change.  READ-ONLY.

    python scripts/measure_crystal_weave.py --state-dir aurora_state [--hub sunni]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal import crystal_weave as W  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--hub", default="")
    a = ap.parse_args()
    r = W.weave(a.state_dir)
    print(json.dumps(r["summary"], default=str, indent=1))
    dps = json.load(open(os.path.join(a.state_dir, "dps_crystals.json")))
    idx = dps["concept_index"]
    print(json.dumps(W.consequence(r["store"], idx, hub=a.hub or None), default=str, indent=1))
    ids = {c for c in r["book"].concepts()}
    print("woven concepts:", len(ids), "| with a crystal:", len(ids & set(idx)), "| without (no crystal to place into):", len(ids - set(idx)))


if __name__ == "__main__":
    main()
