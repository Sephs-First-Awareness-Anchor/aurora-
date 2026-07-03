#!/usr/bin/env python3
"""
AURORA CONVERSATION EPISODE COMPILER
========================================
Reads conversation JSON (same format as corpus_runner.py) and compiles
persistent dream episode packs.

Each pack contains 10 conversation threads organized by rubric pressure
profile — NOT by topic bins. The compiler runs AHEAD of dream execution
so the dream loop never reprocesses the full JSON.

Output: stored DreamEpisodePack objects ready for SimulationEngine consumption.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

from aurora_internal.aurora_conversation_rubric_engine import (
    ConversationRubricEngine,
    ConversationRubricScore,
    RUBRIC_DIMENSIONS,
)

# Engine anchors — the compiler derives signatures/regimes from the live
# constraint engine, never from a parallel abstraction.
from aurora_constraint_engine import (
    FoundationalContract as _EngineFoundationalContract,
    ExistenceMode as _ExistenceMode,
)
_FC = _EngineFoundationalContract()



# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ConversationPayload:
    """One conversation thread packaged for dream consumption."""
    conversation_id: str
    messages: List[Tuple[str, str]]
    rubric_score: Optional[ConversationRubricScore] = None
    message_count: int = 0

    def __post_init__(self):
        self.message_count = len(self.messages)


@dataclass
class DreamEpisodePack:
    """
    A compiled dream episode pack: 10 conversation threads selected
    for developmental diagnostic value.
    """
    episode_id: str
    conversation_ids: List[str]
    design_mode: str                           # "weakness_targeted", "balanced", "stress_test"
    rubric_profile: Dict[str, float] = field(default_factory=dict)
    contextual_modifiers: Dict[str, float] = field(default_factory=dict)
    difficulty_estimate: float = 0.5
    payloads: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    # Engine-derived fields — constraint signature + regime/projection at compile time
    constraint_signature: str = ""
    runtime_regime: Dict[str, Any] = field(default_factory=dict)
    language_projection: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "conversation_ids": self.conversation_ids,
            "design_mode": self.design_mode,
            "rubric_profile": dict(self.rubric_profile),
            "contextual_modifiers": dict(self.contextual_modifiers),
            "difficulty_estimate": self.difficulty_estimate,
            "payload_count": len(self.payloads),
            "timestamp": self.timestamp,
            "constraint_signature": self.constraint_signature,
            "runtime_regime": dict(self.runtime_regime),
            "language_projection": dict(self.language_projection),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DreamEpisodePack":
        return cls(
            episode_id=d["episode_id"],
            conversation_ids=d.get("conversation_ids", []),
            design_mode=d.get("design_mode", "balanced"),
            rubric_profile=d.get("rubric_profile", {}),
            contextual_modifiers=d.get("contextual_modifiers", {}),
            difficulty_estimate=d.get("difficulty_estimate", 0.5),
            payloads=d.get("payloads", []),
            timestamp=d.get("timestamp", 0.0),
            constraint_signature=d.get("constraint_signature", ""),
            runtime_regime=d.get("runtime_regime", {}),
            language_projection=d.get("language_projection", {}),
        )


# ============================================================================
# CONVERSATION JSON PARSING (reuses corpus_runner format)
# ============================================================================

def _extract_message_text(message_obj: Dict[str, Any]) -> str:
    """Extract text from a message object (OpenAI format)."""
    if not message_obj:
        return ""
    content = message_obj.get("content")
    if isinstance(content, dict):
        parts = content.get("parts", [])
        texts = [str(p) for p in parts if isinstance(p, str)]
        return " ".join(texts).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _extract_role(message_obj: Dict[str, Any]) -> str:
    if not message_obj:
        return "unknown"
    author = message_obj.get("author") or {}
    return author.get("role") or "unknown"


def _reconstruct_linear_thread(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Non-recursive reconstruction of main conversation chain from OpenAI DAG."""
    if not mapping or not isinstance(mapping, dict):
        return []

    roots = [nid for nid, node in mapping.items()
             if isinstance(node, dict) and node.get("parent") is None]
    if not roots:
        try:
            roots = [next(iter(mapping.keys()))]
        except StopIteration:
            return []

    def has_message(n: Dict[str, Any]) -> bool:
        msg = n.get("message")
        if not msg:
            return False
        role = _extract_role(msg)
        if role not in ("user", "assistant"):
            return False
        return bool(_extract_message_text(msg))

    score: Dict[str, int] = {}
    best_child: Dict[str, Optional[str]] = {}
    visited: set = set()
    visiting: set = set()

    def compute_from_root(root_id: str) -> int:
        stack = [(root_id, 0)]
        while stack:
            node_id, state = stack.pop()
            if state == 0:
                if node_id in visited or node_id in visiting:
                    continue
                visiting.add(node_id)
                stack.append((node_id, 1))
                node = mapping.get(node_id) or {}
                for c in (node.get("children") or []):
                    if c not in visited and c in mapping:
                        stack.append((c, 0))
            else:
                visiting.discard(node_id)
                node = mapping.get(node_id) or {}
                base = 1 if has_message(node) else 0
                best_s, best_c = 0, None
                for c in (node.get("children") or []):
                    if c in mapping:
                        cs = score.get(c, 0)
                        if cs > best_s:
                            best_s = cs
                            best_c = c
                score[node_id] = base + best_s
                best_child[node_id] = best_c
                visited.add(node_id)
        return score.get(root_id, 0)

    best_root = roots[0]
    best_root_score = -1
    for r in roots:
        rs = compute_from_root(r)
        if rs > best_root_score:
            best_root_score = rs
            best_root = r

    path_ids = []
    seen: set = set()
    cur: Optional[str] = best_root
    while cur is not None and cur not in seen:
        seen.add(cur)
        path_ids.append(cur)
        cur = best_child.get(cur)

    out = []
    for nid in path_ids:
        node = mapping.get(nid)
        if isinstance(node, dict):
            out.append(node)
    return out


