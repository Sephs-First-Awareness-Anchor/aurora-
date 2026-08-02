# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Root conftest.py -- external structural audit (2026-08-02): pytest failed
to collect roughly a third of tests/ from a clean checkout because
aurora.py/aurora_internal/* were never importable without the repo root
manually placed on PYTHONPATH. 94 of 144 existing test files worked
around this individually with their own `sys.path.insert(0, REPO_ROOT)`
boilerplate; the other 50 had no such workaround and failed outright.

pytest always imports the nearest conftest.py before collecting any test
module beneath it, regardless of cwd or how pytest was invoked (plain
`pytest`, `python -m pytest`, an IDE runner, etc.) -- so putting the path
fix here, once, makes every test file importable without relying on each
one to repeat it.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
