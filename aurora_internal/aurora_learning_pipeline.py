#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Small, shared primitives for Aurora's live learning loop.

The runtime has several learning surfaces, but they need two pieces of common
bookkeeping:

* a cheap quality gate that distinguishes observation from useful learning;
* a bounded response/reaction delta record that can be inspected after a
  response has had a chance to meet a receiver.

This module deliberately does not decide whether a response is correct.  The
Understanding Contract and corpus truth comparison remain the authorities for
that.  It only prevents thin/repeated material from being promoted as new
knowledge and preserves the before/after evidence needed by those authorities.
"""

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import math
import hashlib
import json
import re
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional

from aurora_persistence_utils import atomic_write_json


_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can",
    "do", "for", "from", "had", "has", "have", "he", "her", "here",
    "how", "i", "if", "in", "is", "it", "its", "me", "my", "of",
    "on", "or", "our", "she", "that", "the", "their", "them", "there",
    "they", "this", "to", "was", "we", "were", "what", "when", "where",
    "which", "who", "will", "with", "you", "your",
})

_MISSING_CONTEXT_MARKERS = (
    "it", "this", "that", "they", "them", "those", "these", "as above",
    "what you said", "when you said", "the other thing", "again", "still",
)


def _tokens(text: Any) -> List[str]:
    return re.findall(r"[a-z0-9][a-z0-9'_-]*", str(text or "").lower())


def _content_tokens(text: Any) -> List[str]:
    return [token for token in _tokens(text) if token not in _STOPWORDS and len(token) > 2]


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    a = set(left)
    b = set(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def assess_text_quality(
    text: Any,
    previous_texts: Optional[Iterable[str]] = None,
    *,
    min_words: int = 3,
    min_content_words: int = 2,
) -> Dict[str, Any]:
    """Return bounded evidence about whether *text* is worth learning from.

    Short confirmations can be excellent receiver evidence, so this helper is
    intended for learning candidates/corpus material, not for outcome
    classification.  ``missing_context`` is intentionally an observation;
    callers may ask for clarification or route it to a gap ledger.
    """
    normalized = re.sub(r"\s+", " ", str(text or "").strip().lower())
    words = _tokens(normalized)
    content = _content_tokens(normalized)
    prior = [re.sub(r"\s+", " ", str(item or "").strip().lower())
             for item in list(previous_texts or []) if str(item or "").strip()]
    prior_content = [_content_tokens(item) for item in prior]
    similarities = [_jaccard(content, item) for item in prior_content]
    max_similarity = max(similarities, default=0.0)
    novelty = max(0.0, min(1.0, 1.0 - max_similarity))
    unique_ratio = len(set(content)) / float(max(1, len(content)))
    lexical_richness = max(0.0, min(
        1.0,
        0.55 * min(1.0, len(content) / 8.0)
        + 0.45 * unique_ratio,
    ))

    low = f" {normalized} "
    missing_context = [
        marker for marker in _MISSING_CONTEXT_MARKERS
        if re.search(rf"\b{re.escape(marker)}\b", low)
        or marker in normalized
    ]
    missing_context = list(dict.fromkeys(missing_context))
    exact_duplicate = bool(normalized and normalized in set(prior))
    thin = len(words) < int(min_words) or len(content) < int(min_content_words)
    stagnant = bool(exact_duplicate or (prior and novelty < 0.12))
    eligible = bool(normalized and not thin and not stagnant and novelty >= 0.12)

    return {
        "normalized": normalized,
        "word_count": len(words),
        "content_word_count": len(content),
        "unique_content_ratio": round(unique_ratio, 4),
        "lexical_richness": round(lexical_richness, 4),
        "novelty": round(novelty, 4),
        "max_similarity": round(max_similarity, 4),
        "thin": thin,
        "exact_duplicate": exact_duplicate,
        "stagnant": stagnant,
        "missing_context": missing_context,
        "eligible_for_learning": eligible,
        "reason": (
            "thin" if thin else
            "duplicate" if exact_duplicate else
            "stagnant" if stagnant else
            "usable"
        ),
    }


class LearningQualityGate:
    """Bounded rolling quality/absence observer for corpus material."""

    def __init__(self, history_size: int = 32) -> None:
        self._history: Deque[str] = deque(maxlen=max(4, int(history_size or 32)))
        self._observations: Deque[Dict[str, Any]] = deque(maxlen=300)

    def observe(self, text: Any, *, role: str = "") -> Dict[str, Any]:
        result = assess_text_quality(text, self._history)
        result["role"] = str(role or "")
        result["observed_at"] = time.time()
        if result.get("normalized"):
            self._history.append(str(result["normalized"]))
        self._observations.append(dict(result))
        return result

    def recent_observations(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._observations)[-max(1, int(limit or 1)):]

    def status(self) -> Dict[str, Any]:
        recent = list(self._observations)[-8:]
        return {
            "observed": len(self._observations),
            "history": len(self._history),
            "recent_learning_eligible": sum(
                1 for item in recent if item.get("eligible_for_learning")
            ),
            "recent_stagnant": sum(1 for item in recent if item.get("stagnant")),
            "recent_missing_context": sum(
                1 for item in recent if item.get("missing_context")
            ),
        }


def _text_delta(before: Any, after: Any) -> Dict[str, Any]:
    before_tokens = _content_tokens(before)
    after_tokens = _content_tokens(after)
    before_set = set(before_tokens)
    after_set = set(after_tokens)
    return {
        "before_length": len(_tokens(before)),
        "after_length": len(_tokens(after)),
        "length_change": len(_tokens(after)) - len(_tokens(before)),
        "added_terms": sorted(after_set - before_set)[:24],
        "removed_terms": sorted(before_set - after_set)[:24],
        "overlap": round(_jaccard(before_tokens, after_tokens), 4),
        "novelty": round(1.0 - _jaccard(before_tokens, after_tokens), 4),
    }


def build_learning_delta(
    *,
    response_before: str,
    response_after: str,
    reaction_before: str,
    reaction_after: str,
    response_id: str = "",
    outcome_kind: str = "indeterminate",
    observed_effect: str = "pending_verification",
    score: float = 0.0,
    turn_tick: int = 0,
    evidence_id: str = "",
) -> Dict[str, Any]:
    """Build one response/reaction delta—the unit consumed by learning."""
    return {
        "schema_version": 1,
        "response_id": str(response_id or ""),
        "evidence_id": str(evidence_id or response_id or ""),
        "turn_tick": int(turn_tick or 0),
        "response_before": str(response_before or "")[:320],
        "response_after": str(response_after or "")[:320],
        "reaction_before": str(reaction_before or "")[:320],
        "reaction_after": str(reaction_after or "")[:320],
        "response_delta": _text_delta(response_before, response_after),
        "reaction_delta": _text_delta(reaction_before, reaction_after),
        "outcome_kind": str(outcome_kind or "indeterminate"),
        "observed_effect": str(observed_effect or "pending_verification"),
        "score": max(0.0, min(1.0, float(score or 0.0))),
        "timestamp": time.time(),
    }


class LearningDeltaLedger:
    """Bounded, atomic persistence for response/reaction deltas."""

    def __init__(self, storage_path: str = "aurora_state/learning_deltas.json") -> None:
        self.storage_path = str(storage_path)
        self.records: List[Dict[str, Any]] = []
        self.replayed_ids: List[str] = []
        self._load()

    def _load(self) -> None:
        path = Path(self.storage_path)
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.records = []
            for raw_item in list(payload.get("records", []) or [])[-200:]:
                if not isinstance(raw_item, dict):
                    continue
                item = dict(raw_item)
                item["delta_id"] = self._delta_id(item)
                self.records.append(item)
            self.replayed_ids = [
                str(item or "") for item in list(payload.get("replayed_ids", []) or [])
                if str(item or "").strip()
            ][-200:]
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_learning_pipeline.py:236",
                exc=_aurora_boundary_exc,
                context={"function": "_load", "handler_line": 236, "source_file": "aurora_internal/aurora_learning_pipeline.py"},
            )
            self.records = []
            self.replayed_ids = []

    @staticmethod
    def _delta_id(item: Dict[str, Any]) -> str:
        """Return a stable identity for one persisted delta."""
        existing = str(item.get("delta_id", "") or "").strip()
        if existing:
            return existing
        material = {
            key: item.get(key)
            for key in (
                "response_id", "evidence_id", "turn_tick", "response_before",
                "response_after", "reaction_before", "reaction_after",
            )
        }
        return hashlib.sha256(
            json.dumps(material, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:24]

    def record(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(delta or {})
        item["delta_id"] = self._delta_id(item)
        response_id = str(item.get("response_id", "") or "")
        if response_id:
            self.records = [
                prior for prior in self.records
                if str(prior.get("response_id", "") or "") != response_id
            ]
            self.replayed_ids = [
                prior_id for prior_id in self.replayed_ids
                if prior_id != str(item["delta_id"])
            ]
        self.records.append(item)
        self.records = self.records[-200:]
        self.save()
        return item

    def unreplayed(self, limit: int = 24) -> List[Dict[str, Any]]:
        """Return persisted deltas that have not reached a training consumer."""
        replayed = set(self.replayed_ids)
        pending: List[Dict[str, Any]] = []
        for item in self.records:
            delta_id = self._delta_id(item)
            if delta_id in replayed:
                continue
            normalized = dict(item)
            normalized["delta_id"] = delta_id
            pending.append(normalized)
        return pending[-max(1, int(limit or 1)):]

    def mark_replayed(self, delta_ids: Iterable[str]) -> bool:
        """Mark deltas consumed by a downstream learning/decision bridge."""
        known = {self._delta_id(item) for item in self.records}
        current = list(self.replayed_ids)
        for raw_id in list(delta_ids or []):
            delta_id = str(raw_id or "").strip()
            if delta_id and delta_id in known and delta_id not in current:
                current.append(delta_id)
        self.replayed_ids = current[-200:]
        return self.save()

    def replay_status(self) -> Dict[str, int]:
        replayed = set(self.replayed_ids)
        return {
            "records": len(self.records),
            "replayed": sum(1 for item in self.records if self._delta_id(item) in replayed),
            "pending": sum(1 for item in self.records if self._delta_id(item) not in replayed),
        }

    def save(self) -> bool:
        return bool(atomic_write_json(
            Path(self.storage_path),
            {
                "schema_version": 2,
                "records": list(self.records),
                "replayed_ids": list(self.replayed_ids[-200:]),
            },
            indent=2,
            default=str,
        ))