def _extract_messages_from_conversation(conv_obj: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Extract (role, text) pairs from a conversation object."""
    mapping = conv_obj.get("mapping") or {}
    if not isinstance(mapping, dict):
        return []
    nodes = _reconstruct_linear_thread(mapping)
    extracted = []
    for node in nodes:
        msg = node.get("message")
        if not msg:
            continue
        role = _extract_role(msg)
        if role not in ("user", "assistant"):
            continue
        text = _extract_message_text(msg)
        if not text:
            continue
        extracted.append((role, text))
    return extracted


def _load_conversations(path: str) -> List[Dict[str, Any]]:
    """Load conversation JSON (same format as corpus_runner)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("conversations"), list):
            return [d for d in data["conversations"] if isinstance(d, dict)]
        if isinstance(data.get("data"), list):
            return [d for d in data["data"] if isinstance(d, dict)]
    return []


def _generate_id(prefix: str) -> str:
    raw = f"{prefix}_{time.time()}_{random.random()}"
    return f"{prefix}_{hashlib.md5(raw.encode()).hexdigest()[:12]}"


# ============================================================================
# EPISODE DESIGN STRATEGIES
# ============================================================================

def _select_weakness_targeted(
    scored: List[ConversationPayload],
    target_dimensions: List[str],
    count: int = 10,
) -> List[ConversationPayload]:
    """Select conversations that stress specific weak dimensions."""
    def weakness_relevance(payload: ConversationPayload) -> float:
        if not payload.rubric_score:
            return 0.0
        total = 0.0
        for dim in target_dimensions:
            # Lower score in target dimension = more relevant for weakness testing
            score = payload.rubric_score.dimension_scores.get(dim, 0.5)
            total += (1.0 - score)  # Invert: weakness becomes high relevance
        return total / max(len(target_dimensions), 1)

    ranked = sorted(scored, key=weakness_relevance, reverse=True)
    return ranked[:count]


def _select_balanced(
    scored: List[ConversationPayload],
    count: int = 10,
) -> List[ConversationPayload]:
    """Select a balanced mix across rubric dimensions."""
    if len(scored) <= count:
        return scored[:]

    # Pick conversations that have diverse rubric profiles
    selected = []
    remaining = scored[:]
    random.shuffle(remaining)

    # Seed with the conversation that has the most extreme scores
    if remaining:
        most_extreme = max(remaining, key=lambda p: (
            max(p.rubric_score.dimension_scores.values(), default=0) -
            min(p.rubric_score.dimension_scores.values(), default=0)
            if p.rubric_score else 0
        ))
        selected.append(most_extreme)
        remaining.remove(most_extreme)

    # Fill with maximally diverse entries
    while len(selected) < count and remaining:
        # Pick the conversation most different from what we already have
        def diversity_from_selected(payload: ConversationPayload) -> float:
            if not payload.rubric_score:
                return 0.0
            total_diff = 0.0
            for sel in selected:
                if not sel.rubric_score:
                    continue
                for dim in RUBRIC_DIMENSIONS:
                    a = payload.rubric_score.dimension_scores.get(dim, 0.5)
                    b = sel.rubric_score.dimension_scores.get(dim, 0.5)
                    total_diff += abs(a - b)
            return total_diff

        best = max(remaining, key=diversity_from_selected)
        selected.append(best)
        remaining.remove(best)

    return selected


