"""
Spreading-activation field over Aurora's OETS concept space.

The subsurface maintains this continuously — every tick it:
  1. Seeds from current context: conversation concepts, sensory intake
     (visual recognitions, heard audio), conscious frame hypotheses
  2. Spreads activation through OETS relationship edges (associative, not lookup)
  3. Decays existing activations so older context fades naturally

The surface reads top activated concepts each turn and injects them into
law_bindings in chain_down4_meaning, grounding manifold word selection in
what Aurora currently has in mind.

This is not retrieval. It is priming — the same spreading-activation
mechanism the human brain uses to make related knowledge available
before it is explicitly needed.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_SPREAD_DECAY   = 0.45   # activation fraction passed per hop × edge strength
_TICK_DECAY     = 0.88   # per-tick exponential decay
_MIN_STRENGTH   = 0.04   # prune below this
_MAX_HOPS       = 2      # maximum spread depth
_MAX_CONCEPTS   = 200    # cap on tracked concepts
_SEED_STRENGTH  = 1.0    # seeds start at full activation

# Words that carry no semantic content and should not be seeds or spread targets
_STOP_WORDS = {
    "the", "and", "that", "this", "with", "from", "have", "your", "about",
    "there", "which", "would", "could", "should", "what", "when", "where",
    "who", "how", "why", "was", "were", "are", "been", "being", "will",
    "just", "also", "very", "much", "more", "some", "any", "all", "not",
    "you", "me", "we", "it", "he", "she", "they", "do", "did", "does",
    "can", "may", "its", "then", "than", "but", "for", "into", "onto",
    "over", "under", "only", "really", "still", "like", "because", "while",
    "after", "before", "through", "across", "between", "people", "person",
    "here", "now", "ok", "okay", "yeah", "yes", "no", "so", "well",
    "aurora", "hey",
    # sensory prefix words — carry no semantic content for OETS spreading
    "heard", "saw", "cross", "modal",
}


@dataclass
class ActivationField:
    """
    A weighted map of currently primed concepts and their metadata.
    Subsurface writes each tick. Surface reads per turn.
    """
    activations: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)
    tick_count: int = 0

    # ------------------------------------------------------------------ #
    #  Core operations
    # ------------------------------------------------------------------ #

    def decay(self) -> None:
        """Apply per-tick decay. Call once per subsurface tick."""
        self.activations = {
            k: v * _TICK_DECAY
            for k, v in self.activations.items()
            if v * _TICK_DECAY >= _MIN_STRENGTH
        }

    def spread(
        self,
        seeds: List[str],
        oets_web: Any,
        *,
        working_memory: Any = None,
        core_identity: Any = None,
        sensory_recognitions: Optional[List[str]] = None,
        boost: float = 1.0,
    ) -> None:
        """
        Spread activation from seed concepts through OETS.

        seeds               -- concept words from current context
        oets_web            -- OntologicalWeb instance (has get_node, get_all_relations_for)
        working_memory      -- for stated-fact enrichment
        core_identity       -- for entity enrichment
        sensory_recognitions-- visual/audio recognitions; seeded alongside text concepts
        boost               -- multiplier on seed strength (1.0 normal, <1 for weak signal)
        """
        # Combine text seeds with sensory intake
        all_seeds: List[str] = []
        for s in (seeds or []):
            clean = str(s or "").strip().lower()
            if clean and clean not in _STOP_WORDS and len(clean) >= 3:
                all_seeds.append(clean)
        for r in (sensory_recognitions or []):
            clean = str(r or "").strip().lower()
            if clean and clean not in _STOP_WORDS and len(clean) >= 3:
                all_seeds.append(clean)

        if not all_seeds:
            return

        seed_strength = _SEED_STRENGTH * boost
        # Map: concept → activation_to_add this spread pass
        new_wave: Dict[str, float] = {}
        for seed in all_seeds:
            existing = new_wave.get(seed, 0.0)
            new_wave[seed] = min(1.0, existing + seed_strength)

        # BFS spreading through OETS
        if oets_web is not None:
            frontier: List[Tuple[str, float]] = [
                (c, s) for c, s in new_wave.items()
            ]
            for _hop in range(_MAX_HOPS):
                next_frontier: List[Tuple[str, float]] = []
                for concept, strength in frontier:
                    try:
                        relations = oets_web.get_all_relations_for(concept)
                    except Exception:
                        relations = []
                    for rel in relations:
                        try:
                            neighbor = (
                                rel.target_word
                                if rel.source_word == concept
                                else rel.source_word
                            )
                            neighbor = str(neighbor or "").strip().lower()
                            if not neighbor or neighbor in _STOP_WORDS:
                                continue
                            edge_strength = float(getattr(rel, "strength", 0.5) or 0.5)
                            neighbor_gain = strength * _SPREAD_DECAY * edge_strength
                            if neighbor_gain < _MIN_STRENGTH:
                                continue
                            existing = new_wave.get(neighbor, 0.0)
                            if neighbor_gain > existing:
                                new_wave[neighbor] = neighbor_gain
                                next_frontier.append((neighbor, neighbor_gain))
                        except Exception:
                            continue
                frontier = next_frontier
                if not frontier:
                    break

        # Merge into live activations (additive, capped at 1.0)
        for concept, gain in new_wave.items():
            existing = self.activations.get(concept, 0.0)
            self.activations[concept] = min(1.0, existing + gain * 0.6)

        # Collect metadata for activated concepts
        for concept in new_wave:
            if concept in self.metadata:
                continue  # already have it
            entry: Dict[str, Any] = {}
            if oets_web is not None:
                try:
                    node = oets_web.get_node(concept)
                    if node is not None:
                        defns = getattr(node, "definitions", []) or []
                        if defns:
                            entry["definition"] = str(
                                defns[0].get("text", "") or ""
                            )
                        entry["noncomp_id"] = str(
                            getattr(node, "noncomp_id", "") or ""
                        )
                        entry["depth"] = float(
                            getattr(node, "ontological_depth", 0.0) or 0.0
                        )
                        entry["valence"] = float(
                            getattr(node, "emotional_valence", 0.0) or 0.0
                        )
                except Exception:
                    pass

            # Working memory stated facts
            if working_memory is not None and hasattr(working_memory, "get_stated_fact"):
                try:
                    fact = working_memory.get_stated_fact("user", concept)
                    if fact:
                        entry["wm_fact"] = str(fact)
                except Exception:
                    pass

            # Core identity entity lookup
            if core_identity is not None:
                try:
                    entity = None
                    if hasattr(core_identity, "get_entity"):
                        entity = core_identity.get_entity(concept)
                    elif hasattr(core_identity, "entities"):
                        entity = (core_identity.entities or {}).get(concept)
                    if entity is not None:
                        entry["entity_name"] = str(
                            getattr(entity, "name", concept) or concept
                        )
                        entry["entity_role"] = str(
                            getattr(entity, "role", "") or ""
                        )
                except Exception:
                    pass

            if entry:
                self.metadata[concept] = entry

        # Prune to MAX_CONCEPTS by activation strength
        if len(self.activations) > _MAX_CONCEPTS:
            top = sorted(
                self.activations.items(), key=lambda x: x[1], reverse=True
            )[:_MAX_CONCEPTS]
            self.activations = dict(top)
            # Also prune metadata to only tracked concepts
            tracked = set(self.activations)
            self.metadata = {k: v for k, v in self.metadata.items() if k in tracked}

        self.last_updated = time.time()
        self.tick_count += 1

    # ------------------------------------------------------------------ #
    #  Surface read interface
    # ------------------------------------------------------------------ #

    def top_activated(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Return the top N currently primed concepts with their metadata.
        Used by the surface layer to inject grounded content into law_bindings.
        """
        top = sorted(
            self.activations.items(), key=lambda x: x[1], reverse=True
        )[:n]
        result = []
        for concept, strength in top:
            meta = self.metadata.get(concept, {})
            entry = {
                "concept": concept,
                "strength": round(strength, 4),
                "definition": meta.get("definition", ""),
                "noncomp_id": meta.get("noncomp_id", ""),
                "wm_fact": meta.get("wm_fact", ""),
                "entity_name": meta.get("entity_name", ""),
                "entity_role": meta.get("entity_role", ""),
                "depth": meta.get("depth", 0.0),
                "valence": meta.get("valence", 0.0),
            }
            result.append(entry)
        return result

    def law_bindings_from_top(self, n: int = 6) -> List[Dict[str, Any]]:
        """
        Convert top activated concepts into law_binding-compatible dicts
        for direct injection into native_meaning["law_bindings"].
        Only yields concepts that have definition or fact content — bare
        concept names without semantic grounding are skipped.
        """
        bindings = []
        for entry in self.top_activated(n * 2):  # oversample, filter
            concept = entry["concept"]
            strength = entry["strength"]
            defn = entry.get("definition", "")
            fact = entry.get("wm_fact", "")
            entity_name = entry.get("entity_name", "")
            noncomp = entry.get("noncomp_id", "")

            summary = defn or fact or (
                f"{entity_name} ({entry.get('entity_role', '')})"
                if entity_name else ""
            )
            if not summary:
                continue  # no grounded content — skip bare labels

            binding = {
                "nc_name": concept,
                "summary": summary,
                "score": round(strength, 4),
                "source": "activation_field",
            }
            if noncomp:
                parts = noncomp.split(":")
                if len(parts) == 2:
                    binding["family"] = parts[0].lower()
                    binding["dimension"] = parts[1].lower()
            if fact:
                binding["stated_fact"] = fact
            if entity_name:
                binding["entity_name"] = entity_name

            bindings.append(binding)
            if len(bindings) >= n:
                break

        return bindings

    # ------------------------------------------------------------------ #
    #  Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activations": dict(self.activations),
            "metadata": dict(self.metadata),
            "last_updated": self.last_updated,
            "tick_count": self.tick_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivationField":
        obj = cls()
        obj.activations = dict(data.get("activations") or {})
        obj.metadata = dict(data.get("metadata") or {})
        obj.last_updated = float(data.get("last_updated") or 0.0)
        obj.tick_count = int(data.get("tick_count") or 0)
        return obj


