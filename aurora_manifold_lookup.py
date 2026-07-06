# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_manifold_lookup.py

Read-only, cached accessor for aurora_manifold_directory noncomp data, keyed
by nc_name.

This wraps the existing ManifoldDirectory reader (aurora_manifold_directory_
reader.py) instead of re-implementing directory scanning and JSON loading.
That reader is already the live pipeline aurora.py, aurora_reflexive_
interpreter.py, and aurora_constraint_manifold_compiler.py use to read
noncomp files -- a second, independent way to read the same data would just
be the kind of crossed pipeline this project is trying to avoid.

Never writes to aurora_manifold_directory. load_noncomp() returns None on
any miss (unknown nc_name, missing manifold directory, missing _index.json)
-- callers must handle that gracefully rather than assume a hit.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional

from aurora_manifold_directory_reader import ManifoldDirectory

_MANIFOLD_ROOT = "aurora_manifold_directory"


@lru_cache(maxsize=1)
def _directory() -> Optional[ManifoldDirectory]:
    try:
        return ManifoldDirectory(_MANIFOLD_ROOT)
    except Exception:
        return None


@lru_cache(maxsize=None)
def load_noncomp(nc_name: str) -> Optional[Dict]:
    """Load a noncomp JSON by nc_name. Returns None if not found -- callers
    must handle this gracefully."""
    directory = _directory()
    if directory is None:
        return None
    try:
        return directory.load(nc_name).to_dict()
    except KeyError:
        return None