def _select_stress_test(
    scored: List[ConversationPayload],
    count: int = 10,
) -> List[ConversationPayload]:
    """Select the most difficult conversations overall."""
    def difficulty(payload: ConversationPayload) -> float:
        if not payload.rubric_score:
            return 0.0
        scores = list(payload.rubric_score.dimension_scores.values())
        # Lower average = harder
        return 1.0 - (sum(scores) / max(len(scores), 1))

    ranked = sorted(scored, key=difficulty, reverse=True)
    return ranked[:count]


# ============================================================================
# MAIN COMPILER
# ============================================================================

class ConversationEpisodeCompiler:
    """
    Compiles conversation JSON into persistent dream episode packs.

    Runs ahead of dream execution. Each pack contains 10 conversations
    organized by rubric pressure profile.
    """

    PACK_SIZE = 10

    def __init__(self, storage_dir: str = os.path.join(_STATE_ROOT, "dream_episodes")):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.rubric_engine = ConversationRubricEngine()
        self._compiled_packs: List[DreamEpisodePack] = []
        self._all_scored: List[ConversationPayload] = []

    def compile_from_json(
        self,
        json_path: str,
        max_conversations: int = 500,
    ) -> List[DreamEpisodePack]:
        """
        Read conversation JSON, score through rubric, compile into episode packs.

        Returns list of compiled DreamEpisodePacks.
        """
        raw_convs = _load_conversations(json_path)
        if not raw_convs:
            return []

        # Parse and score
        scored_payloads: List[ConversationPayload] = []
        for i, conv in enumerate(raw_convs[:max_conversations]):
            conv_id = conv.get("id") or conv.get("title") or _generate_id("conv")
            messages = _extract_messages_from_conversation(conv)
            if len(messages) < 4:  # Skip very short conversations
                continue

            rubric_score = self.rubric_engine.score_conversation(conv_id, messages)
            payload = ConversationPayload(
                conversation_id=str(conv_id),
                messages=messages,
                rubric_score=rubric_score,
            )
            scored_payloads.append(payload)

        self._all_scored.extend(scored_payloads)

        if not scored_payloads:
            return []

        # Compile packs using different design strategies
        packs = []

        # Identify global weakness dimensions
        global_means = {dim: 0.0 for dim in RUBRIC_DIMENSIONS}
        for p in scored_payloads:
            if p.rubric_score:
                for dim in RUBRIC_DIMENSIONS:
                    global_means[dim] += p.rubric_score.dimension_scores.get(dim, 0.5)
        for dim in RUBRIC_DIMENSIONS:
            global_means[dim] /= max(len(scored_payloads), 1)

        # Sort dimensions by weakness (lowest mean score)
        weakness_order = sorted(global_means.items(), key=lambda kv: kv[1])
        top_weaknesses = [dim for dim, _ in weakness_order[:5]]

        # Pack 1: target top 3 weaknesses
        if len(scored_payloads) >= self.PACK_SIZE:
            selected = _select_weakness_targeted(
                scored_payloads, top_weaknesses[:3], self.PACK_SIZE
            )
            pack = self._build_pack(selected, "weakness_targeted", top_weaknesses[:3])
            packs.append(pack)

        # Pack 2: target next 2 weaknesses
        if len(scored_payloads) >= self.PACK_SIZE * 2:
            selected = _select_weakness_targeted(
                scored_payloads, top_weaknesses[3:5], self.PACK_SIZE
            )
            pack = self._build_pack(selected, "weakness_targeted", top_weaknesses[3:5])
            packs.append(pack)

        # Pack 3: balanced
        if len(scored_payloads) >= self.PACK_SIZE:
            selected = _select_balanced(scored_payloads, self.PACK_SIZE)
            pack = self._build_pack(selected, "balanced", [])
            packs.append(pack)

        # Pack 4: stress test
        if len(scored_payloads) >= self.PACK_SIZE:
            selected = _select_stress_test(scored_payloads, self.PACK_SIZE)
            pack = self._build_pack(selected, "stress_test", [])
            packs.append(pack)

        # Additional targeted packs for remaining conversations
        remaining = [p for p in scored_payloads
                     if p.conversation_id not in {
                         cid for pk in packs for cid in pk.conversation_ids
                     }]
        while len(remaining) >= self.PACK_SIZE:
            batch = remaining[:self.PACK_SIZE]
            remaining = remaining[self.PACK_SIZE:]
            pack = self._build_pack(batch, "balanced", [])
            packs.append(pack)

        # Persist
        self._compiled_packs.extend(packs)
        self._save_packs(packs)

        return packs

    def _build_pack(
        self,
        payloads: List[ConversationPayload],
        design_mode: str,
        target_dims: List[str],
    ) -> DreamEpisodePack:
        """Build a single episode pack from selected payloads."""
        # Compute aggregate rubric profile
        rubric_profile = {dim: 0.0 for dim in RUBRIC_DIMENSIONS}
        for p in payloads:
            if p.rubric_score:
                for dim in RUBRIC_DIMENSIONS:
                    rubric_profile[dim] += p.rubric_score.dimension_scores.get(dim, 0.5)
        for dim in RUBRIC_DIMENSIONS:
            rubric_profile[dim] /= max(len(payloads), 1)

        # Difficulty estimate: inverse of mean rubric score
        mean_score = sum(rubric_profile.values()) / max(len(rubric_profile), 1)
        difficulty = 1.0 - mean_score

        # Contextual modifiers
        modifiers: Dict[str, float] = {}
        if target_dims:
            modifiers["target_dimension_count"] = float(len(target_dims))
            for td in target_dims:
                modifiers[f"target_{td}"] = rubric_profile.get(td, 0.5)

        # Serialize payloads (messages + rubric, not raw JSON)
        serialized_payloads = []
        for p in payloads:
            entry: Dict[str, Any] = {
                "conversation_id": p.conversation_id,
                "messages": [{"role": r, "text": t} for r, t in p.messages],
                "message_count": p.message_count,
            }
            if p.rubric_score:
                entry["rubric"] = p.rubric_score.to_dict()
            serialized_payloads.append(entry)

        return DreamEpisodePack(
            episode_id=_generate_id("dreampk"),
            conversation_ids=[p.conversation_id for p in payloads],
            design_mode=design_mode,
            rubric_profile=rubric_profile,
            contextual_modifiers=modifiers,
            difficulty_estimate=difficulty,
            payloads=serialized_payloads,
        )

    def _save_packs(self, packs: List[DreamEpisodePack]):
        """Persist compiled packs to storage."""
        manifest_path = os.path.join(self.storage_dir, "pack_manifest.json")
        manifest: List[Dict[str, Any]] = []
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = []

        for pack in packs:
            pack_path = os.path.join(self.storage_dir, f"{pack.episode_id}.json")
            with open(pack_path, "w", encoding="utf-8") as f:
                json.dump(pack.to_dict(), f, indent=2)
            # Store payloads separately (they can be large)
            payload_path = os.path.join(self.storage_dir, f"{pack.episode_id}_payloads.json")
            with open(payload_path, "w", encoding="utf-8") as f:
                json.dump(pack.payloads, f)

            manifest.append({
                "episode_id": pack.episode_id,
                "design_mode": pack.design_mode,
                "difficulty_estimate": pack.difficulty_estimate,
                "conversation_count": len(pack.conversation_ids),
                "timestamp": pack.timestamp,
            })

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def load_pack(self, episode_id: str) -> Optional[DreamEpisodePack]:
        """Load a previously compiled pack from storage."""
        pack_path = os.path.join(self.storage_dir, f"{episode_id}.json")
        payload_path = os.path.join(self.storage_dir, f"{episode_id}_payloads.json")
        if not os.path.exists(pack_path):
            return None
        try:
            with open(pack_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pack = DreamEpisodePack.from_dict(data)
            if os.path.exists(payload_path):
                with open(payload_path, "r", encoding="utf-8") as f:
                    pack.payloads = json.load(f)
            return pack
        except Exception:
            return None

    def list_available_packs(self) -> List[Dict[str, Any]]:
        """List all compiled packs from the manifest."""
        manifest_path = os.path.join(self.storage_dir, "pack_manifest.json")
        if not os.path.exists(manifest_path):
            return []
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @property
    def compiled_pack_count(self) -> int:
        return len(self._compiled_packs)

    @property
    def scored_conversation_count(self) -> int:
        return len(self._all_scored)
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")


_DIM_TO_AXIS = {
    "emotional_calibration": "B",
    "boundary_calibration": "B",
    "ambiguity_handling": "B",
    "framing_selection": "A",
    "adaptive_strategy_selection": "A",
    "perspective_integration": "X",
    "uncertainty_signaling": "X",
    "contradiction_handling": "X",
    "context_carryover": "T",
    "multi_turn_stability": "T",
    "semantic_precision": "N",
    "compression_elaboration_fit": "N",
    "implied_intent_inference": "N",
    "coherence_maintenance": "X",
}

_AXES = ("X", "T", "N", "B", "A")


def _derive_signature(weights: dict, include_weighting: bool = True) -> str:
    ordered = [ax for ax in _AXES if float(weights.get(ax, 0.0) or 0.0) > 0.0]
    base = "".join(ordered) or "X"
    if include_weighting and ordered:
        dominant = max(ordered, key=lambda ax: float(weights.get(ax, 0.0) or 0.0))
        if len(ordered) == 5 and float(weights.get(dominant, 0.0) or 0.0) >= 0.30:
            return base + dominant
    return base
