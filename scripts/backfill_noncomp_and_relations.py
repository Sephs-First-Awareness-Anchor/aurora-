#!/usr/bin/env python3
"""
Authors: Sunni (Sir) Morningstar & Cael Devo

BACKFILL: noncomp_id population + honest relation re-typing on the live
OETS web state (aurora_oets_web.json), operating directly on the JSON
so it can run without a full Aurora boot.

WHAT THIS FIXES (root causes, verified by direct inspection of the live
state, aurora_state/aurora_oets_web.json, 2026-08-03):

  1. `noncomp_id` is a real field on SemanticNode
     (aurora_internal/aurora_ontological_scaffolding.py) but was never
     written OR read by the persistence layer
     (aurora_internal/aurora_identity_persistence.py save_web/load_web)
     -- so even a populated value would be silently dropped every
     save/load cycle. This script assumes the persistence patch
     (see accompanying diff) has ALSO been applied, so future saves
     keep what this backfill writes. Confirmed live: 0/1104 nodes carry
     a noncomp_id today.

  2. 99.0% of live relations (18,394 / 18,571) are the generic
     RELATED_TO type, sourced from `infer_relations_from_context()`'s
     exhaustive pairwise co-occurrence loop, which is role-blind. The
     SAME function already has working role-pair heuristics two lines
     below (verb+noun -> ENABLES, adjective+noun -> CONTEXT_OF) but
     only ever applies them to adjacency pairs, not the full pairwise
     set. This script re-types EXISTING relations that fit those two
     already-proven patterns and leaves everything else honestly as
     RELATED_TO -- it does not invent new relation types or guess at
     pairs the live code itself wouldn't have classified.

NONCOMP_ID ASSIGNMENT -- Directive NC1, ratified 2026-08-03 (Sunni & Cael):
  Reuses the canonical AXIS_NC_DIM mapping from
  aurora_internal/aurora_noncomp_registry.py (X->OPERATOR,
  T->DIFFERENCE, N->COST, B->MAGNITUDE, A->POLARITY) exactly as
  defined there -- no new dimension names invented. The axis-per-role
  assignment below is the ratified mapping (also live in
  aurora_internal/aurora_ontological_scaffolding.py's ROLE_TO_AXIS,
  used by add_node() for all future nodes):

      noun         -> X   (entities are the existence-axis)
      verb         -> T   (actions unfold across the temporal axis)
      adjective    -> B   (qualities bound/scope a concept)
      adverb       -> N   (manner/intensity modifies energy expenditure)
      pronoun      -> A   (self/other reference is the agency axis)
      preposition  -> B   (relational/spatial boundary connective)
      determiner   -> X   (scope-setting, grouped with noun)
      anything else (e.g. "training_gap") -> left unpopulated (None)

SAFETY:
  - Never touches the original file. Always writes a fresh output path.
  - Recomputes `_checksum` exactly the way
    aurora_identity_persistence.py's save_web() does
    (md5 of json.dumps(data, sort_keys=True, default=str)[:12]).
  - Only re-types relations matching an EXISTING, already-live heuristic
    at the same strength/confidence values that heuristic already uses
    -- no fabricated specificity.
  - Idempotent: re-running on its own output is a safe no-op (checks
    `noncomp_id is not None` / already-non-RELATED_TO before touching).
"""

import json
import hashlib
import sys
from pathlib import Path

# ── canonical source of truth, reused verbatim (no new taxonomy) ───────────
AXIS_NC_DIM = {
    "X": "OPERATOR",
    "T": "DIFFERENCE",
    "N": "COST",
    "B": "MAGNITUDE",
    "A": "POLARITY",
}

ROLE_TO_AXIS = {
    "noun": "X",
    "verb": "T",
    "adjective": "B",
    "adverb": "N",
    "pronoun": "A",
    "preposition": "B",
    "determiner": "X",
}

APPLY_NONCOMP = True     # set False to skip noncomp_id population entirely
APPLY_RELATIONS = True   # set False to skip relation re-typing entirely


