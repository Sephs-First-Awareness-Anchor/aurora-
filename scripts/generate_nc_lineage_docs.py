#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Dict, List, Tuple

AXES = ("X", "T", "N", "B", "A")
GEN0_ATOMS = [f"NC:{a}>{b}" for a in AXES for b in AXES]
GEN0_SET = set(GEN0_ATOMS)


def load_links(path: Path) -> Dict[str, dict]:
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    links: Dict[str, dict] = {}
    for lid, rec in (raw or {}).items():
        if not isinstance(rec, dict):
            continue
        stats = rec.get("stats", {}) or {}
        obj = {
            "id": str(rec.get("id", lid)),
            "parents": [str(x) for x in (rec.get("parents", []) or [])],
            "depth": int(rec.get("depth", 1) or 1),
            "created_at_tick": int(rec.get("created_at_tick", 0) or 0),
            "count": int(stats.get("count", 0) or 0),
            "dominant_axis": str(rec.get("dominant_relief_axis", "") or ""),
            "mean_relief_total": float(sum((stats.get("mean_relief", {}) or {}).values())),
            "mean_cost_total": float(sum((stats.get("mean_cost", {}) or {}).values())),
            "mean_x_risk": float(stats.get("mean_x_risk", 0.0) or 0.0),
            "tags": [str(t) for t in (rec.get("tags", []) or [])],
        }
        links[obj["id"]] = obj
    return links


def generation_fn(links: Dict[str, dict]):
    cache: Dict[str, int] = {}

    def gen(link_id: str, seen: set | None = None) -> int:
        if link_id in cache:
            return cache[link_id]
        rec = links.get(link_id)
        if rec is None:
            return 0
        if seen is None:
            seen = set()
        if link_id in seen:
            return max(1, int(rec.get("depth", 1)))
        seen.add(link_id)

        parent_vals: List[int] = []
        for p in rec.get("parents", []):
            if p in GEN0_SET:
                parent_vals.append(0)
            elif p in links:
                parent_vals.append(gen(p, seen))
            else:
                parent_vals.append(1)

        g = (max(parent_vals) + 1) if parent_vals else 1
        cache[link_id] = g
        seen.discard(link_id)
        return g

    return gen


