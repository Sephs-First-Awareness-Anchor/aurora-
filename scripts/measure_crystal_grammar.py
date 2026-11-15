#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""What her lexical signals say about function words, as crystal links, from a state directory.  READ-ONLY.

    python scripts/measure_crystal_grammar.py --state-dir aurora_state

Reads the hand-authored role lookup (kept, uncounted), the grounding candidates in `lexical_grounding_state.json` (counted only for evidence earned), and any
word classes found (`hyp:lex:structure` on the crystals).  Writes nothing.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal import crystal_grammar as G  # noqa: E402
from aurora_internal.aurora_utterance_parser import _WORD_ROLES  # noqa: E402
from aurora_internal.crystal_associations import AssociationStore  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    a = ap.parse_args()
    role_of = {w: r.value for w, r in _WORD_ROLES.items()}
    s = AssociationStore()
    G.place_scaffold(s, role_of)
    cands = list((json.load(open(os.path.join(a.state_dir, "lexical_grounding_state.json"))).get("candidates") or {}).values())
    G.place_families(s, cands)
    classes = {}
    dps = json.load(open(os.path.join(a.state_dir, "dps_crystals.json")))
    for c in dps["crystals"].values():
        for f in c["facets"].values():
            if f.get("role") == "hyp:lex:structure":
                st = json.loads(str(f.get("content")))
                for k, members in enumerate(st.get("members") or []):
                    if members:
                        classes[f"L{k}@{(st.get('epochs') or [1] * 4)[k]}"] = members
    G.place_classes(s, classes)
    G.join_groups(s, role_of, classes)
    print(f"role lookup: {len(role_of)} words in {len(set(role_of.values()))} role groups (kept, not counted)")
    print(f"grounding candidates: {len(cands)}; earned evidence on {sum(1 for c in cands if any(e.get('provenance') != 'inherited_scaffold' for e in c.get('evidence') or []))}")
    print(f"word classes she has found: {len(classes)}", {k: len(v) for k, v in classes.items()})
    print("links by basis:", s.basis_counts())
    for w in ("and", "or", "but", "that", "because", "so"):
        print(f"  {w:<8} counted generalizations: {G.generalizations(s, w)}")


if __name__ == "__main__":
    main()