# ------------------------------------------------------------------ #
#  Seed extraction helpers
# ------------------------------------------------------------------ #

def extract_seeds_from_systems(systems: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Pull concept seeds from all available context sources.
    Called by the subsurface each tick.

    Returns:
        (seeds, sensory_recognitions) -- two separate token lists; pass both
        to ActivationField.spread() as `seeds` and `sensory_recognitions`.
    """
    seeds: List[str] = []

    # 1. Recent user utterances — what was just said
    wm = systems.get("working_memory")
    if wm is not None:
        try:
            recent = list(getattr(wm, "recent_user_utterances", None) or [])
            for utt in recent[:3]:
                text = str(utt.get("text", "") if isinstance(utt, dict) else utt or "")
                seeds.extend(_tokenize(text))
        except Exception:
            pass

    # 2. Conscious frame — salient hypotheses and interpretation
    frame = systems.get("_live_conscious_frame") or {}
    if not frame:
        import json, os
        try:
            snap_path = os.path.join(
                str(systems.get("_state_dir", "aurora_state")),
                "dual_strata_snapshot.json",
            )
            if os.path.exists(snap_path):
                snap = json.loads(open(snap_path).read())
                frame = snap.get("conscious_frame") or {}
        except Exception:
            pass

    for hyp in list(frame.get("salient_hypotheses") or [])[:4]:
        seeds.extend(_tokenize(str(hyp.get("summary", "") if isinstance(hyp, dict) else hyp or "")))
    seeds.extend(_tokenize(str(frame.get("interpretation") or "")))

    # 3. Sensory recognitions — visual and audio (what Aurora is perceiving)
    sensory_crystal = systems.get("sensory_crystal")
    sensory_recognitions: List[str] = []
    if sensory_crystal is not None:
        try:
            state = sensory_crystal.get_state()
            recent_recs = (state.get("recognitions") or {}).get("recent") or []
            for rec in recent_recs[:6]:
                if isinstance(rec, str):
                    # "heard sunni", "saw motion detected", "cross-modal speech_tone"
                    sensory_recognitions.extend(_tokenize(rec))
                else:
                    word = str(rec.get("label", "") or rec.get("word", "") or "").strip().lower()
                    if word and word not in _STOP_WORDS and len(word) >= 3:
                        sensory_recognitions.append(word)
        except Exception:
            pass

    # 4. Active topic from working memory
    if wm is not None:
        try:
            topic = str(
                getattr(wm, "active_topic", None)
                or (wm.get_active_topic() if hasattr(wm, "get_active_topic") else "")
                or ""
            )
            seeds.extend(_tokenize(topic))
        except Exception:
            pass

    return seeds, sensory_recognitions


def _tokenize(text: str) -> List[str]:
    """Extract meaningful content words from a text string."""
    words = re.findall(r"[a-z]{3,}", str(text or "").lower())
    return [w for w in words if w not in _STOP_WORDS]


# ------------------------------------------------------------------ #
#  Per-tick orchestration
# ------------------------------------------------------------------ #

_BASE_DIR = Path(__file__).parent.parent.parent  # aurora repo root
_STATE_DIR_DEFAULT = _BASE_DIR / "aurora_state"
_FIELD_FILENAME = "activation_field.json"


def _resolve_state_dir(systems: Dict[str, Any]) -> Path:
    """Mirror the state_dir resolution used by aurora.py's read-side tiers."""
    return Path(str(systems.get("state_dir") or _STATE_DIR_DEFAULT))


def _load_field(state_dir: Path) -> ActivationField:
    path = state_dir / _FIELD_FILENAME
    try:
        if path.exists():
            return ActivationField.from_dict(json.loads(path.read_text()) or {})
    except Exception:
        pass
    return ActivationField()


def _save_field(afield: ActivationField, state_dir: Path) -> None:
    path = state_dir / _FIELD_FILENAME
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(afield.to_dict(), f, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        pass


def run_activation_cycle(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Subsurface per-tick activation cycle: seed -> spread -> decay -> persist.

    Loads the persisted ActivationField (cross-process via
    aurora_state/activation_field.json), extracts seeds from systems
    (working memory, conscious frame, sensory recognitions), spreads through
    OETS, decays existing activations, then writes the result to both
    systems["_activation_field"] (Tier 1, in-process) and
    activation_field.json (Tier 2, cross-process) -- the two tiers
    _chain_down4_meaning and the subsurface-evidence block already check
    before falling through to the dual_strata_snapshot.json metadata tier.

    Best-effort: any failure returns {} and leaves systems untouched.
    """
    try:
        state_dir = _resolve_state_dir(systems)
        afield = _load_field(state_dir)

        seeds, sensory_recognitions = extract_seeds_from_systems(systems)
        oets_web = systems.get("oets") or systems.get("ontological_web")
        wm = systems.get("working_memory")
        identity = systems.get("identity") or systems.get("core_identity")

        afield.spread(
            seeds, oets_web,
            working_memory=wm,
            core_identity=identity,
            sensory_recognitions=sensory_recognitions,
        )
        afield.decay()

        data = afield.to_dict()
        _save_field(afield, state_dir)
        systems["_activation_field"] = data
        return data
    except Exception:
        return {}
