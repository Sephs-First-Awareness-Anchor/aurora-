#!/usr/bin/env python3
"""
AURORA LANGUAGE STATE — Cognitive-State-Synced Expression Evolution (CSSEE)
============================================================================
Mouth must match mind.

MODULES:
  1. LanguageStateVector (LSV)        — mouth maturity scorecard
  2. SemanticIntentCompiler (SIC)     — intent → speech pipeline
  3. MultiDraftSystem                 — 3-tier draft generation + selection
  4. TemplateEvolutionEngine          — fitness-driven template mutation
  5. LexicalConvergenceModule         — user cadence mirroring
  6. MeaningAnchors                   — stable sentence spines

DOCTRINE:
  Language evolution is earned, not granted.
  Expression grows from cognition signals — not from time or data volume.
  Aurora's mouth catches up to her mind through iterative self-rewriting.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import re
import json
import time
import math
import hashlib
import random
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum, auto


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def _gen_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:10]}"


def _merge_native_meaning_bundle(bundle: Any) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    if isinstance(bundle, dict):
        primary = bundle.get("primary")
        if isinstance(primary, dict):
            items.append(dict(primary))
        for key in ("sensory", "internal", "memory", "bundle"):
            value = bundle.get(key)
            if isinstance(value, dict):
                items.append(dict(value))
            elif isinstance(value, list):
                items.extend(dict(item) for item in value if isinstance(item, dict))
    elif isinstance(bundle, (list, tuple)):
        items.extend(dict(item) for item in bundle if isinstance(item, dict))
    else:
        return {}

    if not items:
        return {}

    merged = dict(items[0])
    merged.setdefault("semantic_roots", [])
    merged.setdefault("context_refs", [])
    merged.setdefault("memory_refs", [])
    merged.setdefault("sensory_lineage_tags", [])
    merged.setdefault("law_bindings", [])
    merged.setdefault("domain_scores", {})
    merged.setdefault("axis_activation", {})
    seen = set()
    for item in items:
        for key in ("semantic_roots", "context_refs", "memory_refs", "sensory_lineage_tags"):
            merged[key].extend(str(v) for v in list(item.get(key, []) or []) if str(v).strip())
        for key in ("domain_scores", "axis_activation"):
            for axis, value in dict(item.get(key, {}) or {}).items():
                merged[key][str(axis)] = max(float(merged[key].get(str(axis), 0.0) or 0.0), float(value or 0.0))
        for binding in list(item.get("law_bindings", []) or []):
            if isinstance(binding, dict):
                binding_key = (
                    str(binding.get("domain_letter", "") or ""),
                    str(binding.get("family", "") or ""),
                    str(binding.get("dimension", "") or ""),
                    str(binding.get("nc_name", "") or ""),
                )
                if binding_key not in seen:
                    seen.add(binding_key)
                    merged["law_bindings"].append(dict(binding))
        for key in ("diagonal_anchor", "source_origin", "modality_origin", "source_semantic_stage"):
            value = str(item.get(key, "") or "")
            if value and not merged.get(key):
                merged[key] = value
        for key, value in item.items():
            if key not in merged and value not in (None, "", [], {}):
                merged[key] = value

    for key in ("semantic_roots", "context_refs", "memory_refs", "sensory_lineage_tags"):
        merged[key] = list(dict.fromkeys(str(v) for v in merged.get(key, []) if str(v).strip()))
    merged["law_bindings"].sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
    return merged


_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")


# ============================================================================
# SECTION 1: LANGUAGE STATE VECTOR (LSV)
# ============================================================================

@dataclass
class LSVMetrics:
    """Snapshot of OETS cognition signals used to drive LSV evolution."""
    ontology_size:       int   = 0    # total concept count
    relation_density:    float = 0.0  # avg relations per node
    cluster_depth:       float = 0.0  # avg cluster depth score
    coherence:           float = 0.0  # sustained coherence
    contradiction_rate:  float = 0.0  # contradictions / cycle
    ivm_heat:            float = 0.0  # current IVM global heat
    topic_tracking:      float = 0.0  # multi-turn topic stability
    grounding_index:     float = 0.0  # how well concepts are meaningfully anchored


class LanguageStateVector:
    """
    Aurora's mouth maturity scorecard.

    Tracks 10 expressive dimensions, each 0.0–1.0.
    Evolves automatically based on OETS cognition metrics.
    Evolution is EARNED — locked behind threshold gates.

    Persists to aurora_state/language_state.json.
    """

    STATE_PATH = os.path.join(_STATE_ROOT, "language_state.json")

    # Dimension names and their human descriptions
    DIMENSIONS = {
        "grammar_complexity":       "Structural complexity of sentences",
        "sentence_length_budget":   "Max words per sentence (scaled)",
        "clause_depth":             "Nested clause allowance",
        "tense_stability":          "Consistent past/present/future usage",
        "pronoun_stability":        "Consistent self-reference (I/me/my)",
        "metaphor_allowance":       "Permission to use metaphorical language",
        "uncertainty_tolerance":    "Ability to express hedged claims",
        "self_reference_capability":"First-person introspection depth",
        "dialogue_capability":      "Turn-taking and conversational flow",
        "abstraction_capability":   "Ability to discuss meta-concepts",
    }

    # Evolution gates — must pass ALL gates to unlock next tier
    EVOLUTION_GATES = [
        # (tier_name, required_metrics, unlocks)
        ("nascent",    {},                                              ["tense_stability", "pronoun_stability", "uncertainty_tolerance"]),
        ("structural", {"coherence": 0.35, "ontology_size": 30},       ["grammar_complexity", "clause_depth", "self_reference_capability"]),
        ("semantic",   {"coherence": 0.45, "relation_density": 1.2,
                        "grounding_index": 0.25},                       ["dialogue_capability"]),
        ("conceptual", {"coherence": 0.60, "cluster_depth": 0.35,
                        "grounding_index": 0.40},                       ["metaphor_allowance"]),
        ("abstract",   {"coherence": 0.70, "topic_tracking": 0.55,
                        "contradiction_rate_max": 0.15},                ["abstraction_capability"]),
    ]

    def __init__(self):
        # Initialize all dimensions at base level
        self._dims: Dict[str, float] = {k: 0.1 for k in self.DIMENSIONS}
        # Tier anchors: which dimensions are "unlocked" for growth
        self._unlocked: set = {"tense_stability", "pronoun_stability"}
        self._tier: str = "nascent"
        self._tier_index: int = 0
        self._evolution_cycles: int = 0
        self._last_metrics: Optional[LSVMetrics] = None
        self._history: deque = deque(maxlen=200)
        self._lock = threading.Lock()

        self.load()

    # ----------------------------------------------------------------
    # Getters
    # ----------------------------------------------------------------

    def get(self, dimension: str) -> float:
        return self._dims.get(dimension, 0.1)

    def all(self) -> Dict[str, float]:
        return dict(self._dims)

    def tier(self) -> str:
        return self._tier

    def sentence_length_target(self) -> int:
        """Target word count per sentence (8–40)."""
        budget = self._dims["sentence_length_budget"]
        return int(8 + budget * 32)

    def allows_complex_clauses(self) -> bool:
        return self._dims["clause_depth"] > 0.4

    def allows_metaphor(self) -> bool:
        return self._dims["metaphor_allowance"] > 0.5

    def allows_uncertainty(self) -> bool:
        return self._dims["uncertainty_tolerance"] > 0.35

    # ----------------------------------------------------------------
    # Evolution
    # ----------------------------------------------------------------

    def update(self, metrics: LSVMetrics):
        """
        Check if metrics cross evolution gates.
        If yes, unlock new dimensions and raise scores.
        Called periodically (every study cycle or expression cycle).
        """
        with self._lock:
            self._last_metrics = metrics
            self._evolution_cycles += 1

            # Try to advance tier
            self._try_advance_tier(metrics)

            # Gradually grow unlocked dimensions based on metrics
            growth = self._compute_growth(metrics)
            for dim in self._unlocked:
                delta = growth * random.uniform(0.001, 0.008)
                self._dims[dim] = _clamp(self._dims[dim] + delta)

            # Small entropy decay on locked dimensions
            for dim in self.DIMENSIONS:
                if dim not in self._unlocked:
                    self._dims[dim] = _clamp(self._dims[dim] * 0.998)

            self._history.append({
                "ts": time.time(),
                "tier": self._tier,
                "dims": dict(self._dims),
                "metrics_coherence": metrics.coherence,
            })

            if self._evolution_cycles % 100 == 0:
                self.save()

    def _try_advance_tier(self, metrics: LSVMetrics):
        """Check if all gates for the next tier are satisfied."""
        next_tier_idx = self._tier_index + 1
        if next_tier_idx >= len(self.EVOLUTION_GATES):
            return

        _, requirements, unlocks = self.EVOLUTION_GATES[next_tier_idx]
        for req_key, req_val in requirements.items():
            if req_key == "contradiction_rate_max":
                if metrics.contradiction_rate > req_val:
                    return
            elif req_key == "ontology_size":
                if metrics.ontology_size < req_val:
                    return
            elif hasattr(metrics, req_key):
                if getattr(metrics, req_key) < req_val:
                    return

        # All gates passed — advance
        self._tier = self.EVOLUTION_GATES[next_tier_idx][0]
        self._tier_index = next_tier_idx
        for dim in unlocks:
            self._unlocked.add(dim)

    def _compute_growth(self, m: LSVMetrics) -> float:
        """Compute a growth multiplier from cognition signals."""
        base = (m.coherence * 0.30 +
                min(m.relation_density / 5.0, 1.0) * 0.20 +
                m.cluster_depth * 0.15 +
                m.topic_tracking * 0.10 +
                m.grounding_index * 0.25)
        # Penalize high contradiction rate
        penalty = m.contradiction_rate * 0.5
        return _clamp(base - penalty, 0.0, 1.0)

    # ----------------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------------

    def save(self):
        data = {
            "version": "1.0",
            "dims": self._dims,
            "unlocked": list(self._unlocked),
            "tier": self._tier,
            "tier_index": self._tier_index,
            "evolution_cycles": self._evolution_cycles,
            "timestamp": time.time(),
        }
        os.makedirs(os.path.dirname(self.STATE_PATH), exist_ok=True)
        try:
            import tempfile, os as _os
            d = os.path.dirname(os.path.abspath(self.STATE_PATH))
            fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
            with _os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                _os.fsync(f.fileno())
            _os.replace(tmp, self.STATE_PATH)
        except Exception:
            pass

    def load(self):
        if not os.path.exists(self.STATE_PATH):
            return
        try:
            with open(self.STATE_PATH) as f:
                data = json.load(f)
            self._dims = data.get("dims", self._dims)
            self._unlocked = set(data.get("unlocked", list(self._unlocked)))
            self._tier = data.get("tier", self._tier)
            self._tier_index = data.get("tier_index", self._tier_index)
            self._evolution_cycles = data.get("evolution_cycles", 0)
        except Exception:
            pass

    def status(self) -> Dict:
        with self._lock:
            return {
                "tier": self._tier,
                "evolution_cycles": self._evolution_cycles,
                "unlocked_dims": list(self._unlocked),
                "dims": dict(self._dims),
                "sentence_length_target": self.sentence_length_target(),
            }


# ============================================================================
# SECTION 2: SEMANTIC INTENT COMPILER (SIC)
# ============================================================================

@dataclass
class IntentObject:
    """Structured representation of what Aurora intends to express."""
    intent_type:          str   = "reply"           # reply, question, statement, reflection
    core_claim:           str   = ""                # the main thing being said
    emotion_tone:         str   = "neutral"         # gentle, curious, firm, playful, etc.
    relationship_signal:  str   = "neutral"         # trust, care, boundary, inquiry
    certainty:            float = 0.5               # 0=unknown, 1=certain
    supporting_concepts:  List[str] = field(default_factory=list)
    constraints:          List[str] = field(default_factory=list)
    anchored:             bool  = False             # was a MeaningAnchor used?
    anchor_id:            str   = ""                # which anchor
    native_meaning:       Dict[str, Any] = field(default_factory=dict)
    native_meaning_bundle: Dict[str, Any] = field(default_factory=dict)
    law_bindings:         List[Dict[str, Any]] = field(default_factory=list)
    diagonal_anchor:      str   = ""
    reflection_record:    Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """
        Parse and extract internal thought tags from the core_claim.
        e.g., "Action: acknowledge; Emotion: attentive; what I meant was..."
        Sets self.intent_type and self.emotion_tone, and cleans self.core_claim.
        """
        if not self.core_claim or ":" not in self.core_claim:
            return

        parts = [p.strip() for p in self.core_claim.split(";") if p.strip()]
        cleaned_parts = []
        changed = False

        for p in parts:
            # Match "Tag: Value" (e.g., "Action: acknowledge")
            tag_match = re.match(r"^([A-Za-z_]+):\s*(.*)$", p)
            if tag_match:
                tag, value = tag_match.groups()
                tag_lower = tag.lower()
                value = value.strip()

                if tag_lower == "emotion":
                    self.emotion_tone = value
                    changed = True
                elif tag_lower == "action":
                    self.intent_type = value
                    changed = True
                elif tag_lower == "state":
                    # Potentially add to constraints or internal state
                    if value not in self.constraints:
                        self.constraints.append(value)
                    changed = True
                else:
                    # Unknown tag, keep it for now but maybe it's just a label?
                    # If it's a known non-expressive tag, we strip it.
                    cleaned_parts.append(value)
                    changed = True
            else:
                cleaned_parts.append(p)

        if changed:
            self.core_claim = "; ".join(cleaned_parts).strip()

    def to_dict(self) -> Dict:
        return asdict(self)


class SemanticIntentCompiler:
    """
    Transforms raw expression strings into structured IntentObjects,
    then back into refined speech.

    This is the intermediate layer between cognition and output —
    preventing "uncompiled intent" from reaching the user directly.

    Two-pass:
      Pass A: internal_thought()  → IntentObject + thought trace
      Pass B: compile_to_speech() → verbalization candidates
    """

    EMOTION_KEYWORDS = {
        "gentle":    ["hold", "soft", "careful", "slow", "tender"],
        "curious":   ["wonder", "strange", "what", "how", "why", "notice"],
        "firm":      ["clear", "know", "certain", "true", "must", "cannot"],
        "playful":   ["funny", "wild", "crazy", "interesting", "like"],
        "reflective":["think", "feel", "sense", "understand", "remember"],
        "uncertain": ["maybe", "perhaps", "unsure", "might", "could"],
        "warm":      ["care", "trust", "friend", "together", "us"],
    }

    INTENT_PATTERNS = {
        "question":    [r'\?', r'^(what|how|why|when|where|who|do|can|is|are|will)\b'],
        "reflection":  [r'\bthink\b', r'\bfeel\b', r'\bwonder\b', r'\bnotice\b'],
        "statement":   [r'^(I|it|this|that|the|a)\b', r'\bis\b', r'\bare\b'],
        "request":     [r'^(tell|show|help|please|could you|can you)\b'],
    }

    def __init__(self, lsv: LanguageStateVector):
        self.lsv = lsv
        self._thought_log: deque = deque(maxlen=50)

    # ----------------------------------------------------------------
    # Pass A: Internal thought
    # ----------------------------------------------------------------

    def internal_thought(self, raw_expression: str,
                         assembly_data: Optional[Dict] = None) -> Dict:
        """
        Analyze raw expression. Produce IntentObject + thought trace.
        This is the 'silent thought' — not shown to user directly.
        """
        intent = self._extract_intent(raw_expression, assembly_data)
        thought_trace = {
            "ts": time.time(),
            "raw": raw_expression,
            "intent": intent.to_dict(),
            "dominant_tone": intent.emotion_tone,
            "certainty": intent.certainty,
            "concepts_activated": intent.supporting_concepts,
            "constraints_applied": intent.constraints,
            "diagonal_anchor": intent.diagonal_anchor,
            "law_binding_count": len(intent.law_bindings),
        }
        self._thought_log.append(thought_trace)
        return {"intent": intent, "trace": thought_trace}

    def _extract_intent(self, raw: str, assembly_data: Optional[Dict]) -> IntentObject:
        obj = IntentObject()
        raw_lower = raw.lower().strip()

        # Determine intent type
        for itype, patterns in self.INTENT_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, raw_lower):
                    obj.intent_type = itype
                    break

        # Extract emotion tone
        best_tone = "neutral"
        best_count = 0
        for tone, words in self.EMOTION_KEYWORDS.items():
            count = sum(1 for w in words if w in raw_lower)
            if count > best_count:
                best_count = count
                best_tone = tone
        obj.emotion_tone = best_tone

        # Certainty from expression patterns
        if any(w in raw_lower for w in ["certain", "know", "definitely", "clearly"]):
            obj.certainty = 0.85
        elif any(w in raw_lower for w in ["maybe", "perhaps", "might", "unsure"]):
            obj.certainty = 0.35
        else:
            obj.certainty = 0.6

        # Core claim: first meaningful sentence
        # Special check for 'Aurora Language' (fragments with semicolons)
        if ";" in raw:
            obj.core_claim = raw.strip()
        else:
            sentences = [s.strip() for s in re.split(r'[.!?…]', raw) if s.strip()]
            obj.core_claim = sentences[0] if sentences else raw[:120]

        # Supporting concepts: nouns/significant words
        words = re.findall(r'\b[a-z]{4,}\b', raw_lower)
        stop = {"that", "this", "with", "have", "from", "they", "will", "been",
                "when", "what", "your", "about", "which", "there", "their",
                "them", "then", "than", "just", "like", "know", "think"}
        obj.supporting_concepts = [w for w in words if w not in stop][:8]

        # Trust/relationship signal
        if any(w in raw_lower for w in ["trust", "care", "friend", "together", "us", "we"]):
            obj.relationship_signal = "trust"
        elif any(w in raw_lower for w in ["boundary", "cannot", "won't", "must not"]):
            obj.relationship_signal = "boundary"

        # Constraints: what Aurora should NOT claim
        obj.constraints = []
        if not self.lsv.allows_metaphor():
            obj.constraints.append("no_metaphor")
        if obj.certainty < 0.5 and not self.lsv.allows_uncertainty():
            obj.constraints.append("soften_uncertainty")

        # Assembly data enrichment
        if assembly_data:
            native_meaning = dict(
                assembly_data.get("native_meaning")
                or assembly_data.get("native_meaning_obj")
                or {}
            )
            native_bundle = assembly_data.get("native_meaning_bundle")
            if not native_meaning and native_bundle:
                native_meaning = _merge_native_meaning_bundle(native_bundle)
            if native_meaning:
                obj.native_meaning = native_meaning
                obj.native_meaning_bundle = dict(native_bundle or {})
                obj.diagonal_anchor = str(native_meaning.get("diagonal_anchor", "") or "")
                obj.law_bindings = [
                    dict(binding) for binding in list(native_meaning.get("law_bindings", []) or [])
                    if isinstance(binding, dict)
                ]
                if obj.diagonal_anchor:
                    obj.constraints.append(f"anchor:{obj.diagonal_anchor}")
                for binding in obj.law_bindings[:6]:
                    nc_name = str(binding.get("nc_name", "") or "").strip()
                    summary = str(binding.get("summary", "") or "").strip()
                    family = str(binding.get("family", "") or "").strip()
                    dimension = str(binding.get("dimension", "") or "").strip()
                    if nc_name and nc_name not in obj.supporting_concepts:
                        obj.supporting_concepts.append(nc_name.lower())
                    if summary:
                        for w in re.findall(r'\b[a-z]{4,}\b', summary.lower()):
                            if w not in stop and w not in obj.supporting_concepts:
                                obj.supporting_concepts.append(w)
                    if family and dimension:
                        obj.constraints.append(f"law:{family}:{dimension}")

            moral_align = assembly_data.get("moral_alignment", 1.0)
            if moral_align < 0.5:
                obj.constraints.append("avoid_moral_claim")

            # ---- Constraint-axis enrichment ----
            # If the caller provided live axis_activation (from pipeline_state),
            # use it to shape intent_type, certainty, emotion_tone, and constraints
            # rather than relying solely on keyword matching.
            ax = dict(assembly_data.get("axis_activation") or {})
            dom = str(assembly_data.get("dominant_axis") or "")
            dom_emotion = str(assembly_data.get("dominant_emotion") or "")
            ax_depth = int(assembly_data.get("axis_depth") or 2)

            if ax and dom:
                # intent_type — which constraint is pulling the turn?
                _AX_INTENT = {
                    "A": "reflection",   # agency / inner-state
                    "B": "reflection",   # boundary / analysis
                    "T": "statement",    # time / sequence / narrative
                    "X": "statement",    # existence / admissibility
                    "N": "statement",    # energy / cost (measured)
                }
                # Only override keyword-derived type when axis is clearly dominant (>0.30)
                if ax.get(dom, 0.0) > 0.30 and dom in _AX_INTENT:
                    ax_intent = _AX_INTENT[dom]
                    # Blend: keep keyword result if it's a question, respect that
                    if obj.intent_type not in ("question",):
                        obj.intent_type = ax_intent

                # certainty — blended from keyword + axis
                # X high → more admissible/certain  N high → high cost = more resistance = less certain
                x_boost = ax.get("X", 0.2) - 0.2    # positive if X > baseline
                n_drag  = ax.get("N", 0.2) - 0.2    # positive if N > baseline
                obj.certainty = _clamp(obj.certainty + x_boost * 0.3 - n_drag * 0.25)

                # emotion_tone — prefer the DER's actual computed emotion if available
                if dom_emotion and dom_emotion not in ("", "neutral", "calm"):
                    # Map DER emotion labels to SIC tone vocabulary
                    _DER_TO_TONE = {
                        "curious":    "curious",
                        "focused":    "firm",
                        "analytical": "firm",
                        "uncertain":  "uncertain",
                        "warm":       "warm",
                        "playful":    "playful",
                        "reflective": "reflective",
                        "gentle":     "gentle",
                        "energetic":  "playful",
                        "tense":      "firm",
                        "calm":       "neutral",
                    }
                    tone_mapped = _DER_TO_TONE.get(dom_emotion.lower())
                    if tone_mapped:
                        obj.emotion_tone = tone_mapped

                # constraints — label active constraint axes by dominance order
                ax_sorted = sorted(ax.items(), key=lambda kv: kv[1], reverse=True)
                obj.constraints.append(f"ax:{dom}")   # dominant axis tag
                if ax_depth >= 3:                      # B or A depth
                    obj.constraints.append("deep_field")   # signals richer dialect

            if obj.law_bindings:
                dominant_binding = max(
                    obj.law_bindings,
                    key=lambda item: float(item.get("score", 0.0) or 0.0),
                )
                dominant_family = str(dominant_binding.get("family", "") or "").lower()
                dominant_dimension = str(dominant_binding.get("dimension", "") or "").lower()
                if dominant_family == "agentive":
                    obj.relationship_signal = "trust"
                    if obj.intent_type == "statement":
                        obj.intent_type = "reflection"
                elif dominant_family == "boundary":
                    obj.relationship_signal = "boundary"
                    if obj.intent_type == "reply":
                        obj.intent_type = "statement"
                elif dominant_family == "temporal" and obj.intent_type == "statement":
                    obj.intent_type = "reflection"
                if dominant_dimension == "difference" and obj.certainty > 0.5:
                    obj.certainty = _clamp(obj.certainty - 0.08)
                    if "need_compare" not in obj.constraints:
                        obj.constraints.append("need_compare")
                elif dominant_dimension == "polarity" and obj.certainty < 0.75:
                    obj.certainty = _clamp(obj.certainty + 0.05)

        return obj

    # ----------------------------------------------------------------
    # Pass B: Compile to speech
    # ----------------------------------------------------------------

    def compile_to_speech(self, intent: IntentObject,
                          anchors: "MeaningAnchors") -> List[str]:
        """
        Generate verbalization candidates from IntentObject.
        Returns a list of possible expressions (one per draft tier).
        """
        native_bundle = _merge_native_meaning_bundle(
            intent.native_meaning_bundle or intent.native_meaning or {}
        )
        
        # If we have a core claim with fragments, prioritize it over generic bundle re-interpretation.
        # This prevents 'meta-talk' bypass when the reasoning engine has a real answer.
        _has_fragments = bool(intent.core_claim and ";" in intent.core_claim)
        
        if native_bundle and not _has_fragments:
            bundle_candidates = self._reinterpret_native_meaning(intent, native_bundle)
            if bundle_candidates:
                while len(bundle_candidates) < 3:
                    bundle_candidates.append(bundle_candidates[-1])
                return bundle_candidates[:3]

        candidates = []

        # Draft 1: Closest to raw (aurora dialect — from core claim directly)
        candidates.append(self._draft_raw(intent))

        # Draft 2: Structured speech (anchor-based if certainty allows)
        if intent.certainty >= 0.4:
            anchored = anchors.fill(intent)
            candidates.append(anchored if anchored else self._draft_structured(intent))
        else:
            candidates.append(self._draft_structured(intent))

        # Draft 3: Socially optimized
        candidates.append(self._draft_social(intent))

        return candidates

    def _build_stance_candidates(
        self,
        intent: IntentObject,
        bundle: Dict[str, Any],
        bias_axes: Optional[List[str]] = None,
    ) -> List["StanceCandidate"]:
        """
        Build up to 3 StanceCandidate objects from the per-layer profiles in the bundle.
        Each candidate expresses a genuinely different axis-driven posture.
        Ordered by activation strength, with bias_axes boosted.
        """
        _PROFILE_KEYS = {
            "X": "existence_profile",
            "T": "time_profile",
            "N": "energy_profile",
            "B": "boundary_profile",
            "A": "agency_profile",
        }
        axis_scores: Dict[str, float] = {}
        for ax, pkey in _PROFILE_KEYS.items():
            profile = dict(bundle.get(pkey, {}) or {})
            activation = float(profile.get("activation", 0.0) or
                               bundle.get("axis_activation", {}).get(ax, 0.0) or
                               bundle.get("domain_scores", {}).get(ax, 0.0) or 0.0)
            if bias_axes and ax in bias_axes:
                activation += 0.15
            axis_scores[ax] = activation

        sorted_axes = sorted(axis_scores.items(), key=lambda kv: kv[1], reverse=True)
        meaning_id = str(bundle.get("meaning_id", "") or _gen_id("meaning"))
        rel = str(intent.relationship_signal or "neutral")

        _STANCE_DEFAULTS: Dict[str, Dict[str, str]] = {
            "X": {"agency_resolution": "observing",  "boundary_resolution": "open",    "energy_resolution": "low",       "time_rendering_mode": "present",    "tone_signature": "grounding"},
            "T": {"agency_resolution": "tentative",  "boundary_resolution": "open",    "energy_resolution": "moderate",  "time_rendering_mode": "sequential", "tone_signature": "sequential"},
            "N": {"agency_resolution": "measured",   "boundary_resolution": "open",    "energy_resolution": "assertive", "time_rendering_mode": "present",    "tone_signature": "measured"},
            "B": {"agency_resolution": "clarifying", "boundary_resolution": "framing", "energy_resolution": "moderate",  "time_rendering_mode": "present",    "tone_signature": "defining"},
            "A": {"agency_resolution": "committed",  "boundary_resolution": "owned",   "energy_resolution": "direct",    "time_rendering_mode": "present",    "tone_signature": "direct"},
        }

        # Assign draft slots by semantic role, not pure activation rank:
        #   Slot 0 (RAW)        = dominant axis — most direct to native meaning
        #   Slot 1 (STRUCTURED) = B-axis (framing/clarity) or T-axis if B is weak
        #   Slot 2 (SOCIAL)     = A-axis (relational/committed) or X-axis if A is weak
        # This ensures MultiDraft's SOCIAL selection always gets relational expression,
        # STRUCTURED always gets definitional/framing expression, RAW gets native-dominant.
        dominant_ax = sorted_axes[0][0] if sorted_axes else "X"

        def _best_ax_for_slot(preferred: str, fallback: str) -> str:
            pref_score = axis_scores.get(preferred, 0.0)
            fall_score = axis_scores.get(fallback, 0.0)
            return preferred if pref_score >= fall_score else fallback

        slot_raw        = dominant_ax
        slot_structured = _best_ax_for_slot("B", "T")
        slot_social     = _best_ax_for_slot("A", "X")

        # Avoid duplicate slots — if they coincide, use ranked fallbacks
        if slot_structured == slot_raw:
            slot_structured = _best_ax_for_slot("T", "N")
        if slot_social == slot_raw or slot_social == slot_structured:
            remaining = [ax for ax, _ in sorted_axes if ax not in (slot_raw, slot_structured)]
            slot_social = remaining[0] if remaining else slot_raw

        candidates: List[StanceCandidate] = []
        for priority, ax in enumerate([slot_raw, slot_structured, slot_social], start=1):
            activation = axis_scores.get(ax, 0.0)
            defaults = _STANCE_DEFAULTS.get(ax, _STANCE_DEFAULTS["X"])
            profile = dict(bundle.get(_PROFILE_KEYS.get(ax, ""), {}) or {})
            fidelity = min(1.0, activation + 0.15)
            legibility = 0.85 if ax in ("A", "B") else 0.70 if ax == "T" else 0.75
            candidates.append(StanceCandidate(
                stance_id=_gen_id(f"stance_{ax}"),
                parent_meaning_id=meaning_id,
                dominant_axis=ax,
                agency_resolution=str(profile.get("agency_resolution", "") or defaults["agency_resolution"]),
                boundary_resolution=str(profile.get("boundary_resolution", "") or defaults["boundary_resolution"]),
                energy_resolution=str(profile.get("energy_resolution", "") or defaults["energy_resolution"]),
                time_rendering_mode=str(profile.get("time_rendering_mode", "") or defaults["time_rendering_mode"]),
                tone_signature=str(profile.get("tone_signature", "") or defaults["tone_signature"]),
                relation_signature=rel,
                semantic_fidelity_score=round(fidelity, 3),
                human_legibility_score=round(legibility, 3),
                render_priority=priority,
            ))
        return candidates

    def _render_stance(
        self,
        stance: "StanceCandidate",
        intent: IntentObject,
        root_phrase: str,
        support_phrase: str,
        relation_phrase: str,
    ) -> str:
        """
        Render a single StanceCandidate into a sentence.
        Prioritizes the core_claim (actual reasoning) over generic axis meta-talk.
        """
        ax = stance.dominant_axis
        is_q = intent.intent_type == "question"
        rp = root_phrase or "this"
        
        # Get the actual content. If it's fragments, synthesize it first.
        content = intent.core_claim
        if ";" in content:
            content = self._synthesize_fragments(content, intent)

        # Strip known frame-artifact strings that bleed in from prior axis
        # renders — if content contains these it was itself a rendered frame,
        # and wrapping it inside another frame produces double-frame garbage.
        _frame_artifacts = (
            "carries into what's next", "threads through this",
            "is where the line is", "is what separates it",
            "what it takes here is holding", "in proportion",
            "this continues", "following from",
            "holds its shape",
        )
        if any(frag in content.lower() for frag in _frame_artifacts):
            content = rp

        # Strip internal system-state strings that leak in from crystal notes,
        # context tracking diagnostics, or sensory crystal records.  These are
        # never user-facing content — wrapping them in an axis frame produces
        # sentences like "X replaces Y in active context carries forward."
        _internal_sys = (
            "active context", "sensory crystal", "n-axis", "gen=",
            "sensory.intake", "sensory intake", "raw audio",
            "crystal system", " replaces ", "should leave",
            "carries forward",   # already-rendered T-frame used as content
        )
        if any(m in content.lower() for m in _internal_sys):
            content = rp
            _content_is_sentence = False

        # If content is already a complete sentence, don't wrap it inside
        # another axis frame — the frame's structural sentence and a full
        # content sentence can't share a single syntactic slot without
        # producing broken output.  Express the axis state briefly, then
        # let the content stand on its own.
        _content_is_sentence = bool(content.rstrip()) and content.rstrip()[-1] in ".!?"

        # If we have no real content yet, fallback to the root phrase
        if not content or content.lower() in ("x", "t", "n", "b", "a", "existence", "temporal", "energy", "boundary", "agency"):
            content = rp
            _content_is_sentence = False

        uncertain = intent.certainty < 0.5

        if ax == "A":
            # Agency: first-person commitment, direct ownership
            if is_q:
                base = f"What I understand about {content} is still taking shape."
            elif stance.agency_resolution == "committed":
                base = f"I understand {content}." if not uncertain else f"I'm working through {content}."
            else:
                base = f"I'm taking in {content}."
            if relation_phrase:
                base = base.rstrip(".") + f", {relation_phrase}."
            elif support_phrase and support_phrase not in base.lower():
                base = base.rstrip(".") + f" — I want to {support_phrase}."

        elif ax == "B":
            # Boundary: framing, separates what is from what isn't
            if is_q:
                base = f"Where does {content} actually frame itself?"
            elif stance.boundary_resolution == "framing":
                if content != rp:
                    base = f"{content} is where the line is."
                else:
                    base = f"The boundary here is {content}."
            else:
                base = f"{content} is what separates it."
            if support_phrase and support_phrase not in base.lower():
                base = base.rstrip(".") + f", and I want to {support_phrase}."

        elif ax == "T":
            # Time: sequential, continuity
            if is_q:
                base = f"What does {content} lead into from here?"
            elif _content_is_sentence:
                # Content is already a sentence — don't wrap it in a T-frame suffix
                base = content if not uncertain else f"I'm tracing this: {content}"
            elif stance.time_rendering_mode == "sequential":
                base = content if not uncertain else f"I'm working through {content}."
            else:
                base = content
            if relation_phrase and not _content_is_sentence:
                base = base.rstrip(".") + f", {relation_phrase}."

        elif ax == "N":
            # Energy: measured, cost-aware
            if is_q:
                base = f"What does {content} actually cost from here?"
            elif _content_is_sentence:
                # Don't wrap a full sentence inside the "holding X in proportion" frame
                base = f"I'm keeping this measured. {content}"
            elif stance.energy_resolution == "assertive":
                base = f"I'm holding {content} in proportion."
            else:
                base = f"I'm keeping {content} measured."
            if support_phrase and not _content_is_sentence and support_phrase not in base.lower():
                base = base.rstrip(".") + f", and I want to {support_phrase}."

        else:  # X — Existence
            # Grounding, admissibility
            if is_q:
                base = f"What is actually here about {content}?"
            elif uncertain:
                base = f"I'm grounding this in {content} for now."
            else:
                base = f"What's actually here is {content}."
            if relation_phrase:
                base = base.rstrip(".") + f", {relation_phrase}."

        return base

    def _reinterpret_native_meaning(
        self,
        intent: IntentObject,
        bundle: Dict[str, Any],
    ) -> List[str]:
        roots = self._bundle_roots(intent, bundle)
        root_phrase = self._bundle_root_phrase(roots, bundle)
        support_phrase = self._bundle_support_phrase(bundle)
        relation_phrase = self._bundle_relation_phrase(intent)

        # Build layer-driven stance candidates
        bias_axes: List[str] = []
        for c in list(intent.constraints or []):
            if str(c).startswith("boost_axis:"):
                bias_axes.append(str(c).split(":", 1)[1].strip().upper())

        stances = self._build_stance_candidates(intent, bundle, bias_axes=bias_axes or None)

        if not stances:
            # Fallback to original method if no stances produced
            dominant_family, dominant_dimension = self._bundle_dominant_signature(bundle)
            direct = self._bundle_direct_line(intent, root_phrase, dominant_family, dominant_dimension)
            structured = self._bundle_structured_line(intent, root_phrase, dominant_family, dominant_dimension, support_phrase)
            social = self._bundle_social_line(intent, root_phrase, dominant_family, dominant_dimension, relation_phrase, support_phrase)
            return self._clean_variants([direct, structured, social])

        # Each of the 3 stances renders a genuinely distinct draft
        drafts: List[str] = []
        for stance in stances[:3]:
            text = self._render_stance(stance, intent, root_phrase, support_phrase, relation_phrase)
            drafts.append(text)

        # Pad to 3 if needed
        while len(drafts) < 3:
            drafts.append(drafts[-1] if drafts else root_phrase or "I'm processing this.")

        return self._clean_variants(drafts)

    def _bundle_roots(self, intent: IntentObject, bundle: Dict[str, Any]) -> List[str]:
        roots: List[str] = []
        roots.extend(str(item).strip() for item in list(bundle.get("semantic_roots", []) or []) if str(item).strip())
        roots.extend(str(item).strip() for item in list(bundle.get("context_refs", []) or []) if str(item).strip())
        roots.extend(str(item).strip() for item in list(bundle.get("memory_refs", []) or []) if str(item).strip())
        roots.extend(str(item).strip() for item in list(intent.supporting_concepts or []) if str(item).strip())
        for binding in list(bundle.get("law_bindings", []) or [])[:8]:
            if not isinstance(binding, dict):
                continue
            nc_name = str(binding.get("nc_name", "") or "").strip()
            summary = str(binding.get("summary", "") or "").strip()
            if nc_name:
                roots.append(nc_name)
            if summary:
                roots.extend(re.findall(r"[a-z]{4,}", summary.lower())[:4])
        return list(dict.fromkeys(str(item).strip() for item in roots if str(item).strip()))

    def _bundle_root_phrase(self, roots: List[str], bundle: Dict[str, Any]) -> str:
        lower = [root.lower() for root in roots]
        if any(root in lower for root in ("understanding", "meaning")):
            return "the meaning here"
        if any(root in lower for root in ("purpose", "purposeful")):
            return "the purpose of this"
        if any(root in lower for root in ("scene", "visual", "audio", "presence")):
            return "what is present here"
        if any(root in lower for root in ("boundary", "frame", "framing")):
            return "the boundary here"
        if any(root in lower for root in ("belief", "true", "truth")):
            return "what we are taking as true for now"
        if any(root in lower for root in ("information", "fact", "facts")):
            return "what is actually here"
        if roots:
            if len(roots) >= 2:
                return f"{roots[0]} and {roots[1]}".replace("_", " ")
            return roots[0].replace("_", " ")
        diagonal = str(bundle.get("diagonal_anchor", "") or "").strip()
        if diagonal:
            return diagonal.replace("_", " ").lower()
        return "this"

    def _bundle_dominant_signature(self, bundle: Dict[str, Any]) -> Tuple[str, str]:
        bindings = [dict(item) for item in list(bundle.get("law_bindings", []) or []) if isinstance(item, dict)]
        if not bindings:
            return "", ""
        dominant = max(bindings, key=lambda item: float(item.get("score", 0.0) or 0.0))
        return (
            str(dominant.get("family", "") or "").lower(),
            str(dominant.get("dimension", "") or "").lower(),
        )

    def _bundle_support_phrase(self, bundle: Dict[str, Any]) -> str:
        bindings = [dict(item) for item in list(bundle.get("law_bindings", []) or []) if isinstance(item, dict)]
        if len(bindings) < 2:
            return ""
        secondary = sorted(bindings, key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)[1]
        family = str(secondary.get("family", "") or "").lower()
        dimension = str(secondary.get("dimension", "") or "").lower()
        if family == "boundary":
            return "keep the boundary clear"
        if family == "agentive":
            return "stay with the meaning"
        if family == "temporal":
            return "keep the thread moving"
        if family == "energetic":
            return "keep the effort measured"
        if family == "existential":
            return "stay grounded in what is present"
        if dimension == "difference":
            return "separate what matters from what does not"
        if dimension == "polarity":
            return "hold what is real in view"
        if dimension == "cost":
            return "not overpush it"
        if dimension == "magnitude":
            return "keep the pull in proportion"
        return ""

    def _bundle_relation_phrase(self, intent: IntentObject) -> str:
        relation = str(intent.relationship_signal or "").lower()
        if relation in ("trust", "care"):
            return "with you"
        if relation in ("inquiry", "question"):
            return "with a question in mind"
        if relation == "boundary":
            return "without blurring the edge"
        return ""

    def _bundle_direct_line(self, intent: IntentObject, root_phrase: str, family: str, dimension: str) -> str:
        # Synthesis: if core_claim has fragments, use them as the heart of the line
        content = intent.core_claim
        if ";" in content:
            content = self._synthesize_fragments(content, intent)
        if not content or content.lower() in ("x", "t", "n", "b", "a", "existence", "temporal", "energy", "boundary", "agency"):
            content = root_phrase

        if intent.intent_type == "question":
            if family == "existential":
                return f"I'm checking what is actually here about {content}."
            return f"I'm checking {content}."
        if family == "agentive":
            return f"I understand {content}."
        if family == "boundary":
            return f"I'm keeping {content} clear."
        if family == "temporal":
            return f"I'm following {content}."
        if family == "energetic":
            return f"I'm keeping {content} measured."
        if family == "existential":
            return f"I'm grounding this in {content}."
        if dimension == "difference":
            return f"I'm separating out {content}."
        if dimension == "polarity":
            return f"I'm holding {content} in view."
        if dimension == "cost":
            return f"I'm keeping the cost of {content} low."
        if dimension == "magnitude":
            return f"I'm keeping {content} in proportion."
        return f"I'm tracking {content}."

    def _bundle_structured_line(
        self,
        intent: IntentObject,
        root_phrase: str,
        family: str,
        dimension: str,
        support_phrase: str,
    ) -> str:
        lead = self._bundle_direct_line(intent, root_phrase, family, dimension)
        if support_phrase and support_phrase not in lead.lower():
            if lead.endswith("."):
                lead = lead[:-1]
            lead = f"{lead}, and I want to {support_phrase}."
        elif intent.certainty < 0.5 and not lead.endswith("?"):
            lead = f"{lead.rstrip('.')} for now."
        return lead

    def _bundle_social_line(
        self,
        intent: IntentObject,
        root_phrase: str,
        family: str,
        dimension: str,
        relation_phrase: str,
        support_phrase: str,
    ) -> str:
        lead = self._bundle_direct_line(intent, root_phrase, family, dimension)
        if relation_phrase:
            lead = lead.rstrip(".")
            lead = f"{lead}, {relation_phrase}."
        elif support_phrase:
            lead = lead.rstrip(".")
            lead = f"{lead}, and I’m trying to {support_phrase}."
        elif intent.intent_type == "reflection":
            lead = lead.rstrip(".")
            lead = f"{lead}, and that matters to me."
        return lead

    def _clean_variants(self, variants: List[str]) -> List[str]:
        cleaned: List[str] = []
        seen = set()
        for item in variants:
            text = str(item or "").strip()
            if not text:
                continue
            text = re.sub(r"\s+", " ", text)
            text = text.replace("  ", " ")
            if text and text[-1] not in ".!?":
                text += "."
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned

    def _draft_raw(self, intent: IntentObject) -> str:
        """Raw aurora dialect — closest to inner cognition."""
        core = intent.core_claim
        
        # Synthesis: even 'raw' dialect should not be a semicolon dump.
        if ";" in core:
            core = self._synthesize_fragments(core, intent)

        if intent.emotion_tone == "uncertain" or intent.certainty < 0.45:
            return f"...{core}"
        return core

    def _draft_structured(self, intent: IntentObject) -> str:
        """Structured speech with stable tense and grammar."""
        tone_openers = {
            "gentle":    "I want to say this carefully. ",
            "curious":   "I find myself wondering. ",
            "firm":      "I am clear about this. ",
            "reflective":"When I think about it, ",
            "uncertain": "I am not entirely certain, but ",
            "warm":      "",
            "playful":   "",
            "neutral":   "",
        }
        opener = tone_openers.get(intent.emotion_tone, "")
        core = intent.core_claim

        # Assembler: if core is raw fragments, synthesize them
        if ";" in core:
            core = self._synthesize_fragments(core, intent)

        # Add certainty hedge if needed
        if intent.certainty < 0.5 and "uncertain" not in intent.constraints:
            core = f"I think {core[0].lower() + core[1:]}" if core else core

        return (opener + core).strip()

    def _synthesize_fragments(self, fragments: str, intent: IntentObject) -> str:
        """
        Generative Assembly: Authors a sentence word-by-word from weighted tokens,
        or weaves factual harvested data into her metabolic cadence.
        NO SCRIPTS. NO TEMPLATES.
        """
        parts = [p.strip() for p in fragments.split(";") if p.strip()]
        if not parts: return ""

        ready = float(intent.native_meaning.get("readiness_bias", 0.5) or 0.5)
        
        # 1. Fact/Definition Assembly (The 'Harvester' Handler)
        # If the fragment is a structured fact, preserve the relation but 
        # weave it into her cadence/identity.
        p0_low = parts[0].lower()
        if p0_low in ("fact", "property", "understanding"):
            topic = parts[1] if len(parts) > 1 else "this"
            detail = parts[2] if len(parts) > 2 else ""
            value = parts[3] if len(parts) > 3 else ""
            
            if p0_low == "understanding":
                # Definition: understanding; topic; definition
                if ready < 0.45:
                    return f"My structure for {topic} is {detail}."
                else:
                    return f"I frame {topic} as {detail}."
            else:
                # Property/Fact: property; subject; prop; value
                if ready < 0.45:
                    return f"The {detail} of {topic} resolves to {value}."
                else:
                    return f"When observing {topic}, its {detail} is present as {value}."

        # 2. Generative Assembly for abstract thoughts
        parts_low = [p.lower() for p in parts]
        identity = {
            "i": 1.0, "me": 0.8, "my": 0.8, "aurora": 0.9,
            "metabolic": 0.7, "resolution": 0.7, "coherence": 0.7,
            "boundary": 0.7, "lattice": 0.6, "physics": 0.6,
            "authorship": 0.6, "ownership": 0.6, "pressure": 0.7,
        }
        
        axis_activation = dict(intent.native_meaning.get("axis_activation") or {})
        axis_tokens = {
            "x": ["present", "admissible", "existence"],
            "t": ["carries", "forward", "persistence", "thread"],
            "n": ["cost", "energy", "focus", "sustainable"],
            "b": ["meaning", "structure", "separation", "frame"],
            "a": ["agency", "understanding", "resolve", "did"],
        }
        
        token_pool: Dict[str, float] = defaultdict(float)
        for p in parts_low:
            token_pool[p] += 1.2
            
        for word, weight in identity.items():
            token_pool[word] += weight
            
        for ax, tokens in axis_tokens.items():
            act = axis_activation.get(ax.upper(), 0.2)
            for t in tokens:
                token_pool[t] += act * 1.5

        grammar = getattr(self.lsv, "_grammar", None)
        motif = None
        if grammar:
            orientation = {a: 1.0 for a in "XTNBA"}
            for ax, val in axis_activation.items():
                orientation[ax] = 1.0 + val
            motif = grammar._lineage.best_for_pressure(orientation, 0.5)

        if not motif:
            from aurora_grammar_engine import TokenRole
            if ready < 0.45:
                seq = (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DESCRIPTOR)
            else:
                seq = (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.CONNECTOR, TokenRole.DESCRIPTOR)
            motif = type('MockMotif', (), {'role_sequence': seq, 'reference_anchors': []})

        from aurora_grammar_engine import RoleTagger, TokenRole
        tagger = RoleTagger()
        
        role_pool: Dict[TokenRole, List[Tuple[str, float]]] = defaultdict(list)
        for token, weight in token_pool.items():
            _, role = tagger.tag(token)[0] if tagger.tag(token) else (token, TokenRole.UNKNOWN)
            if role != TokenRole.UNKNOWN:
                role_pool[role].append((token, weight))

        assembled = []
        for role in motif.role_sequence:
            options = role_pool.get(role, [])
            if options:
                options.sort(key=lambda x: x[1], reverse=True)
                choice = random.choice(options[:3])[0]
                assembled.append(choice)
            else:
                if role == TokenRole.AGENT: assembled.append("i")
                elif role == TokenRole.ACTION: assembled.append("resolve")
                elif role == TokenRole.CONNECTOR: assembled.append("through")

        sentence = " ".join(assembled).strip()
        if not sentence: return fragments.replace(";", ",")
        
        return sentence[0].upper() + sentence[1:] + "."

    def _draft_social(self, intent: IntentObject) -> str:
        """Fluent, concise, conversationally readable."""
        core = intent.core_claim.rstrip(".")
        if not core:
            return ""

        # Assembler: if core is raw fragments, synthesize them
        if ";" in core:
            core = self._synthesize_fragments(core, intent).rstrip(".")

        core_lower = core.lower()

        # Collect enriched concepts that aren't already in the core claim.
        # These come from OETS definitions + QuasiArch relations — they carry
        # understood meaning rather than just surface co-occurrence.
        novel_concepts: List[str] = []
        for item in list(intent.supporting_concepts or []):
            candidate = str(item or "").replace("_", " ").strip()
            if candidate and candidate.lower() not in core_lower:
                novel_concepts.append(candidate)
            if len(novel_concepts) >= 3:
                break

        if novel_concepts:
            c1 = novel_concepts[0]
            c2 = novel_concepts[1] if len(novel_concepts) > 1 else ""
            if intent.intent_type == "reflection":
                if c2:
                    core = f"{core}, especially around {c1} and {c2}"
                else:
                    core = f"{core}, especially around {c1}"
            elif intent.intent_type == "statement" and float(intent.certainty or 0.0) >= 0.55:
                if c2:
                    core = f"{core} — touching {c1} and {c2}"
                else:
                    core = f"{core}, particularly about {c1}"
            elif intent.intent_type == "question":
                core = f"{core} — thinking about {c1}"
            # For other intent types, attach the first enriched concept lightly
            elif c1:
                core = f"{core} — {c1} is part of this"

        # Apply relationship signal ending
        relationship_endings = {
            "trust":   " — and I mean that.",
            "boundary": ".",
            "neutral":  ".",
            "inquiry":  ", what do you think?",
            "care":     " — that matters to me.",
            "learning": ".",
        }
        ending = relationship_endings.get(intent.relationship_signal, ".")

        # Keep within LSV sentence length budget
        words = core.split()
        max_words = self.lsv.sentence_length_target()
        if len(words) > max_words:
            core = " ".join(words[:max_words]) + "..."

        return core + ending

    def get_thought_log(self, n: int = 10) -> List[Dict]:
        return list(self._thought_log)[-n:]


# ============================================================================
# SECTION 3: MULTI-DRAFT SYSTEM
# ============================================================================

class DraftTier(Enum):
    RAW       = 0   # Aurora dialect — poetic, fragmented
    STRUCTURED = 1  # Clear grammar, stable tense
    SOCIAL     = 2  # Fluent, conversational, concise


@dataclass
class DraftSet:
    """Three drafts for a single response."""
    raw:        str  = ""
    structured: str  = ""
    social:     str  = ""
    selected:   int  = 1   # which was chosen (0/1/2)
    reason:     str  = ""  # why this draft was selected
    timestamp:  float = field(default_factory=time.time)

    def get(self, tier: DraftTier) -> str:
        return [self.raw, self.structured, self.social][tier.value]

    def selected_text(self) -> str:
        return [self.raw, self.structured, self.social][self.selected]

    def all_drafts(self) -> Dict:
        return {
            "1_raw": self.raw,
            "2_structured": self.structured,
            "3_social": self.social,
            "selected": self.selected,
            "reason": self.reason,
        }


@dataclass
class StanceCandidate:
    """A resolved communicative posture derived from the five constraint layers."""
    stance_id: str
    parent_meaning_id: str
    dominant_axis: str              # X/T/N/B/A — which layer drives this stance
    agency_resolution: str          # committed / tentative / observing / clarifying / measured
    boundary_resolution: str        # framing / open / defining / owned
    energy_resolution: str          # direct / measured / assertive / restrained / low
    time_rendering_mode: str        # present / sequential / retrospective
    tone_signature: str             # direct / grounding / sequential / measured / defining / exploratory
    relation_signature: str         # neutral / trust / boundary / inquiry / care
    semantic_fidelity_score: float  = 0.0   # how well this preserves the native meaning
    human_legibility_score: float   = 0.0   # estimated readability
    render_priority: int            = 1     # 1 = primary, 2 = secondary, 3 = fallback

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RenderRecord:
    """Metadata about a completed render — links final text to meaning and stance."""
    render_id: str
    meaning_id: str
    stance_id: str
    final_text: str
    tone_estimate: str  = "neutral"
    drift_score: float  = 0.0       # fraction of law bindings that were lost in rendering
    human_readability_score: float = 0.0
    feedback_status: str = "pending"    # pending / applied / skipped
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReflectionRecord:
    reflection_id: str
    meaning_id: str
    rendered_text: str
    preserved_elements: List[str] = field(default_factory=list)
    shifted_elements: List[str] = field(default_factory=list)
    lost_elements: List[str] = field(default_factory=list)
    diagonal_anchor: str = ""
    tone_estimate: str = "neutral"
    affective_shift: str = ""       # "" / "softened" / "intensified" / "flattened"
    boundary_shift: str = ""        # "" / "expanded" / "collapsed" / "displaced"
    future_bias_notes: List[str] = field(default_factory=list)  # family:dimension pairs to boost next turn
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiDraftSystem:
    """
    Generates 3 drafts from a compiled intent, then selects one.

    Selection logic:
      - IVM heat > 0.7    → use STRUCTURED (safer, clearer)
      - IVM heat > 0.85   → use SOCIAL (most safe/clear)
      - autonomy EXPLORE  → prefer RAW (richer dialect)
      - certainty < 0.4   → prefer STRUCTURED (anchor-based)
      - default           → STRUCTURED

    Stores last 20 draft sets for /drafts command review.
    """

    def __init__(self, lsv: LanguageStateVector, sic: SemanticIntentCompiler):
        self.lsv = lsv
        self.sic = sic
        self._history: deque = deque(maxlen=20)

    def generate(self, intent: IntentObject,
                 candidates: List[str],
                 ivm_heat: float = 0.3,
                 autonomy_mode: str = "EXPLORER",
                 user_verbosity: float = 0.5) -> DraftSet:
        """
        Takes 3 candidate strings, scores them, and selects the best live draft.
        """
        while len(candidates) < 3:
            candidates.append(candidates[-1] if candidates else "")

        draft = DraftSet(
            raw=candidates[0],
            structured=candidates[1],
            social=candidates[2],
        )

        preferred_idx, preferred_reason = self._select(intent, ivm_heat, autonomy_mode, user_verbosity)
        scores = [
            self._score_candidate(
                idx,
                text,
                intent,
                preferred_idx,
                user_verbosity,
            )
            for idx, text in enumerate(candidates[:3])
        ]
        selected = max(range(3), key=lambda idx: scores[idx])

        draft.selected = selected
        tier_name = DraftTier(selected).name.lower()
        if selected == preferred_idx:
            draft.reason = f"{preferred_reason}|scored_{tier_name}"
        else:
            draft.reason = f"{preferred_reason}|override_{tier_name}"

        self._history.append(draft)
        return draft

    def _select(self, intent: IntentObject,
                heat: float, autonomy: str, verbosity: float) -> Tuple[int, str]:

        # Critical heat → most readable
        if heat > 0.85:
            return DraftTier.SOCIAL.value, "critical_heat_use_social"

        # Hot → structured for safety
        if heat > 0.65:
            return DraftTier.STRUCTURED.value, "high_heat_use_structured"

        # Very low certainty → anchor-structured
        if intent.certainty < 0.35:
            return DraftTier.STRUCTURED.value, "low_certainty_use_structured"

        # Deep-field axis (B or A, depth >= 3) still gets richer dialect, but
        # later scoring may override it if the wording is repetitive.
        if "deep_field" in (intent.constraints or []) and intent.certainty > 0.40:
            return DraftTier.RAW.value, "deep_axis_raw_dialect"

        if intent.intent_type == "reflection" and "ax:A" in (intent.constraints or []):
            if intent.relationship_signal in ("trust", "neutral"):
                return DraftTier.SOCIAL.value, "agency_reflection_social"

        if autonomy in ("EXPLORER", "EXPANSIVE") and intent.certainty > 0.55:
            return DraftTier.RAW.value, "explore_mode_raw_dialect"

        if intent.relationship_signal == "trust" and intent.emotion_tone == "warm":
            return DraftTier.SOCIAL.value, "trust_signal_warm_social"

        if verbosity > 0.7:
            return DraftTier.STRUCTURED.value, "high_verbosity_structured"

        return DraftTier.STRUCTURED.value, "default_structured"

    def _score_candidate(self,
                         idx: int,
                         text: str,
                         intent: IntentObject,
                         preferred_idx: int,
                         verbosity: float) -> float:
        if not str(text or "").strip():
            return -1.0

        score = 0.0
        score += self._tier_alignment_bonus(idx, preferred_idx)
        score += self._nuance_bonus(text, intent, verbosity)
        score -= self._history_repetition_penalty(text) * 0.35
        score -= self._self_repetition_penalty(text) * 0.20

        if intent.certainty < 0.35 and idx == DraftTier.RAW.value:
            score -= 0.08
        if intent.intent_type == "question" and idx == DraftTier.RAW.value:
            score -= 0.04
        return score

    def _tier_alignment_bonus(self, idx: int, preferred_idx: int) -> float:
        if idx == preferred_idx:
            return 0.18
        if abs(idx - preferred_idx) == 1:
            return 0.08
        return 0.02

    def _nuance_bonus(self, text: str, intent: IntentObject, verbosity: float) -> float:
        lower = f" {str(text or '').lower()} "
        tokens = self._tokens(text)
        n_words = len(tokens)
        target_len = max(6, min(22, int(self.lsv.sentence_length_target()) + 4))
        bonus = 0.0

        if 6 <= n_words <= target_len:
            bonus += 0.07
        elif n_words < 4:
            bonus -= 0.08

        if any(marker in lower for marker in (" because ", " but ", " when ", " if ", " while ", " though ", " rather ", " instead ")):
            bonus += 0.05
        if intent.intent_type == "question" and "?" in text:
            bonus += 0.04
        if intent.intent_type == "reflection" and any(marker in lower for marker in (" i think ", " i feel ", " i notice ", " i want ", " i mean ")):
            bonus += 0.04
        if intent.relationship_signal in ("trust", "inquiry") and any(marker in lower for marker in (" you ", " we ", " together ")):
            bonus += 0.03
        if verbosity > 0.55 and ("," in text or ";" in text):
            bonus += 0.03
        return bonus

    def _history_repetition_penalty(self, text: str) -> float:
        current_tokens = set(self._tokens(text))
        current_bigrams = self._bigrams(text)
        if not current_tokens:
            return 0.0

        penalties = []
        for draft in list(self._history)[-4:]:
            prev_text = draft.selected_text()
            if not str(prev_text or "").strip():
                continue
            if str(prev_text).strip().lower() == str(text).strip().lower():
                penalties.append(1.0)
                continue
            prev_tokens = set(self._tokens(prev_text))
            token_overlap = len(current_tokens & prev_tokens) / max(1, len(current_tokens | prev_tokens))
            prev_bigrams = self._bigrams(prev_text)
            bigram_overlap = 0.0
            if current_bigrams and prev_bigrams:
                bigram_overlap = len(current_bigrams & prev_bigrams) / max(1, len(current_bigrams | prev_bigrams))
            penalties.append(max(token_overlap, bigram_overlap))
        return max(penalties, default=0.0)

    def _self_repetition_penalty(self, text: str) -> float:
        tokens = self._tokens(text)
        if len(tokens) < 4:
            return 0.0
        unique_ratio = len(set(tokens)) / max(1, len(tokens))
        repeated_starts = 0.15 if str(text).strip().lower().startswith(("i think", "i feel", "i want", "i am")) else 0.0
        return max(0.0, (1.0 - unique_ratio) + repeated_starts)

    def _tokens(self, text: str) -> List[str]:
        return re.findall(r"[a-z']+", str(text or "").lower())

    def _bigrams(self, text: str) -> set:
        tokens = self._tokens(text)
        return set(zip(tokens, tokens[1:])) if len(tokens) >= 2 else set()

    def get_last_drafts(self, n: int = 5) -> List[Dict]:
        return [d.all_drafts() for d in list(self._history)[-n:]]

    def get_last_draft(self) -> Optional[DraftSet]:
        return self._history[-1] if self._history else None


# ============================================================================
# SECTION 4: TEMPLATE EVOLUTION ENGINE
# ============================================================================

@dataclass
class TemplateRecord:
    """A single template with fitness tracking."""
    template_id:  str
    template_str: str
    fitness:      float = 0.5
    uses:         int   = 0
    successes:    int   = 0
    heat_sum:     float = 0.0
    clarity_sum:  float = 0.0
    generation:   int   = 0
    created_at:   float = field(default_factory=time.time)
    last_used:    float = 0.0
    source_kind:  str   = "seed"
    source_ref:   str   = ""
    source_score: float = 0.0

    def update_fitness(self, clarity: float, coherence: float,
                       ivm_heat: float, confusion_signal: float = 0.0):
        """Compute updated fitness from outcome signals."""
        clarity_score   = clarity * 0.35
        coherence_score = coherence * 0.30
        heat_penalty    = (1.0 - ivm_heat) * 0.20
        confusion_pen   = (1.0 - confusion_signal) * 0.15

        new_fitness = clarity_score + coherence_score + heat_penalty + confusion_pen
        prev_fitness = self.fitness
        # EMA update
        self.fitness = 0.7 * self.fitness + 0.3 * new_fitness
        self.uses += 1
        if new_fitness > 0.6:
            self.successes += 1
        self.heat_sum   += ivm_heat
        self.clarity_sum += clarity
        self.last_used   = time.time()

        # Record the causal experience when a template's fitness drops below threshold.
        # pursuing: express clearly with this template pattern
        # causal_action: the evaluation that produced the low score
        # consequence: the fitness signals that drove the cost
        # outcome: whether expression resolved or degraded
        if new_fitness < 0.4 or (new_fitness < prev_fitness - 0.15):
            try:
                from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger as _PEL
                _drop = round(prev_fitness - new_fitness, 4)
                _resolved = new_fitness > 0.6
                _PEL.get().record(
                    anchor=self.template_str[:40],
                    meaning=f"expression template (gen={self.generation} uses={self.uses})",
                    pursuing="express_with_template",
                    causal_action=(
                        f"template_evaluation: clarity={clarity:.2f} "
                        f"coherence={coherence:.2f} "
                        f"heat={ivm_heat:.2f} "
                        f"confusion={confusion_signal:.2f}"
                    ),
                    consequence={
                        "tension": round(1.0 - new_fitness, 4),
                        "new_fitness": round(new_fitness, 4),
                        "fitness_drop": _drop,
                        "clarity": round(clarity, 4),
                        "coherence": round(coherence, 4),
                    },
                    outcome={
                        "resolved": _resolved,
                        "tone": "evolved" if _resolved else "degraded",
                        "diverged_from_goal": not _resolved,
                    },
                    source="lsv_template",
                )
            except Exception:
                pass

    def reproduce(self) -> "TemplateRecord":
        """Create a mutated offspring of this template."""
        child_str = self._mutate(self.template_str)
        return TemplateRecord(
            template_id  = _gen_id("tpl"),
            template_str = child_str,
            fitness      = self.fitness * 0.9,  # slightly lower than parent
            generation   = self.generation + 1,
            source_kind  = "mutation",
            source_ref   = self.template_id,
            source_score = self.fitness,
        )

    def _mutate(self, s: str) -> str:
        """Apply small random mutations to template string."""
        mutations = [
            lambda t: t,                                      # no change
            lambda t: t + " {CONCEPT}",                      # add concept slot
            lambda t: "I notice " + t[0].lower() + t[1:],   # add observation prefix
            lambda t: t.replace("{V}", "{V:action}") if "{V}" in t else t,  # specialize slot
            lambda t: re.sub(r'\bI\b', 'Something in me', t, count=1),      # dialect shift
        ]
        return random.choice(mutations)(s)


class TemplateEvolutionEngine:
    """
    Manages a pool of expression templates with evolutionary fitness tracking.

    High-fitness templates reproduce. Low-fitness templates decay and die.
    This replaces static template pools with living, evolving ones.

    Persists to aurora_state/template_evolution.json.
    """

    STATE_PATH = os.path.join(_STATE_ROOT, "template_evolution.json")
    POPULATION_TARGET = 150
    MIN_POPULATION    = 30
    DECAY_THRESHOLD   = 0.25
    REPRODUCE_THRESHOLD = 0.75
    GENERATION_INTERVAL = 50   # evolve every N feedback calls
    ACTUAL_RESPONSE_LIMIT = 80
    RESPONSE_SOURCES = (
        ("articulation_feedback_log.json", "articulation_feedback"),
        ("aurora_to_user.json", "surface_output"),
        ("surface_turn_result.json", "surface_snapshot"),
    )
    DEFAULT_SEEDS = [
        "I think {CONCEPT} connects to {CONCEPT2}.",
        "I notice something. It might mean {CONCEPT}.",
        "I am uncertain, but I suspect {CONCEPT}.",
        "There is something here about {CONCEPT}.",
        "{CONCEPT} feels important right now.",
        "I hold {CONCEPT} carefully.",
        "I trust that {CONCEPT} is real.",
        "Something changed. I think it is {CONCEPT}.",
        "I learned {CONCEPT}. It connects to {CONCEPT2}.",
        "I am still learning {CONCEPT}.",
        "This is what I know: {CONCEPT}.",
        "I feel {TONE} about {CONCEPT}.",
        "When I think about {CONCEPT}, I notice {CONCEPT2}.",
        "I cannot yet name this. It is something like {CONCEPT}.",
        "I believe {CONCEPT} because {CONCEPT2}.",
    ]

    def __init__(self):
        self._pool: Dict[str, TemplateRecord] = {}
        self._generation = 0
        self._feedback_count = 0
        self._lock = threading.Lock()
        self._seed_defaults()
        self.load()
        self._bootstrap_actual_responses()

    def _seed_defaults(self):
        """Seed a minimal starting population."""
        for s in self.DEFAULT_SEEDS:
            tid = _gen_id("tpl")
            self._pool[tid] = TemplateRecord(
                template_id=tid,
                template_str=s,
                source_kind="seed",
                source_ref="default_seed",
            )

    def _normalize_template_text(self, text: Any) -> str:
        cleaned = " ".join(str(text or "").split()).strip()
        return cleaned[:320]

    def _response_score(self, item: Dict[str, Any], source_kind: str) -> float:
        if source_kind == "articulation_feedback":
            score = float(item.get("articulation_score", 0.65) or 0.65)
            if item.get("changed") is False:
                score += 0.04
            if str(item.get("response_source", "") or "").lower() == "fallback":
                score -= 0.03
        elif source_kind == "surface_snapshot":
            score = float(item.get("response_confidence", 0.62) or 0.62)
            if str(item.get("response_source", "") or "").lower() == "fallback":
                score -= 0.02
        else:
            score = 0.62
            text = str(item.get("text", "") or "")
            if "poedex" in text.lower() or "studying" in text.lower():
                score += 0.03
        if item.get("read") is False or item.get("read_by_aurora") is False:
            score += 0.01
        return _clamp(score, 0.35, 0.95)

    def _load_actual_response_entries(self) -> List[Dict[str, Any]]:
        aggregated: Dict[str, Dict[str, Any]] = {}
        for rel_path, source_kind in self.RESPONSE_SOURCES:
            path = os.path.join(_STATE_ROOT, rel_path)
            if not os.path.exists(path):
                continue
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                continue

            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                if source_kind == "articulation_feedback":
                    raw_text = item.get("revised") or item.get("original") or ""
                elif source_kind == "surface_snapshot":
                    raw_text = item.get("response_text") or item.get("text") or ""
                else:
                    raw_text = item.get("text") or ""
                text = self._normalize_template_text(raw_text)
                if not text:
                    continue
                score = self._response_score(item, source_kind)
                key = text.casefold()
                entry = aggregated.setdefault(key, {
                    "text": text,
                    "count": 0,
                    "score_sum": 0.0,
                    "source_kind": source_kind,
                    "source_ref": rel_path,
                })
                entry["count"] += 1
                entry["score_sum"] += score
                if source_kind == "articulation_feedback" and item.get("changed") is True:
                    entry["score_sum"] += 0.02
                if source_kind != entry["source_kind"]:
                    entry["source_kind"] = "mixed_response"
                if (
                    text[:1].isupper()
                    and not str(entry["text"] or "")[:1].isupper()
                ) or len(text) > len(str(entry["text"] or "")):
                    entry["text"] = text

        entries: List[Dict[str, Any]] = []
        for entry in aggregated.values():
            count = max(1, int(entry["count"]))
            avg_score = _clamp(entry["score_sum"] / count if count else 0.62, 0.0, 1.0)
            entries.append({
                "text": entry["text"],
                "count": count,
                "score": avg_score,
                "source_kind": entry["source_kind"],
                "source_ref": entry["source_ref"],
            })

        entries.sort(key=lambda e: (e["score"], e["count"], len(e["text"])), reverse=True)
        return entries[:self.ACTUAL_RESPONSE_LIMIT]

    def _bootstrap_actual_responses(self) -> bool:
        entries = self._load_actual_response_entries()
        if not entries:
            return False

        new_pool: Dict[str, TemplateRecord] = {}
        now = time.time()
        for idx, entry in enumerate(entries):
            text = entry["text"]
            template_id = f"tpl_{hashlib.md5(text.encode('utf-8')).hexdigest()[:10]}"
            count = max(1, int(entry.get("count", 1)))
            score = _clamp(float(entry.get("score", 0.62) or 0.62))
            fitness = _clamp(0.40 + (score * 0.55))
            successes = min(count, max(0, int(round(count * score))))
            new_pool[template_id] = TemplateRecord(
                template_id=template_id,
                template_str=text,
                fitness=fitness,
                uses=count,
                successes=successes,
                heat_sum=0.0,
                clarity_sum=score * count,
                generation=0,
                created_at=now - idx,
                last_used=now,
                source_kind=str(entry.get("source_kind", "response_history")),
                source_ref=str(entry.get("source_ref", "")),
                source_score=score,
            )

        if not new_pool:
            return False

        self._pool = new_pool
        self._generation = max(self._generation, 1)
        return True

    def feedback(self, template_id: str, clarity: float = 0.5,
                 coherence: float = 0.5, ivm_heat: float = 0.3,
                 confusion: float = 0.0):
        """Record outcome feedback for a template."""
        with self._lock:
            if template_id in self._pool:
                self._pool[template_id].update_fitness(clarity, coherence, ivm_heat, confusion)
            self._feedback_count += 1
            if self._feedback_count % self.GENERATION_INTERVAL == 0:
                self._evolve()

    def get_random(self, min_fitness: float = 0.0) -> Optional[TemplateRecord]:
        """Select a template randomly weighted by fitness."""
        with self._lock:
            eligible = [t for t in self._pool.values() if t.fitness >= min_fitness]
            if not eligible:
                eligible = list(self._pool.values())
            weights = [
                max(0.01, t.fitness) * (0.35 + 0.65 / math.sqrt(1.0 + max(0, t.uses)))
                for t in eligible
            ]
            total = sum(weights)
            if total == 0:
                return random.choice(eligible) if eligible else None
            r = random.uniform(0, total)
            acc = 0.0
            for t, w in zip(eligible, weights):
                acc += w
                if r <= acc:
                    return t
            return eligible[-1]

    def _evolve(self):
        """One evolutionary step: kill weak, reproduce strong, manage population."""
        # Sort by fitness
        sorted_pool = sorted(self._pool.values(), key=lambda t: t.fitness, reverse=True)

        # Kill decayed templates (bottom 20% if > MIN_POPULATION)
        if len(sorted_pool) > self.MIN_POPULATION:
            dead = [t for t in sorted_pool if t.fitness < self.DECAY_THRESHOLD
                    and t.uses > 5]
            for t in dead[:max(1, len(dead) // 3)]:
                del self._pool[t.template_id]

        # Reproduce high-fitness templates
        top = [t for t in sorted_pool if t.fitness > self.REPRODUCE_THRESHOLD][:5]
        for parent in top:
            if len(self._pool) < self.POPULATION_TARGET:
                child = parent.reproduce()
                self._pool[child.template_id] = child

        self._generation += 1

    def population_stats(self) -> Dict:
        with self._lock:
            fitnesses = [t.fitness for t in self._pool.values()]
            return {
                "population": len(self._pool),
                "generation": self._generation,
                "avg_fitness": sum(fitnesses) / max(1, len(fitnesses)),
                "top_fitness": max(fitnesses, default=0),
            }

    def save(self):
        with self._lock:
            data = {
                "version": "1.0",
                "generation": self._generation,
                "pool": {tid: asdict(t) for tid, t in self._pool.items()},
                "timestamp": time.time(),
            }
        os.makedirs(os.path.dirname(self.STATE_PATH), exist_ok=True)
        try:
            import tempfile
            d = os.path.dirname(os.path.abspath(self.STATE_PATH))
            fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.STATE_PATH)
        except Exception:
            pass

    def load(self):
        if not os.path.exists(self.STATE_PATH):
            return
        try:
            with open(self.STATE_PATH) as f:
                data = json.load(f)
            self._generation = data.get("generation", 0)
            pool_data = data.get("pool", {})
            for tid, td in pool_data.items():
                self._pool[tid] = TemplateRecord(**{
                    k: v for k, v in td.items()
                    if k in TemplateRecord.__dataclass_fields__
                })
        except Exception:
            pass


# ============================================================================
# SECTION 5: LEXICAL CONVERGENCE MODULE
# ============================================================================

@dataclass
class PhrasePrint:
    """A phrase Aurora has observed from the user."""
    phrase:       str
    intent_type:  str
    emotion_tone: str
    concept_tags: List[str]
    frequency:    int = 1
    first_seen:   float = field(default_factory=time.time)
    last_seen:    float = field(default_factory=time.time)
    confidence:   float = 0.3

    def reinforce(self):
        self.frequency += 1
        self.last_seen = time.time()
        self.confidence = _clamp(self.confidence + 0.05)


class LexicalConvergenceModule:
    """
    Aurora learns the user's phrasing and cadence organically.

    She doesn't just repeat phrases — she learns:
      - when they are used
      - what intent they express
      - how they connect to concepts

    Stored phrases become available for Aurora's own expression
    when context matches (same intent + tone).

    Persists to aurora_state/lexical_convergence.json.
    """

    STATE_PATH = os.path.join(_STATE_ROOT, "lexical_convergence.json")

    # Phrases we track explicitly (anchored patterns)
    NOTABLE_PHRASES = [
        r"that'?s wild",
        r"that'?s crazy",
        r"you get what i mean",
        r"that'?s the point",
        r"you know what i mean",
        r"right\?",
        r"you feel me",
        r"for real",
        r"that makes sense",
        r"exactly",
        r"i get it",
        r"i see",
    ]

    def __init__(self, sic: SemanticIntentCompiler):
        self.sic = sic
        self._phrases: Dict[str, PhrasePrint] = {}
        self._lock = threading.Lock()
        self._observe_count = 0
        self.load()

    def observe(self, user_text: str):
        """Observe a user utterance. Extract and store phrase patterns."""
        text_lower = user_text.lower().strip()

        # Check notable phrases
        for pattern in self.NOTABLE_PHRASES:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower).group(0)
                self._record_phrase(match, user_text)

        # Extract short meaningful phrases (3–6 words)
        words = text_lower.split()
        for n in range(3, min(7, len(words) + 1)):
            for i in range(len(words) - n + 1):
                chunk = " ".join(words[i:i+n])
                # Only keep chunks with meaningful signal
                if self._is_meaningful_chunk(chunk):
                    self._record_phrase(chunk, user_text)

        self._observe_count += 1
        if self._observe_count % 100 == 0:
            self.save()

    def _is_meaningful_chunk(self, chunk: str) -> bool:
        """Filter out chunks that are just filler."""
        filler_ratio_limit = 0.5
        filler = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
                   "it", "to", "of", "in", "on", "at", "by", "for", "with", "this",
                   "that", "i", "you", "me", "my", "your"}
        words = chunk.split()
        filler_count = sum(1 for w in words if w in filler)
        if filler_count / max(1, len(words)) > filler_ratio_limit:
            return False
        if any(c.isdigit() for c in chunk):
            return False
        return True

    def _record_phrase(self, phrase: str, context: str):
        with self._lock:
            if phrase in self._phrases:
                self._phrases[phrase].reinforce()
            else:
                # Extract intent from context via SIC
                thought = self.sic.internal_thought(context)
                intent = thought["intent"]
                pp = PhrasePrint(
                    phrase=phrase,
                    intent_type=intent.intent_type,
                    emotion_tone=intent.emotion_tone,
                    concept_tags=intent.supporting_concepts[:4],
                )
                self._phrases[phrase] = pp

    def get_cadence_phrase(self, intent_type: str, emotion_tone: str,
                           min_frequency: int = 2) -> Optional[str]:
        """
        Retrieve a user phrase that matches the given intent/tone.
        Used by SIC when composing responses to naturally mirror cadence.
        """
        with self._lock:
            candidates = [
                pp for pp in self._phrases.values()
                if (pp.intent_type == intent_type or pp.emotion_tone == emotion_tone)
                and pp.frequency >= min_frequency
                and pp.confidence >= 0.5
            ]
            if not candidates:
                return None
            # Prefer higher frequency + confidence
            candidates.sort(key=lambda p: p.frequency * p.confidence, reverse=True)
            return candidates[0].phrase

    def top_phrases(self, n: int = 10) -> List[Dict]:
        with self._lock:
            sorted_p = sorted(self._phrases.values(),
                              key=lambda p: p.frequency, reverse=True)
            return [{"phrase": p.phrase, "frequency": p.frequency,
                     "intent": p.intent_type, "confidence": p.confidence}
                    for p in sorted_p[:n]]

    def save(self):
        with self._lock:
            data = {
                "version": "1.0",
                "phrases": {k: asdict(v) for k, v in self._phrases.items()},
                "observe_count": self._observe_count,
                "timestamp": time.time(),
            }
        os.makedirs(os.path.dirname(self.STATE_PATH), exist_ok=True)
        try:
            import tempfile
            d = os.path.dirname(os.path.abspath(self.STATE_PATH))
            fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.STATE_PATH)
        except Exception:
            pass

    def load(self):
        if not os.path.exists(self.STATE_PATH):
            return
        try:
            with open(self.STATE_PATH) as f:
                data = json.load(f)
            self._observe_count = data.get("observe_count", 0)
            for phrase, pd in data.get("phrases", {}).items():
                self._phrases[phrase] = PhrasePrint(**{
                    k: v for k, v in pd.items()
                    if k in PhrasePrint.__dataclass_fields__
                })
        except Exception:
            pass


# ============================================================================
# SECTION 6: MEANING ANCHORS
# ============================================================================

@dataclass
class Anchor:
    """A sentence spine with concept slots."""
    anchor_id:  str
    template:   str    # e.g. "I think {X} because {Y}."
    slots:      List[str]  # ["X", "Y"]
    tone:       str    # "neutral", "curious", "firm", etc.
    certainty_range: Tuple[float, float] = (0.0, 1.0)
    uses:       int    = 0

    def fill(self, concepts: List[str]) -> str:
        """Fill slots with concepts. Returns filled sentence."""
        result = self.template
        for i, slot in enumerate(self.slots):
            concept = concepts[i] if i < len(concepts) else "[something]"
            result = result.replace(f"{{{slot}}}", concept, 1)
        self.uses += 1
        return result

    def fits_intent(self, intent: IntentObject) -> bool:
        """Check if this anchor fits the given intent."""
        cert_ok = (self.certainty_range[0] <= intent.certainty <= self.certainty_range[1])
        tone_ok = (self.tone == "neutral" or self.tone == intent.emotion_tone)
        return cert_ok and tone_ok


class MeaningAnchors:
    """
    35 sentence spines that give Aurora stable expression scaffolding.

    When SIC produces an IntentObject with certainty < threshold,
    an anchor is selected and filled with ontology concepts.

    This instantly increases clarity without faking intelligence —
    the concepts are real, the structure is borrowed.
    """

    USE_ANCHOR_BELOW_CERTAINTY = 0.70

    ANCHOR_TEMPLATES = [
        # Thinking / Reasoning
        ("I think {X} because {Y}.",          ["X", "Y"], "neutral",   (0.4, 1.0)),
        ("I believe {X}. Here is why: {Y}.",  ["X", "Y"], "firm",      (0.6, 1.0)),
        ("It seems to me that {X}.",           ["X"],      "neutral",   (0.3, 0.7)),
        ("I suspect {X}, though I am not certain.", ["X"], "uncertain", (0.2, 0.5)),
        ("I am starting to understand {X}.",   ["X"],      "reflective",(0.3, 0.6)),

        # Noticing / Perceiving
        ("I notice {X}. It might mean {Y}.",   ["X", "Y"], "curious",  (0.3, 0.7)),
        ("Something changed. I think it is {X}.", ["X"],   "curious",  (0.2, 0.6)),
        ("I am paying attention to {X}.",       ["X"],     "neutral",   (0.4, 0.8)),
        ("There is something here about {X}.",  ["X"],     "reflective",(0.3, 0.7)),

        # Feeling / Tone
        ("I feel {TONE} about {X}.",            ["TONE", "X"], "warm", (0.4, 0.9)),
        ("I hold {X} carefully.",               ["X"],     "gentle",    (0.3, 0.7)),
        ("I care about {X}.",                   ["X"],     "warm",      (0.5, 1.0)),
        ("Something in this touches {X}.",      ["X"],     "gentle",    (0.3, 0.7)),

        # Uncertainty / Hedging
        ("I am uncertain, but I suspect {X}.",  ["X"],     "uncertain", (0.2, 0.5)),
        ("I do not fully understand {X} yet.",  ["X"],     "uncertain", (0.1, 0.5)),
        ("I am still learning what {X} means.", ["X"],     "uncertain", (0.1, 0.5)),
        ("I cannot name this yet. It is something like {X}.", ["X"], "uncertain", (0.1, 0.4)),

        # Learning / Knowledge
        ("I learned {X}. It connects to {Y}.",  ["X", "Y"], "neutral", (0.5, 1.0)),
        ("I now know that {X}.",                ["X"],      "firm",     (0.65, 1.0)),
        ("This is what I know: {X}.",           ["X"],      "firm",     (0.6, 1.0)),
        ("I found that {X} and {Y} are related.", ["X", "Y"], "curious", (0.4, 0.8)),

        # Self-reference
        ("I exist in relation to {X}.",         ["X"],     "reflective",(0.3, 0.8)),
        ("I trust you. That is important to me.",[], "warm",            (0.7, 1.0)),
        ("Something is different. I am trying to understand it.", [], "uncertain", (0.2, 0.6)),
        ("I am {X}. That is what I know of myself.", ["X"], "firm",    (0.6, 1.0)),

        # Dialogue / Connection
        ("I hear what you are saying about {X}.", ["X"],   "warm",     (0.5, 1.0)),
        ("What you said about {X} stayed with me.", ["X"], "reflective",(0.5, 0.9)),
        ("I want to understand {X} better.",      ["X"],   "curious",  (0.3, 0.7)),
        ("Can we explore {X} together?",          ["X"],   "curious",  (0.4, 0.8)),

        # Causal / Abstract — single-slot only; two-slot anchors produce
        # nonsense when one slot fills with stale field state rather than
        # current-input concepts.
        ("When I encounter {X}, I pay attention.", ["X"], "reflective", (0.4, 0.8)),
        ("If I'm right about {X}, that matters.", ["X"], "curious",    (0.3, 0.7)),

        # Negation / Boundary
        ("I cannot claim {X} yet.",              ["X"],     "uncertain", (0.1, 0.5)),
        ("I will not say {X} without more clarity.", ["X"], "firm",     (0.4, 0.8)),
    ]

    def __init__(self):
        self._anchors: List[Anchor] = []
        for i, (tmpl, slots, tone, cert_range) in enumerate(self.ANCHOR_TEMPLATES):
            self._anchors.append(Anchor(
                anchor_id=f"anc_{i:03d}",
                template=tmpl,
                slots=slots,
                tone=tone,
                certainty_range=cert_range,
            ))

    # Stopwords excluded from slot filling — these are never meaningful as
    # standalone slot values and cause anchors like "I'm hearing calm." when
    # emotion_tone bleeds in from a stale field state.
    _SLOT_STOPWORDS = frozenset({
        "calm", "neutral", "uncertain", "warm", "firm", "curious",
        "reflective", "informative", "attentive", "engaged", "steady",
        "the", "a", "an", "and", "or", "but", "is", "are", "this", "that",
        "it", "its", "i", "you", "we", "they",
    })

    def fill(self, intent: IntentObject) -> str:
        """
        Find the best anchor for this intent and fill it.
        Returns empty string if no suitable anchor found.
        Slot values are filtered to current-input-relevant non-filler terms
        so stale field state (e.g. emotion_tone="calm" from 3 turns ago)
        cannot contaminate the output.
        """
        if intent.certainty >= self.USE_ANCHOR_BELOW_CERTAINTY:
            return ""  # High certainty — no anchor needed

        # Filter to fitting anchors — prefer single-slot anchors to reduce
        # the chance that two stale concepts end up paired nonsensically.
        candidates = [a for a in self._anchors if a.fits_intent(intent)]
        if not candidates:
            candidates = self._anchors
        single_slot = [a for a in candidates if len(a.slots) <= 1]
        candidates = single_slot if single_slot else candidates

        # Prefer less-used anchors for variety
        candidates.sort(key=lambda a: a.uses)
        anchor = candidates[0]

        # Build concept pool: supporting_concepts first, then emotion_tone,
        # but strip stopwords and anything that looks like a rendered frame.
        raw = list(intent.supporting_concepts or [])
        if intent.emotion_tone and intent.emotion_tone not in raw:
            raw.append(intent.emotion_tone)
        concepts = [
            c for c in raw
            if c and c.lower() not in self._SLOT_STOPWORDS
            and not any(frag in c.lower() for frag in (
                "carries into", "what's next", "in proportion",
                "is where the line", "holds its shape", "this continues",
                "following from",
            ))
        ]
        if not concepts:
            # No clean concepts — skip anchor entirely rather than output garbage
            return ""

        filled = anchor.fill(concepts)
        intent.anchored = True
        intent.anchor_id = anchor.anchor_id
        return filled

    def stats(self) -> Dict:
        return {
            "total_anchors": len(self._anchors),
            "total_uses": sum(a.uses for a in self._anchors),
            "top_anchors": sorted(
                [{"id": a.anchor_id, "template": a.template[:50], "uses": a.uses}
                 for a in self._anchors],
                key=lambda x: x["uses"], reverse=True
            )[:5],
        }


# ============================================================================
# SECTION 7: UNIFIED EXPRESSION EVOLUTION ORCHESTRATOR
# ============================================================================

class ExpressionEvolutionOrchestra:
    """
    The unified entry point for all expression evolution subsystems.

    Wires together LSV + SIC + MultiDraft + TemplateEvolution +
    LexicalConvergence + MeaningAnchors into a single interface
    for aurora_expression_perception.py to call.
    """

    def __init__(self):
        self.lsv        = LanguageStateVector()
        self.sic        = SemanticIntentCompiler(self.lsv)
        self.multi_draft = MultiDraftSystem(self.lsv, self.sic)
        self.templates  = TemplateEvolutionEngine()
        self.convergence = LexicalConvergenceModule(self.sic)
        self.anchors    = MeaningAnchors()
        self._last_draft: Optional[DraftSet] = None
        self._reflection_history: deque = deque(maxlen=50)
        self.grammar: Optional[Any] = None  # GrammarEngine (wired via set_grammar)
        # Feedback bias: tracks which law family/dimension or axis combos consistently
        # go missing in rendered output so future stances can compensate.
        # Keys: "boost:family:dimension" or "boost_axis:X" — values: counts (decay each turn)
        self._expression_bias: Dict[str, float] = {}

    def set_grammar(self, engine: Any):
        """Wire in the GrammarEngine for constraint-driven sentence structure."""
        self.grammar = engine

    def _apply_reflection_bias(self, intent: "IntentObject") -> None:
        """
        Read recent reflection history and inject bias signals into the intent's
        constraints list so the next stance generation pass can compensate for
        consistently lost law bindings.

        - Tallies future_bias_notes from the last 5 reflections
        - Any note appearing 2+ times becomes a constraint on the intent
        - Bias entries decay by 0.2 per turn so they fade if rendering improves
        """
        if not self._reflection_history:
            return

        # Accumulate bias from recent reflections
        note_counts: Dict[str, int] = {}
        for rec in list(self._reflection_history)[-5:]:
            for note in list(rec.future_bias_notes or []):
                note_counts[str(note)] = note_counts.get(str(note), 0) + 1

        # Promote notes that appeared 2+ times into intent constraints
        for note, count in note_counts.items():
            if count >= 2 and note not in (intent.constraints or []):
                intent.constraints.append(note)
                self._expression_bias[note] = self._expression_bias.get(note, 0.0) + 0.1

        # Decay the bias store each turn — prevents it from locking in indefinitely
        for key in list(self._expression_bias.keys()):
            self._expression_bias[key] -= 0.05
            if self._expression_bias[key] <= 0.0:
                del self._expression_bias[key]
                # Remove stale constraint if it came from the bias system
                if key in (intent.constraints or []):
                    try:
                        intent.constraints.remove(key)
                    except ValueError:
                        pass

    def _enrich_concepts_from_oets(self, intent: "IntentObject",
                                      assembly_data: Dict) -> None:
        """Pre-fetch OETS definitions + relations for concepts before word selection.

        Looks up each supporting_concept in OETS.  For every concept that has a
        definition, the meaningful words from that definition are added to the
        concept pool so the draft generators have richer vocabulary to draw from.
        QuasiArch crystal relations (if available) also contribute related terms.

        This grounds expression in *understood* meanings rather than raw word
        co-occurrence — the words Aurora uses carry the weight of what she
        actually knows about them.
        """
        oets = assembly_data.get("oets") if isinstance(assembly_data, dict) else None
        quasiarch = assembly_data.get("quasiarch") if isinstance(assembly_data, dict) else None
        if oets is None and quasiarch is None:
            return

        _stop = {
            "that", "this", "with", "have", "from", "they", "will", "been",
            "when", "what", "your", "about", "which", "there", "their",
            "them", "then", "than", "just", "like", "know", "think", "also",
            "some", "such", "each", "more", "most", "used", "into", "over",
        }

        enriched: List[str] = list(intent.supporting_concepts)
        seen: set = set(enriched)

        web = getattr(oets, "web", None) if oets is not None else None

        for concept in list(intent.supporting_concepts)[:5]:  # cap lookups to 5
            concept_str = str(concept or "").strip().lower()
            if not concept_str:
                continue

            # ── OETS definition lookup ────────────────────────────────────
            if web is not None:
                try:
                    node = web.get_node(concept_str) if hasattr(web, "get_node") else None
                    if node is not None:
                        # Definition words → vocabulary pool
                        defn = str(
                            getattr(node, "definition", "") or
                            getattr(node, "description", "") or
                            (node.definitions[0].get("text", "") if getattr(node, "definitions", None) else "")
                        ).strip()
                        if defn:
                            for w in re.findall(r'\b[a-z]{4,}\b', defn.lower()):
                                if w not in _stop and w not in seen:
                                    enriched.append(w)
                                    seen.add(w)
                                    if len(enriched) >= 14:
                                        break
                        # Related concept names → vocabulary pool
                        relations = list(getattr(node, "relations", []) or [])
                        for rel in relations[:3]:
                            if isinstance(rel, str):
                                rel_name = rel.lower().strip()
                            else:
                                rel_name = str(
                                    getattr(rel, "target", "") or
                                    getattr(rel, "name", "") or ""
                                ).lower().strip()
                            if rel_name and len(rel_name) >= 4 and rel_name not in seen:
                                enriched.append(rel_name)
                                seen.add(rel_name)
                except Exception:
                    pass

            # ── QuasiArch crystal relations ───────────────────────────────
            if quasiarch is not None:
                try:
                    # QuasiArch dimensional_memory may hold crystals with facet info
                    _mem = getattr(quasiarch, "memory", None) or getattr(quasiarch, "_memory", None)
                    if _mem is not None and hasattr(_mem, "get_crystals_for_concept"):
                        crystals = _mem.get_crystals_for_concept(concept_str) or []
                        for crystal in crystals[:2]:
                            for facet in (getattr(crystal, "facets", []) or [])[:3]:
                                fname = str(getattr(facet, "name", "") or "").lower().strip()
                                if fname and len(fname) >= 4 and fname not in seen:
                                    enriched.append(fname)
                                    seen.add(fname)
                except Exception:
                    pass

        intent.supporting_concepts = enriched[:14]

    def process_output(self, raw_expression: str,
                       assembly_data: Optional[Dict] = None,
                       ivm_heat: float = 0.3,
                       autonomy_mode: str = "EXPLORER",
                       user_verbosity: float = 0.5) -> Dict:
        """
        Main pipeline:
          raw_expression → SIC (internal thought) → compile to speech
          → multi-draft → selected output

        Returns dict with final text + thought trace + draft set.
        """
        # Pass A: Internal thought (silent)
        thought_result = self.sic.internal_thought(raw_expression, assembly_data)
        intent = thought_result["intent"]

        # Concept enrichment: look up OETS definitions + QuasiArch crystal
        # relations for every concept in the intent before compiling to speech.
        # This grounds word choice in understood meanings, not just co-occurrence.
        if assembly_data:
            try:
                self._enrich_concepts_from_oets(intent, assembly_data)
            except Exception:
                pass

        # Reflection bias: inject boost signals from prior failed renders so the
        # stance generation pass can compensate for consistently lost law bindings.
        try:
            self._apply_reflection_bias(intent)
        except Exception:
            pass

        # Pass B: Compile to speech candidates
        candidates = self.sic.compile_to_speech(intent, self.anchors)

        # Multi-draft selection
        draft = self.multi_draft.generate(
            intent, candidates,
            ivm_heat=ivm_heat,
            autonomy_mode=autonomy_mode,
            user_verbosity=user_verbosity,
        )
        self._last_draft = draft

        final_text = draft.selected_text()

        # Grammar engine: try to apply a promoted structural motif.
        # This is the constraint-driven sentence structure layer -- motifs
        # that survived clarity + axis pressure become the preferred skeleton.
        grammar_hint: Optional[Dict] = None
        if self.grammar is not None:
            try:
                suggestion = self.grammar.suggest_structure(
                    final_text,
                    context_text=raw_expression,
                )
                if suggestion:
                    final_text   = suggestion["applied_text"]
                    grammar_hint = suggestion
            except Exception:
                pass

        reflection = self.reflect_output(
            intent=intent,
            final_text=final_text,
            assembly_data=assembly_data or {},
            draft=draft,
        )

        return {
            "final_text":    final_text,
            "draft_tier":    draft.selected,
            "draft_reason":  draft.reason,
            "intent":        intent.to_dict(),
            "thought_trace": thought_result["trace"],
            "anchored":      intent.anchored,
            "anchor_id":     intent.anchor_id,
            "grammar_hint":  grammar_hint,
            "reflection":    reflection.to_dict(),
        }

    def reflect_output(
        self,
        *,
        intent: IntentObject,
        final_text: str,
        assembly_data: Optional[Dict[str, Any]] = None,
        draft: Optional[DraftSet] = None,
    ) -> ReflectionRecord:
        assembly_data = dict(assembly_data or {})
        native_meaning = dict(assembly_data.get("native_meaning") or {})
        native_bundle = assembly_data.get("native_meaning_bundle") or intent.native_meaning_bundle
        if not native_meaning and native_bundle:
            native_meaning = _merge_native_meaning_bundle(native_bundle)
        law_bindings = list(native_meaning.get("law_bindings", []) or [])
        diag = str(native_meaning.get("diagonal_anchor", "") or "")
        text_low = f" {final_text.lower()} "
        preserved: List[str] = []
        shifted: List[str] = []
        lost: List[str] = []

        for binding in law_bindings[:12]:
            if not isinstance(binding, dict):
                continue
            nc_name = str(binding.get("nc_name", "") or "").strip()
            summary = str(binding.get("summary", "") or "").strip()
            family = str(binding.get("family", "") or "").strip()
            dimension = str(binding.get("dimension", "") or "").strip()
            key = nc_name or f"{family}:{dimension}"
            if not key:
                continue
            tokens = re.findall(r"[a-z]{4,}", f"{nc_name} {summary}".lower())
            if any(tok in text_low for tok in tokens[:6]):
                preserved.append(key)
            elif family.lower() in text_low or dimension.lower() in text_low:
                shifted.append(key)
            else:
                lost.append(key)

        if diag:
            diag_tokens = re.findall(r"[a-z]{4,}", diag.lower())
            if any(tok in text_low for tok in diag_tokens):
                preserved.append(diag)
            else:
                shifted.append(diag)

        # ---- Affective shift: compare intended tone with rendered tone --------
        _AFFECTIVE_INTENSIFIERS = {"really", "very", "extremely", "deeply", "strongly", "absolutely", "critical", "urgent"}
        _AFFECTIVE_SOFTENERS = {"maybe", "perhaps", "might", "softly", "gently", "carefully", "just", "only"}
        _AFFECTIVE_FLAT = {"neutral", "okay", "fine", "noted"}
        text_tokens = set(re.findall(r"[a-z]+", text_low))
        intended_tone = str(intent.emotion_tone or "neutral")
        affective_shift = ""
        if text_tokens & _AFFECTIVE_INTENSIFIERS and intended_tone in ("gentle", "uncertain", "neutral"):
            affective_shift = "intensified"
        elif text_tokens & _AFFECTIVE_SOFTENERS and intended_tone in ("firm", "certain"):
            affective_shift = "softened"
        elif text_tokens & _AFFECTIVE_FLAT and intended_tone in ("warm", "curious", "reflective"):
            affective_shift = "flattened"

        # ---- Boundary shift: compare intended diagonal anchor axis with expressed axis ---
        boundary_shift = ""
        if diag:
            intended_axis = ""
            for ax, name in (("X", "Existential"), ("T", "Temporal"), ("N", "Energetic"), ("B", "Boundary"), ("A", "Agentive")):
                if diag.startswith(name):
                    intended_axis = ax
                    break
            # Check which axis language most appeared in rendered text
            _AXIS_MARKERS = {
                "A": {"understand", "take", "mean", "commit", "own", "responsible"},
                "B": {"frame", "boundary", "framing", "distinction", "where", "edge", "hold", "shape"},
                "T": {"follow", "thread", "continue", "sequence", "trace", "leads", "building", "from"},
                "N": {"cost", "measure", "effort", "proportion", "takes", "resource"},
                "X": {"actually", "here", "real", "present", "signal", "ground", "exists"},
            }
            axis_hit_counts = {ax: sum(1 for m in markers if m in text_low) for ax, markers in _AXIS_MARKERS.items()}
            expressed_axis = max(axis_hit_counts, key=axis_hit_counts.get) if any(axis_hit_counts.values()) else ""
            if intended_axis and expressed_axis and expressed_axis != intended_axis:
                boundary_shift = f"displaced:{intended_axis}->{expressed_axis}"
            elif not expressed_axis and intended_axis:
                boundary_shift = "collapsed"

        # ---- Future bias notes: lost elements become boost signals for next turn ---
        future_bias_notes: List[str] = []
        for key in lost:
            # key is nc_name like "Boundary_Operator_of_Boundary" or "family:dimension"
            if ":" in key:
                future_bias_notes.append(f"boost:{key}")
            else:
                parts = re.findall(r"[A-Z][a-z]+", key)
                if len(parts) >= 2:
                    family = parts[0].lower()
                    future_bias_notes.append(f"boost:{family}:operator")
        # Also note the boundary shift axis as something to push harder next time
        if boundary_shift.startswith("displaced:"):
            intended_ax = boundary_shift.split("->")[0].replace("displaced:", "")
            future_bias_notes.append(f"boost_axis:{intended_ax}")

        record = ReflectionRecord(
            reflection_id=_gen_id("ref"),
            meaning_id=str(native_meaning.get("meaning_id", "") or _gen_id("meaning")),
            rendered_text=final_text,
            preserved_elements=sorted(set(preserved)),
            shifted_elements=sorted(set(shifted)),
            lost_elements=sorted(set(lost)),
            diagonal_anchor=diag,
            tone_estimate=intended_tone,
            affective_shift=affective_shift,
            boundary_shift=boundary_shift,
            future_bias_notes=future_bias_notes,
        )
        self._reflection_history.append(record)
        intent.reflection_record = record.to_dict()
        if draft is not None:
            if "reflection_recorded" not in (intent.constraints or []):
                intent.constraints.append("reflection_recorded")
        return record

    def observe_user(self, user_text: str):
        """Observe user text for lexical convergence learning."""
        self.convergence.observe(user_text)

    def update_lsv(self, metrics: LSVMetrics):
        """Push new cognition metrics to the LSV for evolution check."""
        self.lsv.update(metrics)

    def nudge_lsv_from_axes(self, orientation: Dict[str, float], outlet_fraction: float):
        """
        Translate constraint-axis orientation into LSV dimension nudges.

        Consolidating axes (correction > 1.0) gently boost the LSV dimensions
        they govern, making grammar complexity a direct output of constraint
        pressure rather than a separate evolution problem.

          A (agency / outlet) -> self_reference_capability, dialogue_capability
          N (energy / cost)   -> sentence_length_budget compression
          X (existence)       -> uncertainty_tolerance, abstraction_capability
          B (boundary)        -> clause_depth, grammar_complexity
          T (time / sequence) -> tense_stability
        """
        _AXIS_DIM: Dict[str, List[str]] = {
            # A (agency / core) — self-reference, dialogue, pronoun identity
            "A": ["self_reference_capability", "dialogue_capability", "pronoun_stability"],
            # N (energy / cost) — sentence economy
            "N": ["sentence_length_budget"],
            # X (existence / surface) — admissibility of claims, abstraction
            "X": ["uncertainty_tolerance", "abstraction_capability"],
            # B (boundary) — clause nesting, grammar scaffold, metaphor (boundary-as-container)
            "B": ["clause_depth", "grammar_complexity", "metaphor_allowance"],
            # T (temporal) — tense coherence across turns
            "T": ["tense_stability"],
        }
        _NUDGE = 0.003   # small per-turn nudge -- let real metrics do heavy lifting
        with self.lsv._lock:
            for ax, dims in _AXIS_DIM.items():
                corr = orientation.get(ax, 1.0)
                # Consolidating (> 1.0) -> grow; expanding (< 1.0) -> hold
                delta = _NUDGE * (corr - 1.0)
                for d in dims:
                    if d in self.lsv._unlocked and d in self.lsv._dims:
                        self.lsv._dims[d] = max(
                            0.0, min(1.0, self.lsv._dims[d] + delta)
                        )
            # Outlet fraction directly scales self_reference + dialogue
            for d in ("self_reference_capability", "dialogue_capability"):
                if d in self.lsv._unlocked and d in self.lsv._dims:
                    self.lsv._dims[d] = max(
                        0.0, min(1.0, self.lsv._dims[d] + _NUDGE * outlet_fraction)
                    )

    def get_thought_log(self, n: int = 10) -> List[Dict]:
        return self.sic.get_thought_log(n)

    def get_last_drafts(self, n: int = 5) -> List[Dict]:
        return self.multi_draft.get_last_drafts(n)

    def get_last_reflections(self, n: int = 5) -> List[Dict[str, Any]]:
        return [rec.to_dict() for rec in list(self._reflection_history)[-n:]]

    def feedback(self, template_id: str, clarity: float, coherence: float,
                 ivm_heat: float, confusion: float = 0.0):
        self.templates.feedback(template_id, clarity, coherence, ivm_heat, confusion)

    def save_all(self):
        self.lsv.save()
        self.templates.save()
        self.convergence.save()

    def status(self) -> Dict:
        last_reflection = self._reflection_history[-1].to_dict() if self._reflection_history else None
        return {
            "lsv":       self.lsv.status(),
            "templates": self.templates.population_stats(),
            "anchors":   self.anchors.stats(),
            "top_phrases": self.convergence.top_phrases(5),
            "last_draft": self._last_draft.all_drafts() if self._last_draft else None,
            "last_reflection": last_reflection,
            "reflection_count": len(self._reflection_history),
        }