def main() -> None:
    base = Path("/storage/emulated/0/Aurora")
    out_dir = base / "aurora_runtime_output"
    links_path = out_dir / "links.json"

    links = load_links(links_path)
    gen = generation_fn(links)

    children = defaultdict(list)
    edge_rows: List[Tuple[str, str, str]] = []
    for lid, rec in links.items():
        for p in rec["parents"]:
            et = "LINK_TO_LINK" if p.startswith("L:") else ("GEN0_ATOM_TO_LINK" if p in GEN0_SET else "ABILITY_TO_LINK")
            edge_rows.append((p, lid, et))
            if p in links:
                children[p].append(lid)

    anc_counts = {}
    desc_counts = {}
    for lid, rec in links.items():
        seen = set()
        stack = [p for p in rec["parents"] if p in links]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend([pp for pp in links[x]["parents"] if pp in links])
        anc_counts[lid] = len(seen)

    for lid in links:
        seen = set()
        q = deque(children.get(lid, []))
        while q:
            c = q.popleft()
            if c in seen:
                continue
            seen.add(c)
            q.extend(children.get(c, []))
        desc_counts[lid] = len(seen)

    gen_dist = Counter(gen(lid) for lid in links)

    # 25x25 matrix: direct Gen1 links whose exact ordered parents are (a,b)
    pair_to_links = defaultdict(list)
    for lid, rec in links.items():
        if gen(lid) != 1:
            continue
        ps = rec.get("parents", [])
        if len(ps) != 2:
            continue
        if ps[0] in GEN0_SET and ps[1] in GEN0_SET:
            pair_to_links[(ps[0], ps[1])].append(lid)

    lineage_dir = out_dir / "lineage_docs"
    anchors_dir = lineage_dir / "anchors"
    lineage_dir.mkdir(parents=True, exist_ok=True)
    anchors_dir.mkdir(parents=True, exist_ok=True)

    matrix_csv = lineage_dir / "nc_25x25_matrix.csv"
    gt5_csv = lineage_dir / "nc_lineage_gt5.csv"
    index_md = lineage_dir / "README.md"

    with matrix_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["left_gen0_atom", "right_gen0_atom", "gen1_link_count", "gen1_link_ids"])
        for left in GEN0_ATOMS:
            for right in GEN0_ATOMS:
                ids = pair_to_links.get((left, right), [])
                w.writerow([left, right, len(ids), "|".join(sorted(ids))])

    gt5_rows = []
    for anchor in GEN0_ATOMS:
        for lid, rec in links.items():
            # anchor participates if reachable in ancestry
            stack = list(rec.get("parents", []))
            seen = set()
            hit = False
            while stack:
                p = stack.pop()
                if p in seen:
                    continue
                seen.add(p)
                if p == anchor:
                    hit = True
                    break
                if p in links:
                    stack.extend(links[p]["parents"])
            if hit and gen(lid) > 5:
                gt5_rows.append((anchor, lid, gen(lid), rec["depth"], rec["count"], rec["dominant_axis"]))

    with gt5_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["anchor_gen0_atom", "link_id", "generation", "depth", "event_count", "dominant_axis"])
        for row in sorted(gt5_rows, key=lambda r: (r[0], -r[2], -r[4], r[1])):
            w.writerow(row)

    gt5_by_anchor = defaultdict(list)
    for row in gt5_rows:
        gt5_by_anchor[row[0]].append(row)

    # one doc per anchor (25 docs)
    for anchor in GEN0_ATOMS:
        doc = anchors_dir / f"{anchor.replace(':','_').replace('>','_to_')}.md"
        with doc.open("w", encoding="utf-8") as f:
            f.write(f"# Anchor Lineage: {anchor}\n\n")
            f.write("## 25x25 Direct Gen1 Outcomes (this anchor as left parent)\n\n")
            f.write("| Right Gen0 Atom | Gen1 Links | Link IDs |\n|---|---:|---|\n")
            for right in GEN0_ATOMS:
                ids = sorted(pair_to_links.get((anchor, right), []))
                f.write(f"| {right} | {len(ids)} | {'; '.join(ids) if ids else ''} |\n")

            f.write("\n## Descendants with Generation > 5\n\n")
            rows = sorted(gt5_by_anchor.get(anchor, []), key=lambda r: (-r[2], -r[4], r[1]))
            f.write("| Link ID | Generation | Depth | Count | Axis |\n|---|---:|---:|---:|---|\n")
            for _, lid, g, d, cnt, ax in rows[:300]:
                f.write(f"| {lid} | {g} | {d} | {cnt} | {ax} |\n")

            f.write("\n")

    with index_md.open("w", encoding="utf-8") as f:
        f.write("# NC Anchor Lineage Documentation\n\n")
        f.write("Generated from `aurora_runtime_output/links.json` using strict generation logic.\n\n")
        f.write("Generation rules:\n")
        f.write("- Gen0: canonical 25 NC atoms (`NC:X>Y`).\n")
        f.write("- Gen1: link with both parents in Gen0.\n")
        f.write("- Gen2+: at least one parent outside Gen0 (including links/non-NC abilities).\n\n")
        f.write(f"- Total links: **{len(links)}**\n")
        f.write(f"- Generation distribution: **{dict(sorted(gen_dist.items()))}**\n")
        f.write(f"- 25x25 matrix rows: **{len(GEN0_ATOMS) * len(GEN0_ATOMS)}**\n")
        f.write(f"- Generation>5 lineage rows: **{len(gt5_rows)}**\n\n")
        f.write("## Files\n\n")
        f.write("- `nc_25x25_matrix.csv`\n")
        f.write("- `nc_lineage_gt5.csv`\n")
        f.write("- `anchors/` (25 per-anchor docs)\n")

    print(f"Wrote {index_md}")
    print(f"Wrote {matrix_csv}")
    print(f"Wrote {gt5_csv}")
    print(f"Wrote {len(list(anchors_dir.glob('*.md')))} anchor docs")


if __name__ == "__main__":
    main()
