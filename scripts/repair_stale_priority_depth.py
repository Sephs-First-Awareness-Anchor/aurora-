#!/usr/bin/env python3
"""
Authors: Sunni (Sir) Morningstar & Cael Devo

Directive NC2 — one-time repair pass for the CURRENTLY-LIVE state.

Root cause (verified against aurora_state/aurora_oets_web.json,
2026-08-03, build-584): `OntologicalWeb.add_relation()`'s "relation
already exists, strengthen it" branch returns early WITHOUT calling
`self.nodes[source].add_relation(relation)` / `self.nodes[target].
add_relation(relation)` -- the only path that triggers
`SemanticNode._recalculate_depth()`, which is what applies
`research_priority`'s built-in study_decay (0.5 ** times_researched).
Confirmed live: 98.6% of research-sourced relations show strength above
their own creation value (i.e., re-discovered, not new -- exactly the
early-return path), 63.0% of nodes have never been researched once, and
avg comprehension_confidence/ontological_depth sit at 0.35/0.21 because
most nodes never get recalculated past their initial add_node() state.

This script does NOT reimplement that math. It imports the REAL
SemanticNode class from aurora_internal.aurora_ontological_scaffolding
and calls the REAL `._recalculate_depth()` on every node, using the
exact field mapping aurora_identity_persistence.py's load_web()/
save_web() already use (verified against that source, post-NC1, which
already round-trips noncomp_id). This is a ONE-TIME unsticking of
already-frozen values -- the actual fix (Directive NC2's code change)
is what stops it from re-freezing going forward; run that fix FIRST,
this script SECOND.

SAFETY:
  - Never touches the original file. Always writes a fresh output path.
  - Recomputes `_checksum` exactly as save_web() does.
  - Every relation is still re-attached exactly as originally recorded
    (source/target/type/strength/confidence/knowledge_source/timestamp)
    -- this script changes derived fields only (ontological_depth,
    comprehension_confidence, scaffolding_level, research_priority),
    never the relations or definitions themselves.
"""

import json
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aurora_internal.aurora_ontological_scaffolding import (
    SemanticNode, SemanticRelation, RelationType, UsageExample,
)


