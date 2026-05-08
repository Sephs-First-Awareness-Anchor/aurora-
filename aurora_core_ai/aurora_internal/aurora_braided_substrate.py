#!/usr/bin/env python3
"""
AURORA BRAIDED SUBSTRATE LAYER (BSL)
=====================================

Lowest-scale continuity substrate for intent/context/style invariants.
BSL stores state transitions (crossings) and derives stable signatures and
compact bias vectors that can be used by memory and IVM layers.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


@dataclass
class Strand:
    name: str
    group: str
    base_weight: float = 1.0
    decay_rate: float = 0.002
    compatibility: Dict[str, float] = field(default_factory=dict)


@dataclass
class Crossing:
    a: int
    b: int
    polarity: int
    weight: float
    source: str
    ts: float = field(default_factory=time.time)
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubstrateEvent:
    intent_signal: Any
    context_signal: Any
    style_signal: Any
    confidence: float = 0.5
    evidence_level: float = 0.5
    contradiction_flag: bool = False
    autonomy_mode: str = "conservative"
    source: str = "interaction"


@dataclass
class BraidState:
    strands: List[Strand] = field(default_factory=list)
    crossings: Deque[Crossing] = field(default_factory=lambda: deque(maxlen=1000))
    reduced_crossings: List[Crossing] = field(default_factory=list)
    signature: str = ""
    intent_vec: List[float] = field(default_factory=list)
    context_vec: List[float] = field(default_factory=list)
    style_vec: List[float] = field(default_factory=list)
    heat: float = 0.0
    stability: float = 0.0
    last_update_ts: float = field(default_factory=time.time)


class BraidedSubstrateLayer:
    """BSL engine for event→crossing, reduction, signature, and vector output."""

    def __init__(self, max_crossings: int = 1000, reduction_period: int = 50):
        self.reduction_period = max(1, reduction_period)
        self.state = BraidState(strands=self._default_strands())
        self.state.crossings = deque(maxlen=max_crossings)
        self._event_count = 0
        self._name_to_index = {s.name: i for i, s in enumerate(self.state.strands)}
        self._group_indices: Dict[str, List[int]] = defaultdict(list)
        for i, strand in enumerate(self.state.strands):
            self._group_indices[strand.group].append(i)
        self._refresh_state()

    @staticmethod
    def _default_strands() -> List[Strand]:
        return [
            Strand("explore", "intent", 1.0),
            Strand("execute", "intent", 1.0),
            Strand("clarify", "intent", 0.9),
            Strand("safe", "context", 0.9),
            Strand("uncertain", "context", 0.9),
            Strand("task", "context", 0.8),
            Strand("literal", "style", 0.8),
            Strand("poetic", "style", 0.6),
            Strand("concise", "style", 0.8),
            Strand("trust_high", "trust", 0.7),
            Strand("caution_high", "trust", 0.8),
            Strand("truth_pressure", "doctrine", 0.9),
        ]

    def update(self, event: SubstrateEvent) -> BraidState:
        new_crossings = self._event_to_crossings(event)
        for crossing in new_crossings:
            self.state.crossings.append(crossing)

        if event.contradiction_flag:
            self.state.heat = _clamp(self.state.heat + 0.1 + 0.2 * event.confidence, 0.0, 1.0)
        else:
            self.state.heat = _clamp(self.state.heat * 0.99, 0.0, 1.0)

        self._event_count += 1
        if self._event_count % self.reduction_period == 0:
            self._reduce()

        self._refresh_state()
        self.state.last_update_ts = time.time()
        return self.state

    def snapshot(self) -> Dict[str, Any]:
        return {
            'signature': self.state.signature,
            'intent_vec': list(self.state.intent_vec),
            'context_vec': list(self.state.context_vec),
            'style_vec': list(self.state.style_vec),
            'heat': self.state.heat,
            'stability': self.state.stability,
            'dominant_crossings_summary': self.dominant_crossings_summary(),
        }

    def dominant_crossings_summary(self, limit: int = 8) -> List[Dict[str, Any]]:
        candidates = self.state.reduced_crossings or list(self.state.crossings)
        ranked = sorted(candidates, key=lambda c: c.weight, reverse=True)[:limit]
        return [
            {
                'a': self.state.strands[c.a].name,
                'b': self.state.strands[c.b].name,
                'polarity': c.polarity,
                'weight': round(c.weight, 4),
                'source': c.source,
            }
            for c in ranked
        ]

    def _event_to_crossings(self, event: SubstrateEvent) -> List[Crossing]:
        intent = self._resolve_signal(event.intent_signal, "intent", "execute")
        context = self._resolve_signal(event.context_signal, "context", "task")
        style = self._resolve_signal(event.style_signal, "style", "literal")

        base = _clamp(event.confidence) * (0.5 + _clamp(event.evidence_level))
        if event.contradiction_flag:
            base *= 1.4

        pairs = [
            (intent, context),
            (context, style),
            (intent, style),
        ]

        if event.contradiction_flag:
            doctrine = self._resolve_signal("truth_pressure", "doctrine", "truth_pressure")
            pairs.extend([(doctrine, intent), (doctrine, context)])

        if event.source in {"interaction", "system"}:
            trust = self._resolve_signal("trust_high", "trust", "trust_high")
            pairs.append((trust, context))

        polarity = -1 if event.contradiction_flag else 1
        out = []
        for a_name, b_name in pairs:
            a_idx = self._name_to_index[a_name]
            b_idx = self._name_to_index[b_name]
            if a_idx > b_idx:
                a_idx, b_idx = b_idx, a_idx
            strand_weight = self.state.strands[a_idx].base_weight * self.state.strands[b_idx].base_weight
            out.append(Crossing(
                a=a_idx,
                b=b_idx,
                polarity=polarity,
                weight=_clamp(base * strand_weight, 0.0, 5.0),
                source=event.source,
                tags={
                    'confidence': _clamp(event.confidence),
                    'evidence_level': _clamp(event.evidence_level),
                    'autonomy_mode': event.autonomy_mode,
                },
            ))
        return out

    def _resolve_signal(self, signal: Any, group: str, default_name: str) -> str:
        if isinstance(signal, str) and signal in self._name_to_index:
            if self.state.strands[self._name_to_index[signal]].group == group:
                return signal
        if isinstance(signal, dict):
            candidates = {k: v for k, v in signal.items() if k in self._name_to_index}
            if candidates:
                sorted_names = sorted(candidates.items(), key=lambda kv: kv[1], reverse=True)
                for name, _ in sorted_names:
                    if self.state.strands[self._name_to_index[name]].group == group:
                        return name
        return default_name

    def _reduce(self):
        reduced: List[Crossing] = []
        now = time.time()
        epsilon = 0.02

        for crossing in list(self.state.crossings):
            age = max(0.0, now - crossing.ts)
            decay_rate = (self.state.strands[crossing.a].decay_rate + self.state.strands[crossing.b].decay_rate) / 2.0
            decayed_weight = crossing.weight * (2.718281828 ** (-decay_rate * age))
            if decayed_weight < epsilon:
                continue
            current = Crossing(
                a=crossing.a,
                b=crossing.b,
                polarity=crossing.polarity,
                weight=decayed_weight,
                source=crossing.source,
                ts=crossing.ts,
                tags=dict(crossing.tags),
            )

            if reduced:
                prev = reduced[-1]
                if prev.a == current.a and prev.b == current.b:
                    if prev.polarity != current.polarity:
                        reduced.pop()  # inverse cancellation
                        continue
                    prev.weight += current.weight  # merge
                    continue
            reduced.append(current)

        self.state.reduced_crossings = reduced

    def _refresh_state(self):
        source = self.state.reduced_crossings or list(self.state.crossings)
        self.state.intent_vec = self._group_vector('intent', source)
        self.state.context_vec = self._group_vector('context', source)
        self.state.style_vec = self._group_vector('style', source)
        self.state.stability = self._compute_stability(source)
        self.state.signature = self._compute_signature(source)

    def _group_vector(self, group: str, crossings: List[Crossing], dims: int = 8) -> List[float]:
        indices = self._group_indices.get(group, [])
        if not indices:
            return [0.0] * dims
        weights = [0.0] * len(indices)
        index_map = {strand_idx: i for i, strand_idx in enumerate(indices)}
        for c in crossings:
            if c.a in index_map:
                weights[index_map[c.a]] += c.weight
            if c.b in index_map:
                weights[index_map[c.b]] += c.weight
        total = sum(weights) or 1.0
        normed = [w / total for w in weights]
        return (normed + [0.0] * dims)[:dims]

    def _compute_stability(self, crossings: List[Crossing]) -> float:
        if not crossings:
            return 1.0
        key_counts: Dict[Tuple[int, int, int], int] = defaultdict(int)
        for c in crossings:
            key_counts[(c.a, c.b, c.polarity)] += 1
        dominant = max(key_counts.values())
        recurrence = dominant / max(1, len(crossings))
        return _clamp(0.5 * recurrence + 0.5 * (1.0 - self.state.heat))

    def _compute_signature(self, crossings: List[Crossing]) -> str:
        packed = [
            (c.a, c.b, c.polarity, round(c.weight, 4), c.source)
            for c in crossings[:256]
        ]
        payload = {
            'crossings': packed,
            'heat_bucket': round(self.state.heat, 2),
            'stability_bucket': round(self.state.stability, 2),
        }
        raw = json.dumps(payload, sort_keys=True).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()[:24]
