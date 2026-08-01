#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
RW5 -- Boot-spine parity tracking (closes F9, wiring audit 2026-07-20).

The audit found two independent boot paths -- the live daemon's
`aurora.py:boot_aurora` and `aurora_runtime.py:boot_stack` (used only
by `AuroraRuntime`, the offline/batch CLI runner behind
`mode_test`/`mode_burn`/`mode_watch`/`mode_speedrun`/`mode_corpus`) --
with silently divergent mounted-organ sets. Confirmed case: `Primitive
Extractor` mounted only in `boot_stack`, so the live device path never
had a primitive-extraction genealogy lens. This module gives that
finding a permanent, checkable form instead of a one-time diff, so a
future organ added to one spine and silently missing from the other
("I wired this already") gets caught by `tests/test_rw5_boot_
parity.py` rather than rediscovered by a future audit.

This is a *tracking* deliverable, not a mandate to mirror every organ
in both spines. `boot_aurora` is the live production spine; `boot_
stack` is a smaller, purpose-built batch/dev stack that was never
meant to carry the full live organ set. Reconciliation only makes
sense per-organ, and only `PrimitiveExtractor` has been byte-verified
by the audit as a case where both spines genuinely need the same
organ (RW5, done -- see `boot_aurora`'s primitive_extractor mount).
Every other stack-only organ is recorded below as a known, reviewed
divergence pending its own architecture call -- not silently ignored,
not blindly force-mounted.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Set

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Organs that exist in both spines under different key names (naming
# convention drift between the two mount sites, not a real divergence).
# Maps boot_stack's attribute name -> boot_aurora's dict key.
NAME_ALIASES: Dict[str, str] = {
    "attention_engine": "_attention_engine",
    "braided_substrate": "_braided_substrate",
    "strand_builder": "_strand_builder",
}

# boot_stack-only organs the audit has not individually byte-verified
# for a live-spine mount decision (unlike PrimitiveExtractor, RW5's one
# confirmed case). Left stack-only deliberately pending Sunni/Cael's
# own architecture call, per the audit's "architecture calls are yours"
# framing -- recorded here so the gap stays visible instead of silent.
KNOWN_BOOT_STACK_ONLY: Set[str] = {
    "_boot_metrics",       # boot bookkeeping (restore counters), not a subsystem organ
    "emergence_monitor",   # promoted-link capability surface, batch-stack only
    "entropy_detector",    # batch-stack only
    "language_orchestra",  # ExpressionEvolutionOrchestra, batch-stack only
    "printer",             # ChainSummaryPrinter, CLI console output helper
}

# Organs RW5 has reconciled -- mounted in both spines as of this pass.
RECONCILED: Set[str] = {
    "primitive_extractor",
}


def _extract_assigned_names(body: str, pattern: str) -> Set[str]:
    return set(re.findall(pattern, body))


def _function_body(source: str, def_line: str) -> str:
    start = source.index(def_line)
    end = source.index("\ndef ", start + len(def_line))
    return source[start:end]


def extract_boot_aurora_organs() -> Set[str]:
    """Static scan of boot_aurora's systems[...] = assignments (same
    AST/call-site-census method the wiring audit used)."""
    path = os.path.join(_REPO_ROOT, "aurora.py")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    body = _function_body(source, "\ndef boot_aurora(")
    return _extract_assigned_names(body, r"systems\[['\"]([a-zA-Z_][a-zA-Z_0-9]*)['\"]\]\s*=")


def extract_boot_stack_organs() -> Set[str]:
    """Static scan of boot_stack's systems.<attr> = assignments."""
    path = os.path.join(_REPO_ROOT, "aurora_runtime.py")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    body = _function_body(source, "\ndef boot_stack(")
    return _extract_assigned_names(body, r"systems\.([a-zA-Z_][a-zA-Z_0-9]*)\s*=")


def boot_parity_report() -> Dict[str, Any]:
    """The BOOT_PARITY table: current mounted-organ sets for both
    spines, aliased for naming drift, and the resulting divergences."""
    aurora_organs = extract_boot_aurora_organs()
    stack_organs = extract_boot_stack_organs()
    aliased_stack = {NAME_ALIASES.get(name, name) for name in stack_organs}

    stack_only = aliased_stack - aurora_organs
    aurora_only = aurora_organs - aliased_stack
    unexpected_stack_only = stack_only - KNOWN_BOOT_STACK_ONLY

    return {
        "aurora_organs": sorted(aurora_organs),
        "stack_organs": sorted(stack_organs),
        "stack_only": sorted(stack_only),
        "aurora_only": sorted(aurora_only),
        "unexpected_stack_only": sorted(unexpected_stack_only),
        "reconciled_present_in_both": sorted(
            RECONCILED & aurora_organs & aliased_stack
        ),
    }
