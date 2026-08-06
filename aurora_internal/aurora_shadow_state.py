"""
aurora_shadow_state.py
=======================

Build 598: Recursive Causal Experience Chamber -- Stage 6 of 6.
Shadow persistence, built for real.

This pattern previously existed only informally, ad hoc, inside one-off
diagnostic scripts (e.g. scripts/w1_thought_state_diagnostic.py) via
tempfile.mkdtemp() + shutil.copytree() + booting a second, fully
independent Aurora instance against the copy. This module formalizes that
exact pattern into a reusable production utility -- nothing about the
underlying approach changes, it is simply named, tested, and made callable
from more than one script.

open_shadow_state() isolates a copy of a live state_dir; changes inside the
shadow never appear in the original until promote_shadow_deltas() is
called explicitly, and only the named keys move -- never a blanket
overwrite.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Sequence


@dataclass(frozen=True)
class ShadowStateHandle:
    live_state_dir: Path
    shadow_state_dir: Path
    scratch_root: Path


@contextmanager
def open_shadow_state(state_dir: str) -> Iterator[ShadowStateHandle]:
    """Copies the live state_dir to a temp location and yields a handle to
    it. The temp copy (and everything written into it) is discarded when
    the context manager exits, unless promote_shadow_deltas() was called
    first to copy specific named keys back out."""
    live_dir = Path(state_dir).resolve()
    if not live_dir.exists() or not live_dir.is_dir():
        raise FileNotFoundError(f"state_dir does not exist or is not a directory: {live_dir}")

    scratch_root = Path(tempfile.mkdtemp(prefix="aurora_shadow_state_"))
    shadow_dir = scratch_root / live_dir.name
    try:
        shutil.copytree(str(live_dir), str(shadow_dir))
        yield ShadowStateHandle(live_state_dir=live_dir, shadow_state_dir=shadow_dir, scratch_root=scratch_root)
    finally:
        shutil.rmtree(str(scratch_root), ignore_errors=True)


def promote_shadow_deltas(handle: ShadowStateHandle, keys: Sequence[str]) -> List[str]:
    """Copies back ONLY the explicitly named files/directories (paths
    relative to state_dir) from the shadow copy to the live state_dir.
    Never a blanket overwrite -- any key not present in the shadow copy is
    silently skipped rather than deleting anything live. Returns the keys
    actually promoted."""
    promoted: List[str] = []
    for key in keys:
        shadow_path = handle.shadow_state_dir / key
        if not shadow_path.exists():
            continue
        live_path = handle.live_state_dir / key
        live_path.parent.mkdir(parents=True, exist_ok=True)
        if shadow_path.is_dir():
            if live_path.exists():
                shutil.rmtree(str(live_path))
            shutil.copytree(str(shadow_path), str(live_path))
        else:
            shutil.copy2(str(shadow_path), str(live_path))
        promoted.append(key)
    return promoted