def repair(in_path: Path, out_path: Path):
    data = json.load(open(in_path, encoding="utf-8"))
    nodes_data = data.get("nodes", {})
    relations_data = data.get("relations", {})

    # ── Reconstruct real SemanticNode objects (mirrors load_web()) ─────
    live_nodes = {}
    for word, ndata in nodes_data.items():
        node = SemanticNode(
            word=ndata["word"],
            role=ndata.get("role", "noun"),
            emotional_valence=ndata.get("emotional_valence", 0.0),
            lineage=ndata.get("lineage", ""),
            noncomp_id=ndata.get("noncomp_id"),
        )
        node.definitions = ndata.get("definitions", [])
        for exdata in ndata.get("usage_examples", []):
            node.usage_examples.append(UsageExample(
                text=exdata.get("text", ""),
                context=exdata.get("context", ""),
                i_state=exdata.get("i_state", "i_is"),
                fitness=exdata.get("fitness", 0.5),
                timestamp=exdata.get("timestamp", 0.0),
            ))
        node.times_encountered = ndata.get("times_encountered", 0)
        node.times_used_in_expression = ndata.get("times_used_in_expression", 0)
        node.times_researched = ndata.get("times_researched", 0)
        node.first_encountered = ndata.get("first_encountered", 0.0)
        node.last_accessed = ndata.get("last_accessed", 0.0)
        live_nodes[word] = node

    # ── Reattach real relations to real nodes (mirrors load_web()) ─────
    rtype_map = {rt.value: rt for rt in RelationType}
    for rel_id, rdata in relations_data.items():
        rtype = rtype_map.get(rdata.get("relation_type", "related_to"), RelationType.RELATED_TO)
        source, target = rdata.get("source_word", ""), rdata.get("target_word", "")
        if source not in live_nodes or target not in live_nodes:
            continue
        relation = SemanticRelation(
            relation_id=rel_id, source_word=source, target_word=target,
            relation_type=rtype,
            strength=rdata.get("strength", 0.5),
            confidence=rdata.get("confidence", 0.5),
            source_of_knowledge=rdata.get("source_of_knowledge", "restored"),
            timestamp=rdata.get("timestamp", 0.0),
        )
        # Attaching via the node's own relations dict directly here
        # (not node.add_relation()) so THIS reconstruction step doesn't
        # itself trigger a premature recalculation before every relation
        # for that node is attached -- we want one clean recalculation
        # per node below, with its FULL relation set already in place.
        live_nodes[source].relations[rel_id] = relation
        live_nodes[target].relations[rel_id] = relation

    # Perf (2026-08-20): _recalculate_depth() now sums relation
    # contributions from node._rel_contribution_sum (a cache normally kept
    # up to date by SemanticNode.add_relation()) instead of rescanning
    # self.relations.values() every call. Relations were attached directly
    # above, bypassing add_relation(), so every node's cache would still
    # be its 0.0 default without this -- same one-time fix as
    # aurora_identity_persistence.py's load_web().
    for node in live_nodes.values():
        node._rel_contribution_sum = sum(
            r.depth_contribution() for r in node.relations.values()
        )

    # ── The actual repair: real _recalculate_depth() on every node ────
    before = {
        w: (n.ontological_depth, n.comprehension_confidence, n.research_priority)
        for w, n in live_nodes.items()
    }
    for node in live_nodes.values():
        node._recalculate_depth()

    depth_deltas = [live_nodes[w].ontological_depth - before[w][0] for w in live_nodes]
    conf_deltas = [live_nodes[w].comprehension_confidence - before[w][1] for w in live_nodes]
    prio_deltas = [live_nodes[w].research_priority - before[w][2] for w in live_nodes]

    # ── Reserialize (mirrors save_web() exactly, post-NC1 field set) ──
    nodes_out = {}
    for word, node in live_nodes.items():
        nodes_out[word] = {
            "word": node.word, "role": node.role,
            "emotional_valence": node.emotional_valence,
            "definitions": node.definitions,
            "usage_examples": [
                {"text": e.text, "context": e.context, "i_state": e.i_state,
                 "fitness": e.fitness, "timestamp": e.timestamp}
                for e in node.usage_examples
            ],
            "ontological_depth": node.ontological_depth,
            "comprehension_confidence": node.comprehension_confidence,
            "research_priority": node.research_priority,
            "scaffolding_level": node.scaffolding_level,
            "cluster_ids": list(node.cluster_ids),
            "times_encountered": node.times_encountered,
            "times_used_in_expression": node.times_used_in_expression,
            "times_researched": node.times_researched,
            "first_encountered": node.first_encountered,
            "last_accessed": node.last_accessed,
            "lineage": node.lineage,
            "noncomp_id": node.noncomp_id,
        }
    data["nodes"] = nodes_out
    # relations_data is untouched (this script never modifies a relation
    # itself, only the derived per-node fields above)

    data.pop("_checksum", None)
    content = json.dumps(data, sort_keys=True, default=str)
    data["_checksum"] = hashlib.md5(content.encode()).hexdigest()[:12]

    json.dump(data, open(out_path, "w", encoding="utf-8"), indent=1, default=str)

    def avg(xs):
        return sum(xs) / len(xs) if xs else 0.0

    print(f"Nodes repaired:                    {len(live_nodes)}")
    print(f"avg ontological_depth delta:       {avg(depth_deltas):+.4f}")
    print(f"avg comprehension_confidence delta:{avg(conf_deltas):+.4f}")
    print(f"avg research_priority delta:       {avg(prio_deltas):+.4f}")
    unresearched_now_below_threshold = sum(
        1 for w, n in live_nodes.items()
        if n.times_researched == 0 and n.research_priority >= 0.3
    )
    print(f"never-researched nodes still >= MIN_PRIORITY_THRESHOLD(0.3): "
          f"{unresearched_now_below_threshold}")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "aurora_state/aurora_oets_web.json")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else str(src) + ".nc2repaired")
    if dst.resolve() == src.resolve():
        print("Refusing to overwrite the source file. Pass a different output path.")
        sys.exit(1)
    repair(src, dst)
