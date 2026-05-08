"""
aurora_surface_doc.py
─────────────────────────────────────────────────────────────────────────────
Explains what evolved surfaces do — both in plain English and in terms of
applied axis pressure.

Two data sources:
  1. _SURFACE_REGISTRY in aurora_evolved_surfaces.py
     — what each surface IS (signature, constraints, effect_modes, genealogy)
  2. aurora_state/surface_pressure_log.jsonl
     — what each surface DID at runtime (axis_pressure snapshot + effect)

Public API
----------
  explain(name)          → dict card for one surface
  full_report()          → list of cards for all surfaces, sorted by score
  pressure_history(name) → recent pressure log entries for one surface
  print_report()         → human-readable console output
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


# ── axis metadata ──────────────────────────────────────────────────────────────

_AXIS_NAMES = {
    "X": "Existence",
    "T": "Temporal",
    "N": "Energy",
    "B": "Boundary",
    "A": "Agency",
}

_EFFECT_MODE_DESC = {
    "state_schema_change":          "alters existence/state schema (X)",
    "temporal_orchestration_change":"reshapes temporal sequencing (T)",
    "cost_pressure_change":         "adjusts energy cost pressure (N)",
    "interface_boundary_change":    "modifies interface boundaries (B)",
    "adaptive_steering_change":     "influences agency/steering (A)",
    "gateway_surface":              "acts as a routing gateway (B)",
    "lineage_surface":              "extends evolutionary lineage (B)",
    "latent_route_surface":         "opens a latent routing path (A)",
    "class_lineage_surface":        "hooks into a class's lineage (B)",
}

_CONSTRAINT_TO_AXIS = {
    "existence": "X",
    "temporal":  "T",
    "energy":    "N",
    "boundary":  "B",
    "agency":    "A",
}


# ── path helpers ───────────────────────────────────────────────────────────────

def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _pressure_log_path() -> str:
    return os.path.join(_repo_root(), "aurora_state", "surface_pressure_log.jsonl")


# ── registry loader ────────────────────────────────────────────────────────────

def _load_registry() -> Dict[str, Dict[str, Any]]:
    try:
        from aurora_internal.aurora_evolved_surfaces import _SURFACE_REGISTRY  # type: ignore
        return dict(_SURFACE_REGISTRY)
    except Exception:
        return {}


# ── pressure log ───────────────────────────────────────────────────────────────

def _load_pressure_log(max_entries: int = 2000) -> List[Dict[str, Any]]:
    path = _pressure_log_path()
    if not os.path.exists(path):
        return []
    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return entries[-max_entries:]


# ── signature → plain English ──────────────────────────────────────────────────

def _parse_signature(sig: str) -> Dict[str, int]:
    """Parse 'N^2*B^1' → {'N': 2, 'B': 1}"""
    counts: Dict[str, int] = {}
    for part in str(sig or "").split("*"):
        part = part.strip()
        if "^" in part:
            ax, n = part.split("^", 1)
            try:
                counts[ax.strip()] = int(float(n.strip()))
            except ValueError:
                pass
        elif part and part in _AXIS_NAMES:
            counts[part] = 1
    return counts


def _signature_sentence(sig: str) -> str:
    counts = _parse_signature(sig)
    if not counts:
        return "no axis signature recorded"
    parts = []
    for ax in ("X", "T", "N", "B", "A"):
        n = counts.get(ax, 0)
        if n > 0:
            label = _AXIS_NAMES[ax]
            parts.append(f"{label}×{n}" if n > 1 else label)
    return "touches " + ", ".join(parts)


def _effect_sentence(effect_modes: List[str], effect_phrases: List[str]) -> str:
    descs = [_EFFECT_MODE_DESC.get(m, m) for m in (effect_modes or [])]
    phrases = [p for p in (effect_phrases or []) if p]
    combined = descs + phrases
    if not combined:
        return "no documented effects"
    return "; ".join(combined[:4])


def _pressure_level(score: float) -> str:
    if score >= 0.80:   return "high"
    if score >= 0.50:   return "moderate"
    if score >= 0.25:   return "low"
    return "minimal"


def _axis_composition(sig: str) -> Dict[str, float]:
    """
    Normalize signature counts into percentage contributions per axis.

    E.g. 'N^2*B^2' → {'X': 0.0, 'T': 0.0, 'N': 0.50, 'B': 0.50, 'A': 0.0}
    Each value is 0.0–1.0, all values sum to 1.0 (or all 0.0 if no signature).
    """
    counts = _parse_signature(sig)
    total = sum(counts.values())
    if total == 0:
        return {ax: 0.0 for ax in ("X", "T", "N", "B", "A")}
    return {ax: round(counts.get(ax, 0) / total, 4) for ax in ("X", "T", "N", "B", "A")}


def _effect_composition(effect_modes: List[str]) -> Dict[str, float]:
    """
    Uniform fractional weight per effect mode.

    E.g. ['cost_pressure_change', 'adaptive_steering_change']
    → {'cost_pressure_change': 0.50, 'adaptive_steering_change': 0.50}
    """
    modes = [m for m in (effect_modes or []) if m]
    if not modes:
        return {}
    weight = round(1.0 / len(modes), 4)
    return {m: weight for m in modes}


def _semantic_label(
    axis_comp: Dict[str, float],
    effect_comp: Dict[str, float],
    kind: str,
    gpressure: float,
) -> str:
    """
    Generate a compact human-readable label from composition data.

    Format: "<dominant-axis>-driven <kind> [+ <secondary>] — <top-effect>"
    E.g.:   "Energy-driven reflection + Boundary — cost adjustment"
    """
    axis_names = {"X": "Existence", "T": "Temporal", "N": "Energy", "B": "Boundary", "A": "Agency"}
    effect_short = {
        "state_schema_change":           "state reshape",
        "temporal_orchestration_change": "timing shift",
        "cost_pressure_change":          "cost adjustment",
        "interface_boundary_change":     "boundary edit",
        "adaptive_steering_change":      "steering bias",
        "gateway_surface":               "routing gate",
        "lineage_surface":               "lineage hook",
        "latent_route_surface":          "latent path",
        "class_lineage_surface":         "class hook",
    }

    # top two axes by weight
    ranked_axes = sorted(
        [(v, ax) for ax, v in axis_comp.items() if v > 0.0],
        reverse=True,
    )
    if not ranked_axes:
        dominant = "Unknown"
        secondary = ""
    elif len(ranked_axes) == 1:
        dominant = axis_names[ranked_axes[0][1]]
        secondary = ""
    else:
        dominant  = axis_names[ranked_axes[0][1]]
        secondary = axis_names[ranked_axes[1][1]]

    # top effect
    if effect_comp:
        top_effect_key = max(effect_comp, key=lambda k: effect_comp[k])
        top_effect = effect_short.get(top_effect_key, top_effect_key.replace("_", " "))
    else:
        top_effect = "unknown effect"

    gen_tag = f"  gen≈{gpressure:.2f}" if gpressure > 0.05 else ""
    label = f"{dominant}-driven {kind}"
    if secondary and secondary != dominant:
        label += f" + {secondary}"
    label += f" — {top_effect}{gen_tag}"
    return label


# ── core explain ───────────────────────────────────────────────────────────────

def explain(name: str, registry: Optional[Dict[str, Any]] = None, _cached_log: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Return a documentation card for one evolved surface.

    Keys:
      name                  surface method name
      op_id                 originating operation id
      kind                  latent | reflection
      what_it_does          plain-English summary sentence
      axis_signature        e.g. "N^2*B^2"
      axes_involved         human labels for each active axis
      pressure_level        high / moderate / low / minimal
      effect_modes          list of effect mode strings
      effect_descriptions   plain-English per effect_mode
      effect_phrases        evolution-generated description phrases
      expected_axes         axis letters this op targets
      surface_score         float 0–1
      genealogy_pressure    float 0–1
      alignment_gap         float — how far from alignment
      coupling_signature    best coupling match
      ability_hits          how many existing abilities share signature
      link_hits             how many DAG links share signature
      constraints           raw constraint list
      runtime_pressure_avg  avg axis_pressure snapshot across recent calls (or {})
      call_count            how many times seen in pressure log
    """
    if registry is None:
        registry = _load_registry()

    meta = dict(registry.get(str(name), {}) or {})

    # registry uses genealogy_signature; fall back to signature for compat
    sig              = str(meta.get("genealogy_signature", "") or meta.get("signature", "") or "")
    kind             = str(meta.get("kind", "") or "unknown")
    op_id            = str(meta.get("op_id", "") or "")
    constraints      = list(meta.get("constraints", []) or [])
    effect_modes     = list(meta.get("effect_modes", []) or [])
    effect_phrases   = list(meta.get("effect_phrases", []) or [])
    surface_score    = float(meta.get("surface_score", 0.0) or 0.0)
    gpressure        = float(meta.get("genealogy_pressure", 0.0) or 0.0)
    alignment_gap    = float(meta.get("alignment_gap", 0.0) or 0.0)
    coupling_sig     = str(meta.get("best_coupling_signature", "") or "")
    ability_hits     = int(meta.get("ability_hits", 0) or 0)
    link_hits        = int(meta.get("link_hits", 0) or 0)
    contract         = dict(meta.get("contract_profile", {}) or {})

    counts = _parse_signature(sig)
    axes_involved = {ax: _AXIS_NAMES[ax] for ax in counts if ax in _AXIS_NAMES}
    expected_axes = list(dict.fromkeys(
        _CONSTRAINT_TO_AXIS.get(c.strip().lower(), "")
        for c in constraints
        if _CONSTRAINT_TO_AXIS.get(c.strip().lower())
    ))

    # plain-English summary
    sig_phrase    = _signature_sentence(sig)
    effect_phrase = _effect_sentence(effect_modes, effect_phrases)
    doc_hint      = str(contract.get("doc_hint", "") or "")
    if doc_hint:
        what_it_does = f"{doc_hint} — {sig_phrase}; {effect_phrase}"
    else:
        verb = "Reflects" if kind == "reflection" else "Activates"
        what_it_does = f"{verb} '{op_id}' — {sig_phrase}; {effect_phrase}"

    # composition
    axis_comp   = _axis_composition(sig)
    effect_comp = _effect_composition(effect_modes)
    label       = _semantic_label(axis_comp, effect_comp, kind, gpressure)

    # runtime data from pressure log
    log = _cached_log if _cached_log is not None else _load_pressure_log()
    surface_entries = [e for e in log if e.get("surface") == name or e.get("op_id") == op_id]
    call_count = len(surface_entries)
    runtime_pressure_avg: Dict[str, float] = {}
    runtime_axis_composition: Dict[str, float] = {}
    if surface_entries:
        axes = ("X", "T", "N", "B", "A")
        totals = {ax: 0.0 for ax in axes}
        for entry in surface_entries:
            snap = dict(entry.get("axis_pressure", {}) or {})
            for ax in axes:
                totals[ax] += float(snap.get(ax, 0.0) or 0.0)
        n = len(surface_entries)
        runtime_pressure_avg = {ax: round(totals[ax] / n, 6) for ax in axes}
        # normalize observed runtime pressures into a composition percentage
        total_runtime = sum(runtime_pressure_avg.values())
        if total_runtime > 0:
            runtime_axis_composition = {
                ax: round(runtime_pressure_avg[ax] / total_runtime, 4) for ax in axes
            }

    return {
        "name":                     name,
        "op_id":                    op_id,
        "kind":                     kind,
        "label":                    label,
        "what_it_does":             what_it_does,
        "axis_signature":           sig,
        "axes_involved":            axes_involved,
        "axis_composition":         axis_comp,         # {X/T/N/B/A: 0.0–1.0} from signature
        "effect_composition":       effect_comp,       # {effect_mode: weight} uniform split
        "pressure_level":           _pressure_level(surface_score),
        "effect_modes":             effect_modes,
        "effect_descriptions":      [_EFFECT_MODE_DESC.get(m, m) for m in effect_modes],
        "effect_phrases":           effect_phrases,
        "expected_axes":            expected_axes,
        "surface_score":            surface_score,
        "genealogy_pressure":       gpressure,
        "alignment_gap":            alignment_gap,
        "coupling_signature":       coupling_sig,
        "ability_hits":             ability_hits,
        "link_hits":                link_hits,
        "constraints":              constraints,
        "runtime_pressure_avg":     runtime_pressure_avg,
        "runtime_axis_composition": runtime_axis_composition,  # observed composition at runtime
        "call_count":               call_count,
    }


