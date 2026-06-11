#!/usr/bin/env python3
"""Canonical lineage mapping shared across Aurora modules.

This module stabilizes operation-to-constraint ancestry so existing
operational abilities are not reclassified differently by module.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import json
import os

AXIS_ORDER: Tuple[str, ...] = ("X", "T", "N", "B", "A")
LABEL_ORDER: Tuple[str, ...] = ("existence", "temporal", "energy", "boundary", "agency")

AXIS_TO_LABEL = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}

LABEL_TO_AXIS = {
    "existence": "X",
    "x": "X",
    "temporal": "T",
    "time": "T",
    "t": "T",
    "energy": "N",
    "cost": "N",
    "n": "N",
    "boundary": "B",
    "b": "B",
    "agency": "A",
    "a": "A",
}

CANONICAL_OPERATION_CONSTRAINTS = {
    # Runtime steerer surface
    "tick": ("temporal", "energy"),
    "inject": ("agency", "temporal", "boundary"),
    "inject_custom": ("agency", "temporal", "boundary"),
    "chain_burst": ("temporal", "energy", "boundary", "agency"),
    "sim_episode": ("existence", "temporal", "agency"),
    "sim_epoch": ("existence", "temporal", "energy", "agency"),
    "pressure_report": ("temporal", "energy"),
    "status": ("existence", "temporal", "energy", "boundary", "agency"),
    "links": ("boundary", "agency", "temporal"),
    "what_learned": ("existence", "temporal", "agency"),
    "available_actions": ("existence", "temporal"),
    "register_action": ("agency", "existence", "temporal"),
    "review_before_save": ("existence", "temporal", "boundary"),
    "save": ("existence", "boundary", "energy"),
    "shutdown": ("temporal", "boundary", "agency"),
    # Bridge/runtime ops
    "bridge.inject_promoted_links": ("boundary", "agency", "temporal", "energy"),
    "bridge.feedback_episode_fitness": ("agency", "existence", "temporal", "energy"),
    "runtime.boot": ("existence", "temporal", "boundary"),
    "runtime.restore_operator_gradients": ("existence", "temporal", "energy"),
    "runtime.restore_genealogy_state": ("existence", "temporal", "boundary"),
    "runtime.restore_checkpoint": ("existence", "temporal", "boundary"),
    "runtime.persist_operator_gradients": ("energy", "temporal", "boundary"),
    # Pipeline signal / modulation ops (wired in aurora.py)
    "extract_pipeline_signals": ("energy", "temporal", "agency", "boundary"),
    "apply_pipeline_modulation": ("boundary", "existence", "temporal", "energy", "agency"),
    # Layer-3 semantic operations (aurora_dimensional_systems.py)
    "extract": ("existence", "temporal", "energy", "boundary", "agency"),
    "process_concepts": ("boundary", "existence", "temporal", "energy", "agency"),
    "store_semantic": ("existence", "boundary", "temporal", "energy", "agency"),
    "get_recall_context": ("temporal", "boundary", "energy", "agency", "existence"),
    # Sensory crystal operations (aurora_sensory_crystal.py)
    "sensory.intake":           ("energy", "temporal", "existence"),
    "sensory.cluster":          ("boundary", "energy", "existence"),
    "sensory.promote":          ("agency", "boundary", "energy"),
    "sensory.cross_modal_link": ("energy", "agency", "boundary", "existence"),
    "sensory.distill":          ("temporal", "energy", "existence"),
    "sensory.crystal_boot":     ("existence", "temporal"),
    "sensory.end_session":      ("temporal", "boundary", "agency"),
    "sensory.observe_audio":    ("energy", "temporal", "existence"),
    "sensory.observe_visual":   ("energy", "existence", "boundary"),
    "sensory.observe_frame":    ("energy", "temporal", "boundary", "agency"),
}

KEYWORD_TO_LABELS = {
    "tick": ("temporal",),
    "epoch": ("temporal",),
    "phase": ("temporal",),
    "time": ("temporal",),
    "watch": ("temporal",),
    "chain": ("temporal", "energy"),
    "burst": ("temporal", "energy"),
    "cost": ("energy",),
    "budget": ("energy",),
    "energy": ("energy",),
    "pressure": ("energy", "temporal"),
    "diff": ("energy", "temporal"),
    "amplifier": ("energy",),
    "relief": ("energy",),
    "bridge": ("boundary", "agency"),
    "link": ("boundary", "agency"),
    "inject": ("boundary", "agency"),
    "promote": ("boundary", "agency"),
    "constraint": ("boundary",),
    "partition": ("boundary",),
    "interface": ("boundary",),
    "coupling": ("boundary", "agency"),
    "sim": ("agency", "temporal"),
    "episode": ("agency", "temporal"),
    "behavior": ("agency",),
    "align": ("agency",),
    "mutation": ("agency", "boundary"),
    "feedback": ("agency", "temporal"),
    "learn": ("agency", "existence"),
    "boot": ("existence", "temporal"),
    "restore": ("existence", "temporal"),
    "save": ("existence", "boundary"),
    "load": ("existence",),
    "checkpoint": ("existence", "boundary"),
    "state": ("existence",),
    "identity": ("existence", "agency"),
    "status": ("existence",),
    "report": ("existence", "temporal"),
    "lineage": ("existence", "boundary"),
    "ancestry": ("existence", "boundary"),
    "root": ("existence",),
}




def _load_generated_constraints() -> Dict[str, Tuple[str, ...]]:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "lineage_canonical_generated.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh) or {}
        ops = raw.get("operation_constraints", {}) if isinstance(raw, dict) else {}
        out: Dict[str, Tuple[str, ...]] = {}
        if isinstance(ops, dict):
            for k, v in ops.items():
                if not isinstance(k, str):
                    continue
                vals = v if isinstance(v, (list, tuple)) else []
                labels = []
                for x in vals:
                    sx = str(x or "").strip().lower()
                    if sx in AXIS_TO_LABEL.values() and sx not in labels:
                        labels.append(sx)
                out[k] = tuple(labels)
        return out
    except Exception:
        return {}


GENERATED_OPERATION_CONSTRAINTS: Dict[str, Tuple[str, ...]] = _load_generated_constraints()
# Pre-computed lowercase index — avoids O(n) linear scan in _generated_lookup.
_GENERATED_LOWER: Dict[str, Tuple[str, ...]] = {
    k.lower(): v for k, v in GENERATED_OPERATION_CONSTRAINTS.items()
}


def _generated_lookup(op_name: str) -> Tuple[str, ...]:
    name = str(op_name or "").strip()
    if not name:
        return tuple()

    exact = GENERATED_OPERATION_CONSTRAINTS.get(name)
    if exact:
        return exact

    # Lowercase exact fallback — O(1) via pre-computed index
    low = name.lower()
    result = _GENERATED_LOWER.get(low)
    if result:
        return result

    # Suffix fallback: fn, cls.fn, mod.cls.fn
    toks = [t for t in name.split(".") if t]
    for n in (3, 2, 1):
        if len(toks) >= n:
            suf = ".".join(toks[-n:])
            exact_suf = GENERATED_OPERATION_CONSTRAINTS.get(suf)
            if exact_suf:
                return exact_suf
            result = _GENERATED_LOWER.get(suf.lower())
            if result:
                return result

    return tuple()

def axis_token(raw: str) -> Optional[str]:
    tok = str(raw or "").strip().lower()
    ax = LABEL_TO_AXIS.get(tok)
    return ax if ax in AXIS_ORDER else None


def label_for_axis(axis: str) -> Optional[str]:
    ax = str(axis or "").strip().upper()
    return AXIS_TO_LABEL.get(ax)


def _ordered_unique(labels: Iterable[str]) -> Tuple[str, ...]:
    seen = set()
    out: List[str] = []
    for lbl in labels:
        s = str(lbl or "").strip().lower()
        if s in AXIS_TO_LABEL.values() and s not in seen:
            seen.add(s)
            out.append(s)
    # keep canonical ordering for stability
    return tuple([l for l in LABEL_ORDER if l in seen and l in out] + [l for l in out if l not in LABEL_ORDER])


def constraints_for_operation(
    op_name: str,
    axis: Optional[str] = None,
    requires: Optional[Sequence[str]] = None,
    effect_tags: Optional[Sequence[str]] = None,
) -> Tuple[str, ...]:
    name = str(op_name or "").strip()

    exact = CANONICAL_OPERATION_CONSTRAINTS.get(name)
    if exact:
        return _ordered_unique(exact)

    generated = _generated_lookup(name)
    if generated:
        return _ordered_unique(generated)

    labels: List[str] = []

    def add_axis_like(raw: Optional[str]) -> None:
        ax = axis_token(str(raw or ""))
        if ax:
            lbl = label_for_axis(ax)
            if lbl:
                labels.append(lbl)

    # Operation id prefix, e.g. X:ADMIT / N:REDISTRIBUTE / A:ALIGNMENT_PUSH
    if ":" in name:
        pref = name.split(":", 1)[0]
        add_axis_like(pref)

    add_axis_like(axis)

    for r in (requires or ()):
        add_axis_like(r)

    for tag in (effect_tags or ()):
        text = str(tag or "").replace(":", " ").replace(">", " ").replace("_", " ")
        for tok in text.split():
            add_axis_like(tok)

    low_name = name.lower()
    for key, adds in KEYWORD_TO_LABELS.items():
        if key in low_name:
            labels.extend(adds)

    if not labels:
        labels = ["existence", "temporal"]

    return _ordered_unique(labels)


def operator_action_for_axis(axis: str) -> str:
    ax = str(axis or "X").strip().upper()
    mapping = {
        "X": "admissibility_gating",
        "T": "temporal_orchestration",
        "N": "energy_economics",
        "B": "boundary_shaping",
        "A": "agency_direction",
    }
    return str(mapping.get(ax, "cross_constraint_operation"))
