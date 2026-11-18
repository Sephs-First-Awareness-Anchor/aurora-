"""Keeps the category column of docs/LAYER_MODULE_OWNERSHIP.md whole.

The category is a view over the layer map, never a folder: no module is
moved for it. This test reads the map as text only. It imports nothing
from Aurora, so it cannot change behaviour or write state.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_PATH = os.path.join(ROOT, "docs", "LAYER_MODULE_OWNERSHIP.md")
ROW = re.compile(r"^\|\s*`([^`]+\.py)`\s*\|")


def _read_map():
    with open(MAP_PATH, encoding="utf-8") as fh:
        return fh.read().splitlines()


def _categories(lines):
    """Category names from the Categories table."""
    names, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line.strip() == "## Categories"
            continue
        if inside and line.startswith("| ") and not line.startswith("| Category") and not line.startswith("|---"):
            names.append(line.split("|")[1].strip())
    return names


def _listed(lines):
    """(module path, category heading) for every row under 'Every module by category'."""
    rows, inside, heading = [], False, None
    for line in lines:
        if line.startswith("## "):
            inside = line.strip() == "## Every module by category"
            continue
        if not inside:
            continue
        if line.startswith("### "):
            heading = line[4:].strip()
            continue
        m = ROW.match(line)
        if m:
            rows.append((m.group(1), heading))
    return rows


def _modules_on_disk():
    found = set()
    patterns = ["*.py", "aurora_internal/**/*.py", "aurora_manifold_directory/**/*.py"]
    for pattern in patterns:
        for path in glob.glob(os.path.join(ROOT, pattern), recursive=True):
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if "__pycache__" in rel:
                continue
            found.add(rel)
    return found


def test_categories_table_is_present():
    names = _categories(_read_map())
    assert names, "the Categories table is missing"
    assert len(names) == len(set(names))


def test_every_listed_row_sits_under_a_known_category():
    lines = _read_map()
    known = set(_categories(lines))
    rows = _listed(lines)
    assert rows
    stray = [(path, heading) for path, heading in rows if heading not in known]
    assert stray == []


def test_every_module_is_listed_once():
    rows = _listed(_read_map())
    paths = [path for path, _ in rows]
    dupes = sorted({p for p in paths if paths.count(p) > 1})
    assert dupes == []
    missing = sorted(_modules_on_disk() - set(paths))
    assert missing == [], "give these modules a category in docs/LAYER_MODULE_OWNERSHIP.md: %s" % missing


def test_no_listed_module_is_missing_from_disk():
    on_disk = _modules_on_disk()
    gone = sorted(path for path, _ in _listed(_read_map()) if path not in on_disk)
    assert gone == [], "remove these rows (file deleted): %s" % gone