def full_report(top_n: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return doc cards for all evolved surfaces, sorted by surface_score descending.
    """
    registry = _load_registry()
    log = _load_pressure_log()   # load once, share across all explain() calls
    cards = [explain(name, registry, _cached_log=log) for name in registry]
    cards.sort(key=lambda c: -c["surface_score"])
    if top_n is not None:
        cards = cards[:top_n]
    return cards


def pressure_history(name: str, last_n: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent pressure log entries for one surface."""
    log = _load_pressure_log()
    entries = [e for e in log if e.get("surface") == name]
    return entries[-last_n:]


# ── console output ─────────────────────────────────────────────────────────────

def print_report(top_n: int = 20, min_score: float = 0.0) -> None:
    cards = full_report()
    cards = [c for c in cards if c["surface_score"] >= min_score]
    if not cards:
        print("No evolved surfaces found.")
        return

    print(f"{'═'*78}")
    print(f"  AURORA EVOLVED SURFACES  ({len(cards)} surfaces)")
    print(f"{'═'*78}")

    for card in cards[:top_n]:
        axes_str = "+".join(sorted(card["axes_involved"].keys())) or "—"
        print(f"\n  {card['name'][:60]}")
        print(f"  {'─'*60}")
        print(f"  label : {card['label']}")
        print(f"  what  : {card['what_it_does'][:100]}")

        # axis composition bar
        acomp = card["axis_composition"]
        abar = "  ".join(
            f"{ax}:{int(round(v * 100)):3d}%"
            for ax, v in acomp.items()
            if v > 0.0
        ) or "—"
        print(f"  makeup: {abar}   (sig={card['axis_signature']})")

        # effect composition
        ecomp = card["effect_composition"]
        if ecomp:
            ebar = "  ".join(
                f"{k.replace('_change','').replace('_surface','')}: {int(round(v*100))}%"
                for k, v in sorted(ecomp.items(), key=lambda x: -x[1])
            )
            print(f"  effect: {ebar[:100]}")

        print(f"  score : {card['surface_score']:.3f}   "
              f"gen={card['genealogy_pressure']:.3f}   "
              f"gap={card['alignment_gap']:.3f}   "
              f"pressure={card['pressure_level']}")

        # runtime composition if available, otherwise lineage
        if card["call_count"]:
            rcomp = card["runtime_axis_composition"]
            if rcomp:
                rbar = "  ".join(
                    f"{ax}:{int(round(v * 100)):3d}%"
                    for ax, v in rcomp.items()
                    if v > 0.0
                )
                print(f"  runtime ({card['call_count']} calls): observed={rbar}")
            else:
                avg = card["runtime_pressure_avg"]
                active = {ax: f"{v:.4f}" for ax, v in avg.items() if v != 0.0}
                print(f"  runtime: {card['call_count']} call(s) — "
                      f"avg pressure {active or 'not yet captured'}")
        elif card["ability_hits"] or card["link_hits"]:
            print(f"  lineage: {card['ability_hits']} ability hit(s)  "
                  f"{card['link_hits']} link hit(s)  (not yet called at runtime)")

    if len(cards) > top_n:
        print(f"\n  ... and {len(cards) - top_n} more (use top_n= to see them)")
    print(f"\n{'═'*78}")


if __name__ == "__main__":
    import sys
    top = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print_report(top_n=top)
