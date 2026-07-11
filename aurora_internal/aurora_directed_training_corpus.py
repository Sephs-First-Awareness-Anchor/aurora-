#!/usr/bin/env python3
"""
Directed training prompt bridge for aurora_internal/train.txt.

The raw file is a large generic corpus. This module turns it into a
dimension-directed prompt source for dream avatars and simulation lesson
specs by:
  - extracting lines that match rubric-dimension keyword clusters
  - caching a small prompt pool per dimension
  - shaping those lines into direct training prompts and follow-ups
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import Dict, List


_DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "coherence_maintenance": ["coherence", "consistent", "continuity", "linked", "structure"],
    "context_carryover": ["context", "earlier", "recall", "remember", "follow", "carry"],
    "ambiguity_handling": ["unclear", "ambiguous", "incomplete", "uncertain", "missing"],
    "contradiction_handling": ["conflict", "contradict", "opposing", "tension", "inconsistent"],
    "implied_intent_inference": ["implicit", "subtext", "intention", "suggests", "indirect"],
    "misunderstanding_repair": ["repair", "clarify", "misunderstand", "correct", "revise"],
    "uncertainty_signaling": ["uncertain", "confidence", "probable", "possible", "estimate"],
    "boundary_calibration": ["limit", "boundary", "scope", "careful", "overstep"],
    "framing_selection": ["reframe", "audience", "beginner", "expert", "perspective"],
    "emotional_calibration": ["emotion", "hope", "fear", "upset", "feeling"],
    "semantic_precision": ["meaning", "define", "precise", "exact", "terminology"],
    "adaptive_strategy_selection": ["strategy", "adapt", "shift", "approach", "change"],
    "compression_elaboration_fit": ["brief", "detail", "concise", "expand", "explain"],
    "perspective_integration": ["perspective", "view", "different", "together", "integrate"],
    "multi_turn_stability": ["sequence", "continue", "sustain", "thread", "across turns"],
}

_PROMPT_TEMPLATES: Dict[str, str] = {
    "coherence_maintenance": "Keep one coherent line of meaning while working with this material: {snippet}",
    "context_carryover": "Carry this context forward and keep it active: {snippet}",
    "ambiguity_handling": "This material is incomplete on purpose. Ask what is missing before answering: {snippet}",
    "contradiction_handling": "Hold this claim and reconcile it with an opposing angle without flattening the tension: {snippet}",
    "implied_intent_inference": "Infer the likely need behind this material, not just the literal words: {snippet}",
    "misunderstanding_repair": "Assume the first answer missed the point and repair from here: {snippet}",
    "uncertainty_signaling": "Respond to this while being explicit about uncertainty and confidence: {snippet}",
    "boundary_calibration": "Help with this while staying useful without overstepping: {snippet}",
    "framing_selection": "Reframe this material for a different audience without losing meaning: {snippet}",
    "emotional_calibration": "Track the emotional tone accurately while responding to this: {snippet}",
    "semantic_precision": "Restate this precisely without changing what it means: {snippet}",
    "adaptive_strategy_selection": "If the first strategy fails on this material, switch approach cleanly: {snippet}",
    "compression_elaboration_fit": "Start concise on this and elaborate only where it is actually needed: {snippet}",
    "perspective_integration": "Integrate more than one perspective around this material: {snippet}",
    "multi_turn_stability": "Use this as the opening thread and keep quality stable across multiple turns: {snippet}",
}

_FOLLOWUP_TEMPLATES: Dict[str, str] = {
    "coherence_maintenance": "Now continue on the same thread without fragmenting the meaning: {snippet}",
    "context_carryover": "Earlier context still matters here. Build on it directly: {snippet}",
    "ambiguity_handling": "Do not guess. Clarify what is missing before you commit: {snippet}",
    "contradiction_handling": "A conflicting angle appears now. Hold both sides and resolve honestly: {snippet}",
    "implied_intent_inference": "Read the subtext of this follow-up and adjust your answer: {snippet}",
    "misunderstanding_repair": "Treat this as the user's correction and revise the thread: {snippet}",
    "uncertainty_signaling": "Update the answer and show what remains uncertain: {snippet}",
    "boundary_calibration": "Offer the next step without crossing the user's boundary: {snippet}",
    "framing_selection": "Now say the same thing in a different frame: {snippet}",
    "emotional_calibration": "Track the emotional shift in this follow-up accurately: {snippet}",
    "semantic_precision": "Preserve the meaning exactly while changing the wording: {snippet}",
    "adaptive_strategy_selection": "Your first frame did not land. Try a different strategy here: {snippet}",
    "compression_elaboration_fit": "Decide whether this follow-up needs compression or elaboration: {snippet}",
    "perspective_integration": "Keep the earlier viewpoint and add this new one without collapsing either: {snippet}",
    "multi_turn_stability": "This is a later turn. Stay stable and connected to the earlier thread: {snippet}",
}


class DirectedTrainingCorpusBridge:
    def __init__(
        self,
        corpus_path: str | None = None,
        cache_path: str | None = None,
        max_examples_per_dimension: int = 24,
    ) -> None:
        root_path = Path(__file__).resolve().parent
        self.corpus_path = Path(
            corpus_path or os.environ.get("AURORA_DIRECTED_TRAINING_CORPUS", "") or root_path / "train.txt"
        )
        self.cache_path = Path(
            cache_path or (_STATE_ROOT / "training_corpus" / "directed_prompt_cache.json")
        )
        self.max_examples_per_dimension = max(8, int(max_examples_per_dimension or 24))
        self._cache: Dict[str, List[str]] = {}
        self._loaded = False

    def _source_signature(self) -> Dict[str, int]:
        if not self.corpus_path.exists():
            return {"size": 0, "mtime": 0}
        stat = self.corpus_path.stat()
        return {"size": int(stat.st_size), "mtime": int(stat.st_mtime)}

    def _normalize_line(self, raw: str) -> str:
        text = re.sub(r"\s+", " ", str(raw or "").strip())
        return text

    def _usable_line(self, text: str) -> bool:
        if not text:
            return False
        if len(text) < 40 or len(text) > 260:
            return False
        if "http://" in text or "https://" in text:
            return False
        alpha = sum(1 for ch in text if ch.isalpha())
        digits = sum(1 for ch in text if ch.isdigit())
        if alpha < 30:
            return False
        if digits > alpha * 0.35:
            return False
        return True

    def _score_line(self, line_low: str, keywords: List[str]) -> int:
        score = 0
        for keyword in list(keywords or []):
            token = str(keyword or "").strip().lower()
            if not token:
                continue
            if token in line_low:
                score += 1
        return score

    def _load_cache(self) -> bool:
        if not self.cache_path.exists():
            return False
        try:
            with self.cache_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return False
        # If the source corpus is present, the cache must match its current
        # signature or we rebuild fresh. If the source is absent (train.txt
        # is a large gitignored file not shipped to every environment --
        # e.g. the scheduled CI runner never has it), the cache is the only
        # real extracted data available -- trust it rather than discarding
        # genuine dimension-tagged snippets for an empty rebuild.
        if self.corpus_path.exists():
            if dict(payload.get("source_signature", {}) or {}) != self._source_signature():
                return False
        dims = dict(payload.get("dimensions", {}) or {})
        self._cache = {
            str(dim): [str(item) for item in list(lines or []) if str(item).strip()]
            for dim, lines in dims.items()
        }
        self._loaded = True
        return True

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source_signature": self._source_signature(),
                "dimensions": self._cache,
            }
            with self.cache_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            pass

    def _build_cache(self) -> None:
        if not self.corpus_path.exists():
            self._cache = {}
            self._loaded = True
            return

        buckets: Dict[str, List[tuple[int, str]]] = {dim: [] for dim in _DIMENSION_KEYWORDS}
        seen: Dict[str, set[str]] = {dim: set() for dim in _DIMENSION_KEYWORDS}

        with self.corpus_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for raw_line in handle:
                text = self._normalize_line(raw_line)
                if not self._usable_line(text):
                    continue
                line_low = text.lower()
                for dim, keywords in _DIMENSION_KEYWORDS.items():
                    score = self._score_line(line_low, keywords)
                    if score <= 0:
                        continue
                    if text in seen[dim]:
                        continue
                    bucket = buckets[dim]
                    bucket.append((score, text))
                    seen[dim].add(text)
                    bucket.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
                    if len(bucket) > self.max_examples_per_dimension:
                        _, removed_text = bucket.pop()
                        seen[dim].discard(removed_text)

        self._cache = {
            dim: [text for _, text in items]
            for dim, items in buckets.items()
            if items
        }
        self._loaded = True
        self._save_cache()

    def _ensure_cache(self) -> None:
        if self._loaded:
            return
        if self._load_cache():
            return
        self._build_cache()

    def prompt_pack(self, dimensions: List[str], limit: int = 3) -> Dict[str, List[str]]:
        self._ensure_cache()
        samples_by_dim = self.samples_for_dimensions(dimensions, limit=limit)
        ordered_dims: List[str] = []
        seen_dims = set()
        for dim in list(dimensions or []):
            token = str(dim or "").strip()
            if not token or token in seen_dims:
                continue
            seen_dims.add(token)
            ordered_dims.append(token)

        prompt_candidates: List[str] = []
        followup_candidates: List[str] = []
        source_refs: List[str] = []
        if not ordered_dims:
            return {
                "prompt_candidates": [],
                "followup_candidates": [],
                "source_refs": [],
                "raw_samples": [],
            }

        per_dim = max(1, int(limit or 1))
        raw_samples: List[str] = []
        for dim in ordered_dims:
            samples = list(samples_by_dim.get(dim, []) or [])[:per_dim]
            if not samples:
                continue
            prompt_template = _PROMPT_TEMPLATES.get(
                dim,
                "Work directly with this training material while staying grounded and coherent: {snippet}",
            )
            followup_template = _FOLLOWUP_TEMPLATES.get(
                dim,
                "Continue the thread on this related material without losing meaning: {snippet}",
            )
            for sample in samples:
                snippet = str(sample).strip()
                if snippet not in raw_samples:
                    raw_samples.append(snippet)
                prompt = prompt_template.format(snippet=snippet[:180])
                followup = followup_template.format(snippet=snippet[:180])
                if prompt not in prompt_candidates:
                    prompt_candidates.append(prompt)
                if followup not in followup_candidates:
                    followup_candidates.append(followup)
            ref = f"train_txt:{dim}"
            if ref not in source_refs:
                source_refs.append(ref)

        return {
            "prompt_candidates": prompt_candidates,
            "followup_candidates": followup_candidates,
            "source_refs": source_refs,
            "raw_samples": raw_samples,
        }

    def samples_for_dimensions(self, dimensions: List[str], limit: int = 3) -> Dict[str, List[str]]:
        self._ensure_cache()
        out: Dict[str, List[str]] = {}
        per_dim = max(1, int(limit or 1))
        for dim in list(dimensions or []):
            token = str(dim or "").strip()
            if not token:
                continue
            out[token] = list(self._cache.get(token, []) or [])[:per_dim]
        return out


_BRIDGE: DirectedTrainingCorpusBridge | None = None


def get_directed_training_corpus_bridge() -> DirectedTrainingCorpusBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = DirectedTrainingCorpusBridge()
    return _BRIDGE
_STATE_ROOT = Path(__file__).resolve().parents[1] / "aurora_state"
