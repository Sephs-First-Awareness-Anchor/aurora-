"""Keeps docs/module_ownership.json, the source and docs/LAYER_MODULE_OWNERSHIP.md as one record.

docs/module_ownership.json places every source file in the repository on her
crystal ladder: the repository is the king quasi, each domain a quasi, each
subsystem a higher order, and files split into composites and base files.
Domains, subsystems, layers and duties are declared; composites and the files
each test exercises are derived from the source. The markdown map is
generated from the record, and the knowledge graph reads the record.

These tests read files and parse source text only. They import nothing from
Aurora, so they cannot change behaviour or write state.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import copy
import importlib.util
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPING_PATH = os.path.join(ROOT, "docs", "module_ownership.json")
MAP_PATH = os.path.join(ROOT, "docs", "LAYER_MODULE_OWNERSHIP.md")
RENDER_PATH = os.path.join(ROOT, "scripts", "render_module_ownership.py")
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|")
BASES = {"reviewed", "name_and_docstring", "location"}
FIELDS = {"domain", "subsystem", "also", "composite", "layer", "layer_role", "language", "basis", "duties"}
LANGUAGE_BY_EXTENSION = {".py": "python", ".dart": "dart", ".rs": "rust", ".kt": "kotlin", ".java": "java",
                         ".sh": "shell", ".bat": "batch", ".ps1": "powershell", ".jsx": "jsx", ".html": "html",
                         ".service": "systemd", ".yml": "yaml", ".yaml": "yaml"}


def _renderer():
    spec = importlib.util.spec_from_file_location("render_module_ownership", RENDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def render():
    return _renderer()


@pytest.fixture(scope="module")
def mapping(render):
    return render.load_mapping(MAPPING_PATH)


def _read_map():
    with open(MAP_PATH, encoding="utf-8") as fh:
        return fh.read()


# ---- the record itself -----------------------------------------------------

def test_mapping_has_no_duplicate_keys():
    def strict(pairs):
        keys = [k for k, _ in pairs]
        assert len(keys) == len(set(keys)), "duplicate keys: %s" % sorted({k for k in keys if keys.count(k) > 1})
        return dict(pairs)

    with open(MAPPING_PATH, encoding="utf-8") as fh:
        json.loads(fh.read(), object_pairs_hook=strict)


def test_schema_authors_and_ladder(mapping):
    assert mapping["schema"] == "aurora.module_ownership/2"
    assert mapping["authors"] == "Sunni (Sir) Morningstar and Cael Devo"
    assert [r["order"] for r in mapping["ladder"]] == ["king_quasi", "quasi", "higher_order", "composite", "base"]


def test_every_source_file_is_recorded_and_nothing_else(mapping, render):
    on_disk = render.scan(ROOT, mapping["scope"])
    recorded = set(mapping["files"])
    assert sorted(on_disk - recorded) == [], "add these to docs/module_ownership.json"
    assert sorted(recorded - on_disk) == [], "remove these from docs/module_ownership.json (file gone)"


def test_every_entry_uses_known_ids(mapping):
    domains = [d["id"] for d in mapping["domains"]]
    subs = {s["id"]: s for s in mapping["subsystems"]}
    layers = [l["id"] for l in mapping["layers"]]
    assert len(domains) == len(set(domains))
    assert len(subs) == len(mapping["subsystems"]) and len(layers) == len(set(layers))
    assert all(s["domain"] in domains for s in subs.values())
    bad = []
    for path, f in mapping["files"].items():
        expected = FIELDS | ({"exercises"} if f.get("subsystem") == "tests" else set())
        if set(f) != expected:
            bad.append((path, "fields", sorted(f)))
            continue
        if f["domain"] not in domains:
            bad.append((path, "domain", f["domain"]))
        if f["subsystem"] not in subs or subs[f["subsystem"]]["domain"] != f["domain"]:
            bad.append((path, "subsystem", f["subsystem"]))
        if any(a not in subs or a == f["subsystem"] for a in f["also"]):
            bad.append((path, "also", f["also"]))
        if f["layer"] is not None and (f["layer"] not in layers or f["domain"] != "desktop"):
            bad.append((path, "layer", f["layer"]))
        if (f["layer"] is None) != (f["layer_role"] is None):
            bad.append((path, "layer_role", f["layer_role"]))
        ext = os.path.splitext(path)[1]
        if f["language"] != LANGUAGE_BY_EXTENSION.get(ext):
            bad.append((path, "language", f["language"]))
        if f["basis"] not in BASES:
            bad.append((path, "basis", f["basis"]))
        if (f["basis"] == "reviewed") != bool(f["duties"]):
            bad.append((path, "duties", f["duties"]))
    assert bad == []


def test_layer_records_without_file_really_have_no_file(mapping):
    layers = {l["id"] for l in mapping["layers"]}
    for r in mapping["layer_records_without_file"]:
        assert r["layer"] in layers
        assert not os.path.exists(os.path.join(ROOT, r["path"])), "%s exists now: move it into files" % r["path"]
        assert r["path"] not in mapping["files"]


def test_coverage_boundary_is_stated(mapping):
    scope = mapping["scope"]
    assert scope["statement"] and scope["not_covered"]
    languages = {f["language"] for f in mapping["files"].values()}
    for needed in ("python", "dart", "rust", "kotlin"):
        assert needed in languages, needed
    domains = {f["domain"] for f in mapping["files"].values()}
    assert domains == {d["id"] for d in mapping["domains"]}, "every domain holds files"


# ---- derived parts are evidence, not declarations ---------------------------

def test_composites_and_exercises_match_the_source(mapping, render):
    fresh = render.apply_derived(ROOT, copy.deepcopy(mapping))
    assert fresh["composites"] == mapping["composites"], "composites are stale: run --update-derived"
    stale = [p for p, f in fresh["files"].items() if f != mapping["files"][p]]
    assert stale == [], "derived fields are stale for %s: run --update-derived" % stale[:10]


def test_every_composite_is_a_connected_group_inside_one_subsystem(mapping):
    files = mapping["files"]
    for cid, c in mapping["composites"].items():
        members = set(c["members"])
        assert len(members) >= 2, cid
        assert cid.split(".")[0] == c["subsystem"]
        assert all(files[p]["subsystem"] == c["subsystem"] and files[p]["domain"] == c["domain"] for p in members), cid
        assert all(files[p]["composite"] == cid for p in members), cid
        assert c["hub"] in members
        seen, stack = set(), [c["hub"]]
        adjacent = {p: set() for p in members}
        for a, b in c["links"]:
            assert a in members and b in members, cid
            adjacent[a].add(b)
            adjacent[b].add(a)
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(adjacent[node] - seen)
        assert seen == members, "%s is not connected" % cid
    listed = {p for c in mapping["composites"].values() for p in c["members"]}
    assert listed == {p for p, f in files.items() if f["composite"]}


# ---- the generated map agrees with the record -------------------------------

def test_markdown_map_is_generated_from_the_record(mapping, render):
    assert _read_map() == render.render(mapping), (
        "docs/LAYER_MODULE_OWNERSHIP.md differs from docs/module_ownership.json: "
        "run python scripts/render_module_ownership.py")


def test_layer_assignments_agree_everywhere_in_the_map(mapping):
    """Each layer section and the per-subsystem tables give a module the same layer as the record."""
    heads = {}
    for l in mapping["layers"]:
        heads["### Orchestrator" if l["id"] == "orchestrator" else "### %s (%s)" % (l["id"], l["name"])] = l["id"]
    in_sections, in_tables = {}, {}
    part, section = None, None
    for line in _read_map().splitlines():
        if line.startswith("## "):
            part, section = line.strip(), None
            continue
        if line.startswith("### "):
            section = line.strip()
            continue
        m = ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if part == "## Desktop layers (L1 to L8)" and section in heads:
            assert m.group(1) not in in_sections, "%s is in two layer sections" % m.group(1)
            in_sections[m.group(1)] = heads[section]
        elif part == "## Every file by domain and subsystem":
            assert m.group(1) not in in_tables, "%s is listed twice" % m.group(1)
            in_tables[m.group(1)] = cells[2] or None
    record = {p: f["layer"] for p, f in mapping["files"].items()}
    expected_sections = {p: l for p, l in record.items() if l}
    expected_sections.update({r["path"]: r["layer"] for r in mapping["layer_records_without_file"]})
    assert in_sections == expected_sections
    assert in_tables == record


# ---- names are not job descriptions ----------------------------------------

def test_investigative_modules_used_by_operational_code_were_reviewed(mapping, render):
    """An investigative module that operational code imports may carry an operational duty.

    Its name and docstring are not enough: it must be read and its duties
    written down, or it must move to the subsystem it really serves.
    """
    files = mapping["files"]
    not_operational = {"investigative", "tests", "tooling"}
    users = {}
    for a, bs in render.python_edges(ROOT, files).items():
        for b in bs:
            users.setdefault(b, set()).add(a)
    unreviewed = []
    for path, who in users.items():
        f = files[path]
        if f["subsystem"] != "investigative" or f["basis"] == "reviewed":
            continue
        operational = sorted(u for u in who if files[u]["subsystem"] not in not_operational)
        if operational:
            unreviewed.append((path, operational))
    assert unreviewed == [], "review these and record their duties: %s" % unreviewed
