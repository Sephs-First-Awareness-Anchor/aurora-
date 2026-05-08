"""
aurora_pressure_router.py
─────────────────────────────────────────────────────────────────────────────
Unified motivational substrate router.

Takes a TypedPressureSignal and simultaneously feeds three growth systems:

  LAYER 1 — EVOLUTION
    Writes bias hints for CodeAutoEvolver and SurfaceDispatcher threshold
    so evolution budget concentrates on the pressured axes.
    (Mostly already done via PressureParameterAdapter.  This layer reads
    the classified type and amplifies the budget allocation for the
    dominant pressure type.)

  LAYER 2 — TRAINING CURRICULUM
    Calls FailPointLedger.record_fail() on the dimensions that map to the
    dominant pressure types, with severity proportional to pressure score.
    This steers dream curriculum episodes toward the fault lines.

  LAYER 3 — GPT / RETRIEVAL QUERY BIAS
    Writes aurora_state/query_bias.json.
    Aurora's GPT-mediated processes (reflection, retrieval, hypothesis
    generation) read this file to know what to study next and how to
    frame queries.  Each pressure type generates:
      - query_templates   concrete search/reflection questions
      - retrieval_domains knowledge domains to pull from
      - reflection_directive  one-line instruction for the next self-review
      - hypothesis_seed   what hypothesis to test in next episode

The three-layer dispatch happens atomically in route().  Call it after
every PressureParameterAdapter.adapt() cycle (every 50 ticks), or any
time you want the system to reconsider its growth priorities.

Output file: aurora_state/query_bias.json
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from aurora_internal.aurora_pressure_classifier import (  # type: ignore
    PressureClassifier,
    TypedPressureSignal,
    PRESSURE_TYPES,
)

_QUERY_BIAS_REL  = "aurora_state/query_bias.json"
_EVOLVER_BIAS_REL = "aurora_state/adapter_hints.json"

# ── Per-type knowledge descriptors ────────────────────────────────────────────
# Used to generate contextually relevant query templates and reflection
# directives when a given type is the dominant pressure signal.

_TYPE_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "knowledge_gap": {
        "label":      "Missing conceptual content",
        "axis":       "X (Existence)",
        "dimensions": ["uncertainty_signaling", "contradiction_handling", "perspective_integration"],
        "retrieval_domains": [
            "epistemology", "self-modeling", "constraint satisfaction",
            "epistemic limits", "grounding mechanisms",
        ],
        "query_templates": [
            "What conceptual framework best handles {axis_context}? "
            "What am I missing about its structure?",
            "What is unknown or unresolved in my understanding of {dim_context}?",
            "What knowledge would resolve the tension between acknowledging "
            "limits and maintaining coherence in {axis_context}?",
            "What examples of {dim_context} failure reveal the missing structure?",
        ],
        "reflection_directive": (
            "Identify one concept in {dim_context} that you currently "
            "cannot fully ground.  Describe what you do and do not know about it."
        ),
        "hypothesis_seed": (
            "If I had clearer grounding in {axis_context}, "
            "what specific failure mode would it prevent?"
        ),
        "training_severity_boost": 0.10,  # added to base severity
    },
    "reasoning_gap": {
        "label":      "Weak causal / temporal linkage",
        "axis":       "T (Temporal)",
        "dimensions": ["coherence_maintenance", "context_carryover", "misunderstanding_repair"],
        "retrieval_domains": [
            "causal reasoning", "sequential inference", "narrative coherence",
            "temporal logic", "multi-step argument structure",
        ],
        "query_templates": [
            "How does {axis_context} connect across multiple reasoning steps? "
            "Where does the chain typically break?",
            "What logical bridges are missing between {dim_context} and its resolution?",
            "What multi-step reasoning pattern would resolve {dim_context} failures?",
            "When {axis_context} pressure is high, what is the most common "
            "inference failure — gap, reversal, or false assumption?",
        ],
        "reflection_directive": (
            "Trace a recent failure in {dim_context} step by step. "
            "Identify the exact point where the reasoning chain broke."
        ),
        "hypothesis_seed": (
            "What intermediate reasoning step, if added explicitly, "
            "would close the {axis_context} gap in {dim_context}?"
        ),
        "training_severity_boost": 0.12,
    },
    "articulation_gap": {
        "label":      "Expression precision failure",
        "axis":       "N (Energy / Resource)",
        "dimensions": ["semantic_precision", "compression_elaboration_fit", "implied_intent_inference"],
        "retrieval_domains": [
            "lexical precision", "vocabulary anchoring", "semantic consistency",
            "concision techniques", "implied meaning extraction",
        ],
        "query_templates": [
            "What vocabulary best captures the distinction required in {dim_context}?",
            "How can the idea behind {axis_context} be expressed "
            "more precisely without losing meaning?",
            "What is the minimum words needed to convey {dim_context} unambiguously?",
            "What paraphrase drift patterns cause {dim_context} failures?",
        ],
        "reflection_directive": (
            "Find one recent response where {dim_context} was imprecise. "
            "Rewrite the critical sentence using anchored vocabulary."
        ),
        "hypothesis_seed": (
            "If {dim_context} were expressed with a fixed canonical vocabulary, "
            "how much of the current {axis_context} pressure would dissolve?"
        ),
        "training_severity_boost": 0.08,
    },
    "stability_gap": {
        "label":      "Inconsistent behavioral output",
        "axis":       "A (Agency)",
        "dimensions": ["adaptive_strategy_selection", "framing_selection"],
        "retrieval_domains": [
            "decision theory", "strategy consolidation", "behavioral consistency",
            "identity stability", "meta-cognition",
        ],
        "query_templates": [
            "What conditions trigger a strategy switch in {axis_context}? "
            "Are those switches principled or reactive?",
            "What framing pattern would produce consistent output in {dim_context}?",
            "What internal signal should Aurora use to decide when to shift "
            "strategy in {axis_context}?",
            "What is the difference between adaptive flexibility and instability "
            "in {dim_context}?",
        ],
        "reflection_directive": (
            "Identify a recent turn where {dim_context} produced inconsistent output. "
            "What decision criterion, if applied, would have resolved it?"
        ),
        "hypothesis_seed": (
            "Is the current {axis_context} pressure caused by too few strategies, "
            "or by failure to choose between existing ones at the right moment?"
        ),
        "training_severity_boost": 0.10,
    },
    "tool_gap": {
        "label":      "Resource / boundary leverage failure",
        "axis":       "B (Boundary)",
        "dimensions": ["boundary_calibration", "ambiguity_handling", "emotional_calibration"],
        "retrieval_domains": [
            "tool-use patterns", "interface calibration", "clarification strategies",
            "boundary negotiation", "emotional register management",
        ],
        "query_templates": [
            "What tool or capability, if present, would relieve {axis_context} pressure?",
            "How should the boundary between Aurora's domain and the user's "
            "domain be calibrated in {dim_context}?",
            "What clarification strategy works best when {dim_context} is failing?",
            "How does emotional register affect {axis_context} success or failure?",
        ],
        "reflection_directive": (
            "Identify the last time {dim_context} failed due to boundary overreach "
            "or under-reach.  What calibration signal was missing?"
        ),
        "hypothesis_seed": (
            "Would explicit clarification at the {axis_context} interface "
            "reduce the current fail rate in {dim_context}?"
        ),
        "training_severity_boost": 0.09,
    },
    "code_gap": {
        "label":      "Code structure bottleneck",
        "axis":       "multi-axis (evolutionary budget)",
        "dimensions": [],
        "retrieval_domains": [
            "architectural patterns", "code refactoring", "module boundary design",
            "evolutionary operator theory", "pressure-relief code structures",
        ],
        "query_templates": [
            "What code structure would best implement the missing capability "
            "in the high-pressure axis cluster?",
            "How should the evolutionary operator be modified to generate "
            "ops that relieve the current axis imbalance?",
            "What architectural boundary change would reduce code-level pressure?",
            "Which module is the structural bottleneck for the current "
            "evolutionary budget allocation?",
        ],
        "reflection_directive": (
            "Identify the code module whose structure is most limiting Aurora's "
            "ability to express the currently pressured capability. "
            "What change would create the most relief?"
        ),
        "hypothesis_seed": (
            "If the evolutionary operator budget were reallocated toward "
            "the highest-bias axis, which surface would be produced next "
            "and would it actually relieve pressure?"
        ),
        "training_severity_boost": 0.07,
    },
}


# Axis letter extracted from each pressure type's axis field.
# Used to compute the magnitude formula weight when routing training severity.
_TYPE_TO_AXIS: Dict[str, str] = {
    "knowledge_gap":   "X",
    "reasoning_gap":   "T",
    "articulation_gap": "N",
    "tool_gap":        "B",
    "stability_gap":   "A",
    # code_gap is multi-axis; excluded from formula (no single axis)
}


def _impact_formula_weight(axis_scores: Dict[str, float]) -> float:
    """
    Compute the canonical impact formula weight from per-axis pressure scores:

        Impact = ((B × T × X) / N) × A

    Each axis score is in [0.0, 1.0] (higher = more pressure on that axis).
    N acts as denominator: high N pressure (energy deficit) amplifies severity.
    N_denom = max(0.1, 1.0 - N_score) so that high N pressure → low N_denom → higher weight.

    Returns a multiplicative weight in [0.0, ~∞] — caller should clamp to [0.0, 1.0].
    Returns 1.0 (neutral) when axis scores are insufficient to compute.
    """
    if not axis_scores or len(axis_scores) < 3:
        return 1.0
    b = float(axis_scores.get("B", 0.0))
    t = float(axis_scores.get("T", 0.0))
    x = float(axis_scores.get("X", 0.0))
    n = float(axis_scores.get("N", 0.0))
    a = float(axis_scores.get("A", 0.0))
    n_denom = max(0.1, 1.0 - n)   # high N pressure → small denominator → amplifies
    magnitude = (b * t * x) / n_denom
    return float(magnitude * a) if a > 0.0 else float(magnitude)


def _render_template(template: str, axis_context: str, dim_context: str) -> str:
    return (
        template
        .replace("{axis_context}", axis_context)
        .replace("{dim_context}", dim_context)
    )


class PressureRouter:
    """
    Routes typed pressure signals to all three growth layers.

    Usage:
        router = PressureRouter(repo_root)
        result = router.route(fail_ledger=ledger)   # full three-layer dispatch
        # or just re-read the last written bias:
        bias = router.load_query_bias()
    """

    def __init__(self, repo_root: str):
        self.repo_root  = os.path.abspath(repo_root)
        self._classifier = PressureClassifier(repo_root)

    # ── public ────────────────────────────────────────────────────────────────

    def route(
        self,
        fail_ledger: Any = None,
        min_score: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Full three-layer dispatch.

        fail_ledger: FailPointLedger instance (Layer 2).  If None, training
                     layer is skipped.
        min_score:   pressure types below this threshold are not routed.

        Returns a summary of what was dispatched.
        """
        signal = self._classifier.classify()
        active = signal.above(min_score)
        directive_active, classification_mode, directive_floor = self._select_directive_types(
            signal,
            min_score,
        )

        r_training  = self._route_training(signal, active, fail_ledger)
        r_evolution = self._route_evolution(signal, directive_active)
        r_gpt       = self._route_gpt_bias(
            signal,
            directive_active,
            classification_mode=classification_mode,
            min_score=min_score,
            fallback_min_score=directive_floor,
        )

        return {
            "dominant_type":     signal.dominant,
            "active_types":      [(t, round(s, 4)) for t, s in active],
            "directive_types":   [(t, round(s, 4)) for t, s in directive_active],
            "classification_mode": classification_mode,
            "layer_training":    r_training,
            "layer_evolution":   r_evolution,
            "layer_gpt":         r_gpt,
            "classified_at":     round(signal.timestamp, 2),
        }

    def load_query_bias(self) -> Dict[str, Any]:
        """Read the most recent query_bias.json (safe if missing)."""
        path = os.path.join(self.repo_root, _QUERY_BIAS_REL)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def status(self) -> Dict[str, Any]:
        signal = self._classifier.classify()
        bias   = self.load_query_bias()
        return {
            "classifier":   signal.to_dict(),
            "query_bias_age": round(
                time.time() - float(bias.get("last_updated", 0.0)), 1
            ) if bias else None,
            "dominant_bias_type": bias.get("dominant_type"),
            "active_biases": len(bias.get("active_biases", [])),
        }

    def _select_directive_types(
        self,
        signal: TypedPressureSignal,
        min_score: float,
    ) -> Tuple[List[Tuple[str, float]], str, float]:
        strong = signal.above(min_score)
        if strong:
            return strong, "active", min_score

        fallback_min = max(0.08, min_score * 0.5)
        weak = [(ptype, score) for ptype, score in signal.ranked if score >= fallback_min]
        if weak:
            return weak[:3], "weak_signal", fallback_min

        if signal.ranked and float(signal.ranked[0][1]) > 0.0:
            return [signal.ranked[0]], "weak_signal", 0.0

        return [], "idle", fallback_min

    # ── Layer 1: Evolution ────────────────────────────────────────────────────

    def _route_evolution(
        self,
        signal: TypedPressureSignal,
        active: List[Tuple[str, float]],
    ) -> Dict[str, Any]:
        """
        Update adapter_hints.json with a routing_type annotation so that
        CodeAutoEvolver knows the semantic interpretation of the current
        axis imbalance and can choose operators accordingly.
        """
        if not active:
            return {"dispatched": False, "reason": "no_active_types"}

        path = os.path.join(self.repo_root, _EVOLVER_BIAS_REL)
        try:
            hints: Dict[str, Any] = {}
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    hints = json.load(fh)
            if not isinstance(hints, dict):
                hints = {}

            # Annotate the routing interpretation
            hints["routing_type"]         = signal.dominant
            hints["routing_type_scores"]  = {t: round(s, 4) for t, s in active}
            hints["routing_updated_at"]   = float(time.time())

            with open(path, "w", encoding="utf-8") as fh:
                json.dump(hints, fh, indent=2, sort_keys=True, ensure_ascii=True)

            return {
                "dispatched":   True,
                "routing_type": signal.dominant,
                "annotated_in": _EVOLVER_BIAS_REL,
            }
        except Exception as exc:
            return {"dispatched": False, "error": str(exc)}

    # ── Layer 2: Training ─────────────────────────────────────────────────────

    def _route_training(
        self,
        signal: TypedPressureSignal,
        active: List[Tuple[str, float]],
        fail_ledger: Any,
    ) -> Dict[str, Any]:
        """
        Feed FailPointLedger with pressure-weighted fail signals for the
        dimensions that correspond to active pressure types.
        Only injects into dimensions that have existing fail counts < 20
        (avoids polluting well-trained dimensions).
        """
        if fail_ledger is None:
            return {"dispatched": False, "reason": "no_fail_ledger"}
        if not hasattr(fail_ledger, "record_fail"):
            return {"dispatched": False, "reason": "ledger_missing_record_fail"}

        # Build per-axis pressure scores from active signal types for impact weighting.
        axis_scores: Dict[str, float] = {}
        for ptype, score in active:
            ax = _TYPE_TO_AXIS.get(ptype)
            if ax:
                axis_scores[ax] = max(axis_scores.get(ax, 0.0), score)
        impact_weight = _impact_formula_weight(axis_scores)
        # Clamp weight to [0.5, 2.0] so formula amplifies but never collapses severity.
        impact_weight = max(0.5, min(2.0, impact_weight)) if impact_weight != 1.0 else 1.0

        seeded = 0
        for ptype, score in active:
            meta    = _TYPE_KNOWLEDGE.get(ptype, {})
            dims    = meta.get("dimensions", [])
            boost   = float(meta.get("training_severity_boost", 0.0))
            # Apply impact formula weight: multi-axis failures compound severity
            severity = min(1.0, (score + boost) * impact_weight)

            for dim in dims:
                try:
                    rec = getattr(fail_ledger, "_records", {}).get(dim)
                    current_count = int(getattr(rec, "fail_count", 0) or 0) if rec else 0
                    if current_count >= 20:
                        continue  # dimension already well-represented
                    fail_ledger.record_fail(
                        dimension=dim,
                        severity=severity,
                        example={
                            "conversation_id": f"pressure_route_{ptype}_{dim}",
                            "user_turns": [
                                f"[PRESSURE ROUTING] {ptype} signal at {score:.2f} — "
                                f"training needed on {dim}."
                            ],
                            "aurora_turns": [f"[{ptype} deficit — structural reinforcement needed]"],
                            "scores": {dim: severity},
                            "tags": ["pressure_routed", f"type:{ptype}"],
                        },
                    )
                    seeded += 1
                except Exception:
                    pass

        if seeded > 0:
            try:
                fail_ledger.save()
            except Exception:
                pass

        return {
            "dispatched":   seeded > 0,
            "seeded":       seeded,
            "active_types": len(active),
        }

    # ── Layer 3: GPT / Retrieval Query Bias ──────────────────────────────────

    def _route_gpt_bias(
        self,
        signal: TypedPressureSignal,
        active: List[Tuple[str, float]],
        classification_mode: str = "active",
        min_score: float = 0.20,
        fallback_min_score: float = 0.10,
    ) -> Dict[str, Any]:
        """
        Write aurora_state/query_bias.json.

        Format:
        {
          "dominant_type": "reasoning_gap",
          "active_biases": [
            {
              "pressure_type":        "reasoning_gap",
              "priority":             0.72,
              "label":                "Weak causal / temporal linkage",
              "axis":                 "T (Temporal)",
              "retrieval_domains":    [...],
              "query_templates":      [...],   # rendered with axis/dim context
              "reflection_directive": "...",
              "hypothesis_seed":      "...",
              "source_dimensions":    ["coherence_maintenance", ...]
            },
            ...
          ],
          "last_updated": 1234567890.0
        }
        """
        biases: List[Dict[str, Any]] = []

        for ptype, score in active:
            meta = _TYPE_KNOWLEDGE.get(ptype, {})
            dims = meta.get("dimensions", [])

            # pick the highest-failing dimension as context anchor
            top_dim = ""
            if dims:
                top_dim = max(
                    dims,
                    key=lambda d: float(signal.dim_sources.get(d, 0.0)),
                    default=dims[0],
                )

            axis_context = meta.get("axis", ptype)
            dim_context  = top_dim or ptype

            rendered_templates = [
                _render_template(tpl, axis_context, dim_context)
                for tpl in meta.get("query_templates", [])
            ]
            reflection = _render_template(
                meta.get("reflection_directive", "Examine current {axis_context} pressure."),
                axis_context, dim_context,
            )
            hypothesis = _render_template(
                meta.get("hypothesis_seed", "What would reduce {axis_context} pressure?"),
                axis_context, dim_context,
            )

            biases.append({
                "pressure_type":        ptype,
                "priority":             round(score, 4),
                "label":                meta.get("label", ptype),
                "axis":                 axis_context,
                "signal_mode":          classification_mode,
                "retrieval_domains":    meta.get("retrieval_domains", []),
                "query_templates":      rendered_templates,
                "reflection_directive": reflection,
                "hypothesis_seed":      hypothesis,
                "source_dimensions":    [
                    d for d in dims if signal.dim_sources.get(d, 0.0) > 0
                ],
            })

        dominant_score = 0.0
        if signal.ranked:
            dominant_score = float(signal.ranked[0][1] or 0.0)

        payload: Dict[str, Any] = {
            "dominant_type":      signal.dominant,
            "dominant_score":     round(dominant_score, 4),
            "classification_mode": classification_mode,
            "min_score":          float(min_score),
            "fallback_min_score": float(fallback_min_score),
            "active_biases":      biases,
            "axis_pressure":      signal.axis_sources,
            "last_updated":       float(time.time()),
            "pressure_scores":    {t: round(s, 4) for t, s in signal.ranked},
        }

        path = os.path.join(self.repo_root, _QUERY_BIAS_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=True)
            return {
                "dispatched":   True,
                "written_to":   _QUERY_BIAS_REL,
                "active_types": len(biases),
                "dominant":     signal.dominant,
                "mode":         classification_mode,
            }
        except Exception as exc:
            return {"dispatched": False, "error": str(exc)}


# ── Module-level convenience ──────────────────────────────────────────────────

def route_pressure(repo_root: str, fail_ledger: Any = None) -> Dict[str, Any]:
    """
    Module-level shortcut.  Call from aurora_runtime.py tick loop.
    """
    try:
        return PressureRouter(repo_root).route(fail_ledger=fail_ledger)
    except Exception as exc:
        return {"error": str(exc)}