def noncomp_id_for_role(role: str):
    axis = ROLE_TO_AXIS.get(role)
    if axis is None:
        return None
    return f"{axis}:{AXIS_NC_DIM[axis]}"


def backfill(in_path: Path, out_path: Path):
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", {})
    relations = data.get("relations", {})

    # ── Pass 1: noncomp_id ──────────────────────────────────────────────
    noncomp_written = 0
    noncomp_skipped_unknown_role = 0
    if APPLY_NONCOMP:
        for word, node in nodes.items():
            if node.get("noncomp_id"):
                continue  # already populated (idempotent)
            ncid = noncomp_id_for_role(node.get("role", ""))
            if ncid is None:
                noncomp_skipped_unknown_role += 1
                continue
            node["noncomp_id"] = ncid
            noncomp_written += 1

    # ── Pass 2: honest relation re-typing ───────────────────────────────
    # Mirrors infer_relations_from_context()'s existing adjacency
    # heuristics exactly (same relation types, same strength/confidence),
    # applied retroactively to any RELATED_TO relation whose source/
    # target role pair matches -- in EITHER direction, since the live
    # pairwise co-occurrence loop that created these is unordered.
    retyped = 0
    retype_counts = {}
    if APPLY_RELATIONS:
        role_of = {w: n.get("role", "") for w, n in nodes.items()}
        for rel_id, rel in relations.items():
            if rel.get("relation_type") != "related_to":
                continue
            if rel.get("source_of_knowledge") != "co-occurrence":
                continue  # only touch the exhaustive pairwise source
            src_role = role_of.get(rel.get("source_word", ""))
            tgt_role = role_of.get(rel.get("target_word", ""))
            new_type = None
            if src_role == "verb" and tgt_role == "noun":
                new_type = "enables"
            elif tgt_role == "verb" and src_role == "noun":
                new_type = "enables"
            elif src_role == "adjective" and tgt_role == "noun":
                new_type = "context_of"
            elif tgt_role == "adjective" and src_role == "noun":
                new_type = "context_of"
            if new_type is None:
                continue
            rel["relation_type"] = new_type
            # Keep the adjacency heuristic's own confidence/strength
            # ceiling so a retroactive pass never claims MORE certainty
            # than the live-turn version of the same heuristic would.
            rel["strength"] = min(rel.get("strength", 0.2), 0.35)
            rel["confidence"] = min(rel.get("confidence", 0.3), 0.3)
            rel["source_of_knowledge"] = "backfill_role_heuristic"
            retyped += 1
            retype_counts[new_type] = retype_counts.get(new_type, 0) + 1

    # ── Recompute checksum exactly as save_web() does ───────────────────
    data.pop("_checksum", None)
    content = json.dumps(data, sort_keys=True, default=str)
    data["_checksum"] = hashlib.md5(content.encode()).hexdigest()[:12]

    # Match aurora_identity_persistence.py's own _write_web_payload()
    # on-disk formatting (indent=1) -- the checksum itself is computed
    # over the unindented json.dumps(..., sort_keys=True) form either
    # way, so this only affects readability/diff quality, not content.
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, default=str)

    print(f"Nodes total:              {len(nodes)}")
    print(f"noncomp_id written:       {noncomp_written}")
    print(f"noncomp_id skipped (unmapped role): {noncomp_skipped_unknown_role}")
    print(f"Relations total:          {len(relations)}")
    print(f"Relations re-typed:       {retyped}")
    for t, c in sorted(retype_counts.items()):
        print(f"  -> {t}: {c}")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "aurora_state/aurora_oets_web.json")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else str(src) + ".backfilled")
    if not src.exists():
        print(f"Input not found: {src}")
        sys.exit(1)
    # Never overwrite the source, even if dst == src was passed by mistake.
    if dst.resolve() == src.resolve():
        print("Refusing to overwrite the source file. Pass a different output path.")
        sys.exit(1)
    backfill(src, dst)
