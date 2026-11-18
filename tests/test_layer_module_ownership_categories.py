"""Keeps docs/module_ownership.json and docs/LAYER_MODULE_OWNERSHIP.md as one record.

docs/module_ownership.json is the one machine-readable record of each covered
module's layer and function category. The markdown map is generated from it,
and the knowledge graph reads it. These tests read files and parse source text
only. They import nothing from Aurora, so they cannot change behaviour or
write state.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import ast
import glob
import importlib.util
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPING_PATH = os.path.join(ROOT, "docs", "module_ownership.json")
MAP_PATH = os.path.join(ROOT, "docs", "LAYER_MODULE_OWNERSHIP.md")
RENDER_PATH = os.path.join(ROOT, "scripts", "render_module_ownership.py")
ROW = re.compile(r"^\|\s*`([^`]+\.py)`\s*\|")
BASES = {"reviewed", "name_and_docstring"}


def _renderer():
    spec = importlib.util.spec_from_file_location("render_module_ownership", RENDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mapping():
    return _renderer().load_mapping(MAPPING_PATH)


def _modules_on_disk(scope):
    found = set()
    for pattern in scope["covers"]:
        for path in glob.glob(os.path.join(ROOT, pattern), recursive=True):
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if any(skip in rel.split("/") for skip in scope["skips"]):
                continue
            found.add(rel)
    return found


def _read_map():
    with open(MAP_PATH, encoding="utf-8") as fh:
        return fh.read()


# ---- the record itself -----------------------------------------------------

def test_mapping_has_no_duplicate_keys():
    with open(MAPPING_PATH, encoding="utf-8") as fh:
        text = fh.read()

    def strict(pairs):
        keys = [k for k, _ in pairs]
        assert len(keys) == len(set(keys)), "duplicate keys: %s" % sorted({k for k in keys if keys.count(k) > 1})
        return dict(pairs)

    json.loads(text, object_pairs_hook=strict)


def test_schema_and_authors(mapping):
    assert mapping["schema"] == "aurora.module_ownership/1"
    assert mapping["authors"] == "Sunni (Sir) Morningstar and Cael Devo"


def test_every_module_on_disk_is_recorded_and_nothing_else(mapping):
    on_disk = _modules_on_disk(mapping["scope"])
    recorded = set(mapping["modules"])
    assert sorted(on_disk - recorded) == [], "add these to docs/module_ownership.json"
    assert sorted(recorded - on_disk) == [], "remove these from docs/module_ownership.json (file gone)"


def test_every_entry_uses_known_ids(mapping):
    cats = [c["id"] for c in mapping["categories"]]
    layers = [l["id"] for l in mapping["layers"]]
    assert len(cats) == len(set(cats)) and len(layers) == len(set(layers))
    bad = []
    for path, m in mapping["modules"].items():
        if set(m) != {"category", "also", "layer", "layer_role", "basis", "duties"}:
            bad.append((path, "fields", sorted(m)))
        if m["category"] not in cats:
            bad.append((path, "category", m["category"]))
        if any(a not in cats or a == m["category"] for a in m["also"]):
            bad.append((path, "also", m["also"]))
        if m["layer"] is not None and m["layer"] not in layers:
            bad.append((path, "layer", m["layer"]))
        if (m["layer"] is None) != (m["layer_role"] is None):
            bad.append((path, "layer_role", m["layer_role"]))
        if m["basis"] not in BASES:
            bad.append((path, "basis", m["basis"]))
        if (m["basis"] == "reviewed") != bool(m["duties"]):
            bad.append((path, "duties", m["duties"]))
    assert bad == []


def test_layer_records_without_file_really_have_no_file(mapping):
    on_disk = _modules_on_disk(mapping["scope"])
    layers = {l["id"] for l in mapping["layers"]}
    for r in mapping["layer_records_without_file"]:
        assert r["layer"] in layers
        assert r["path"] not in on_disk, "%s exists now: move it into modules" % r["path"]
        assert r["path"] not in mapping["modules"]


def test_coverage_boundary_is_stated(mapping):
    scope = mapping["scope"]
    assert "not an ownership map of the whole repository" in scope["statement"]
    for path in ("flutter_app/", "aurora-acm/", "scripts/", "tests/"):
        assert any(item["path"] == path for item in scope["not_covered"]), path
    for item in scope["not_covered"]:
        top = item["path"].split("/")[0]
        assert not any(m.split("/")[0] == top for m in mapping["modules"] if "/" in m), item["path"]


# ---- the generated map agrees with the record -------------------------------

def test_markdown_map_is_generated_from_the_record(mapping):
    assert _read_map() == _renderer().render(mapping), (
        "docs/LAYER_MODULE_OWNERSHIP.md differs from docs/module_ownership.json: "
        "run python scripts/render_module_ownership.py")


def test_layer_assignments_agree_everywhere_in_the_map(mapping):
    """Each layer section and the per-category tables give a module the same layer as the record."""
    layer_heads = {}
    for l in mapping["layers"]:
        head = "## Orchestrator" if l["id"] == "orchestrator" else "## %s (%s)" % (l["id"], l["name"])
        layer_heads[head] = l["id"]
    in_sections, in_tables, section, inside_all = {}, {}, None, False
    for line in _read_map().splitlines():
        if line.startswith("## "):
            section = layer_heads.get(line.strip())
            inside_all = line.strip() == "## Every module by category"
            continue
        m = ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if section:
            assert m.group(1) not in in_sections, "%s is in two layer sections" % m.group(1)
            in_sections[m.group(1)] = section
        elif inside_all:
            assert m.group(1) not in in_tables, "%s is listed twice" % m.group(1)
            in_tables[m.group(1)] = cells[1] or None
    record = {p: m["layer"] for p, m in mapping["modules"].items()}
    expected_sections = {p: l for p, l in record.items() if l}
    expected_sections.update({r["path"]: r["layer"] for r in mapping["layer_records_without_file"]})
    assert in_sections == expected_sections
    assert in_tables == record


def test_category_counts_add_up(mapping):
    counts = {c["id"]: 0 for c in mapping["categories"]}
    for m in mapping["modules"].values():
        counts[m["category"]] += 1
    assert sum(counts.values()) == len(mapping["modules"])


# ---- names are not job descriptions ----------------------------------------

def _module_name(path):
    name = path[:-3].replace("/", ".")
    return name[: -len(".__init__")] if name.endswith(".__init__") else name


def _importers(mapping):
    """Covered module -> covered modules that import it anywhere in their source."""
    names = {_module_name(p): p for p in mapping["modules"]}

    def resolve(n):
        while n:
            if n in names:
                return names[n]
            n = n.rsplit(".", 1)[0] if "." in n else ""
        return None

    found = {p: set() for p in mapping["modules"]}
    for path in mapping["modules"]:
        with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read())
        name = _module_name(path)
        pkg = name if path.endswith("__init__.py") else (name.rsplit(".", 1)[0] if "." in name else "")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = pkg.split(".") if pkg else []
                    if node.level > 1:
                        parts = parts[: len(parts) - (node.level - 1)]
                    base = ".".join(parts + ([base] if base else []))
                targets = [base + "." + a.name if base else a.name for a in node.names] + [base]
            else:
                continue
            for t in targets:
                hit = resolve(t)
                if hit and hit != path:
                    found[hit].add(path)
    return found


def test_investigative_modules_used_by_operational_code_were_reviewed(mapping):
    """An investigative module that operational code imports may carry an operational duty.

    Its name and docstring are not enough: it must be read and its duties
    written down, or it must move to the category it really serves.
    """
    modules = mapping["modules"]
    unreviewed = []
    for path, users in _importers(mapping).items():
        if modules[path]["category"] != "investigative" or modules[path]["basis"] == "reviewed":
            continue
        operational = sorted(u for u in users if modules[u]["category"] != "investigative")
        if operational:
            unreviewed.append((path, operational))
    assert unreviewed == [], "review these and record their duties: %s" % unreviewed
