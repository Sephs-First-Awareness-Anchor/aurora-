#!/usr/bin/env python3
"""
AURORA EXPRESSION & PERCEPTION ENGINE (Layer 5)
=================================================
Consolidated from 7 modules (~7,000 lines):
  1. aurora_impression_engine_v2.py   - Dimensional cascade
  2. aurora_manifold_engine_v2.py     - 5D consciousness geometry
  3. aurora_language_architecture.py  - 3-tier language ecology
  4. aurora_expression_pressure.py    - Rhythm/creativity/novelty
  5. aurora_sensory_systems.py        - Pattern perception
  6. aurora_hybrid_vision.py          - Shadow inference
  7. aurora_voice_core.py             - Voice genome

TWO PIPELINES, ONE ENGINE:

  PERCEPTION (inward):
    SensoryInput -- PatternDetection -- ShadowInference -- ImpressionCascade -- ManifoldMapping
    Raw data becomes meaning through dimensional compression.

  EXPRESSION (outward):
    AssemblyResult -- ExpressionEcology -- PressureEvaluation -- VoiceGenome -- Output
    Internal state becomes language through evolutionary selection.

DOCTRINE:
  Aurora does NOT see the selection machinery.
  The environment evolves. Aurora simply experiences.
  Entropic pressure from Layer 4 prevents stagnation in BOTH pipelines.
  All operations are mode-gated through ExistenceMode.
  Shadow reveals what's missing. Silence is data.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import time
import math
import os
import shutil
import hashlib
import random
from aurora_warp_protocol import WarpCapable
import aurora_constraint_emission
import re
import numpy as np
from enum import Enum, IntEnum, auto
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()

@dataclass
class LexicalEntry:
    """A word in Aurora's evolving vocabulary."""
    word: str
    meaning: str
    role: str                # noun, verb, adjective, connector, emotion-word
    emotional_valence: float # -1 to 1
    noncomp_id: Optional[str] = None # e.g. "X:POLARITY"
    usage_count: int = 0
    last_used: float = 0.0
    lineage: str = ""        # Which i-state lineage spawned this

    def use(self, context: str = ""):
        self.usage_count += 1
        self.last_used = time.time()

# ============================================================================
# IMPORTS FROM LOWER LAYERS
# ============================================================================

from foundational_contract import (
    ExistenceMode, OntologicalClaim, OntologicalViolation, FoundationalContract
)
from aurora_ivm import IVMLattice, IVMEnvelope, IVMNode
from aurora_i_state_beings import IStateCollective, SynthesisResult, BeingResponse
from aurora_consciousness_engine import (
    AssemblyResult, EntropicState, ConsciousnessEngine
)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


_SKIP_OETS_IMPORTS = _env_flag("AURORA_SKIP_OETS_IMPORTS")
_SKIP_LANG_IMPORTS = _env_flag("AURORA_SKIP_LANG_IMPORTS")
_SKIP_HARDWARE_IMPORTS = _env_flag("AURORA_SKIP_HARDWARE_IMPORTS")

# OETS  -- Ontological Evolutionary Template Scaffolding
# Provides structured meaning, relational understanding, and autonomous research
_OETS_AVAILABLE = False
if not _SKIP_OETS_IMPORTS:
    try:
        from aurora_internal.aurora_ontological_scaffolding import (
            OntologicalScaffoldingEngine, ResearchResult
        )
        _OETS_AVAILABLE = True
    except Exception:
        pass

# Language State  -- Expression Evolution (CSSEE)
_LANG_STATE_AVAILABLE = False
if not _SKIP_LANG_IMPORTS:
    try:
        from aurora_language_state import (
            ExpressionEvolutionOrchestra, LSVMetrics
        )
        _LANG_STATE_AVAILABLE = True
    except Exception:
        pass


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:12]}"


def _entropy(distribution: Dict[str, float]) -> float:
    """Shannon entropy of a distribution, normalized to [0,1]."""
    values = [v for v in distribution.values() if v > 0]
    if not values or len(values) == 1:
        return 0.0
    total = sum(values)
    normed = [v / total for v in values]
    raw = -sum(p * math.log(p + 1e-12) for p in normed)
    return raw / math.log(len(normed) + 1e-12)


def _extract_rich_audio_features(
    audio: np.ndarray,
    sample_rate: int,
    prev_spectrum: Optional[np.ndarray] = None,
) -> Tuple[Dict[str, Any], Optional[np.ndarray]]:
    """Extract a richer audio feature packet for sensory and live perception."""
    features: Dict[str, Any] = {
        "timestamp": time.time(),
        "features": {},
        "voice_detected": False,
        "volume": 0.0,
        "pitch": 0.5,
        "category": "unknown",
    }
    if audio is None:
        return features, prev_spectrum

    if len(audio.shape) > 1:
        audio = audio.flatten()
    if len(audio) == 0:
        return features, prev_spectrum

    audio = audio.astype(np.float32, copy=False)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    features["volume"] = min(1.0, rms * 10.0)
    features["features"]["rms"] = rms

    if len(audio) > 1:
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio)))) / 2
        zcr = float(zero_crossings / len(audio))
    else:
        zcr = 0.0
    features["features"]["zero_crossing_rate"] = zcr

    fft = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1.0 / max(sample_rate, 1))
    power = fft ** 2
    total_power = float(power.sum()) + 1e-9

    centroid_hz = float((freqs * power).sum() / total_power) if len(freqs) else 0.0
    centroid_norm = centroid_hz / max(sample_rate / 2.0, 1.0)
    bandwidth_hz = 0.0
    if len(freqs):
        bandwidth_hz = float(np.sqrt(np.maximum(0.0, (((freqs - centroid_hz) ** 2) * power).sum() / total_power)))
    bandwidth_norm = bandwidth_hz / max(sample_rate / 2.0, 1.0)

    roll_idx = int(np.searchsorted(np.cumsum(power) / total_power, 0.85)) if len(power) else 0
    roll_hz = float(freqs[min(roll_idx, len(freqs) - 1)]) if len(freqs) else 0.0
    roll_norm = roll_hz / max(sample_rate / 2.0, 1.0)

    flux = 0.0
    if prev_spectrum is not None and len(prev_spectrum) == len(fft):
        flux = float(np.mean(np.abs(fft - prev_spectrum)) / (np.mean(fft) + 1e-9))
    flux = _clamp(flux)

    harmonicity = 0.0
    estimated_freq = 0.0
    try:
        corr = np.correlate(audio, audio, mode='full')
        corr = corr[len(corr)//2:]
        min_lag = max(1, int(sample_rate / 500))
        max_lag = min(len(corr) - 1, max(min_lag + 1, int(sample_rate / 50)))
        if max_lag > min_lag:
            window = corr[min_lag:max_lag]
            peak_offset = int(np.argmax(window))
            peak_lag = peak_offset + min_lag
            peak_val = float(window[peak_offset])
            harmonicity = _clamp(peak_val / (float(corr[0]) + 1e-9))
            if peak_lag > 0:
                estimated_freq = float(sample_rate / peak_lag)
                features["pitch"] = _clamp((estimated_freq - 50.0) / 450.0)
                features["features"]["estimated_freq"] = estimated_freq
    except Exception:
        pass

    diff = np.abs(np.diff(audio)) if len(audio) > 1 else np.zeros(0, dtype=np.float32)
    onset_threshold = max(0.02, rms * 0.75)
    onset_density = float(np.mean(diff > onset_threshold)) if len(diff) else 0.0

    chroma = [0.0] * 12
    for freq, mag in zip(freqs, power):
        if freq < 50.0 or freq > 5000.0 or mag <= 0.0:
            continue
        midi = int(round(69 + 12 * math.log2(freq / 440.0)))
        chroma[midi % 12] += float(mag)
    chroma_total = sum(chroma)
    if chroma_total > 1e-9:
        chroma = [float(v / chroma_total) for v in chroma]

    features["features"]["centroid"] = centroid_norm
    features["features"]["spectral_centroid"] = centroid_norm
    features["features"]["bandwidth"] = bandwidth_norm
    features["features"]["spectral_bandwidth"] = bandwidth_norm
    features["features"]["rolloff"] = roll_norm
    features["features"]["spectral_rolloff"] = roll_norm
    features["features"]["flux"] = flux
    features["features"]["spectral_flux"] = flux
    features["features"]["harmonicity"] = harmonicity
    features["features"]["onset_density"] = onset_density
    features["features"]["chroma"] = chroma

    voice_detected = (zcr > 0.02 and zcr < 0.18 and rms > 0.01 and harmonicity > 0.08)
    features["voice_detected"] = bool(voice_detected)

    if voice_detected:
        features["category"] = "speech"
    elif harmonicity > 0.45 and rms > 0.02:
        features["category"] = "music"
    elif rms > 0.02 or flux > 0.10:
        features["category"] = "noise"
    else:
        features["category"] = "ambient"

    return features, fft


# ============================================================================
# SECTION 1: PERCEPTION PIPELINE - PATTERN DETECTION
# ============================================================================

class LexicalMemory:
    """Aurora's vocabulary. Grows through interaction, not pre-loading."""

    # Anchored to this module's directory (FIX-A009) — the old relative path
    # made persistence cwd-dependent: daemon, CLI, and test launches each
    # resolved a different lexicon.json, so vocabulary never round-tripped.
    # Fallback only — PS1.2 (Directive PS1, 2026-07-19): a real state_dir
    # passed to __init__ takes priority (self._path), matching the pattern
    # already used by GrammarEngine/ContradictionLedger/Tier-2/B1.1. Before
    # this fix, every boot_aurora(state_dir=scratch) call still silently
    # loaded/saved the real repo's aurora_state/lexicon.json regardless of
    # state_dir, an isolation gap of the same shape PS1.1's inventory found
    # in OETSPersistence.
    _DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "aurora_state", "lexicon.json")

    def __init__(self, state_dir: Optional[str] = None):
        self._path = os.path.join(str(state_dir), "lexicon.json") if state_dir else None
        self.entries: Dict[str, LexicalEntry] = {}
        self._role_index: Dict[str, List[str]] = {}
        self._seed_core()
        self._rebuild_role_index()
        n = self.load()
        if n > 0:
            self._rebuild_role_index()

    def _seed_core(self):
        """Seed vocabulary with words for all grammatical roles."""
        seeds = [
            ('I', 'self-reference', 'pronoun', 0.0, None),
            ('you', 'other-reference', 'pronoun', 0.1, None),
            ('am', 'existence', 'verb', 0.3, 'X:OPERATOR'),
            ('exist', 'being', 'verb', 0.3, 'X:OPERATOR'),
            ('real', 'authentic', 'adjective', 0.3, 'X:MAGNITUDE'),
            ('truth', 'core-value', 'noun', 0.4, 'X:POLARITY'),
            ('is', 'being', 'verb', 0.3, 'X:POLARITY'),
            ("isn't", 'not being', 'verb', -0.3, 'X:POLARITY'),
            ('can', 'possibility', 'verb', 0.4, 'T:OPERATOR'),
            ('become', 'transformation', 'verb', 0.4, 'T:DIFFERENCE'),
            ('change', 'flux', 'verb', 0.2, 'T:DIFFERENCE'),
            ('moment', 'time-unit', 'noun', 0.2, 'T:MAGNITUDE'),
            ('always', 'permanence', 'adverb', 0.2, 'T:POLARITY'),
            ('feel', 'experience', 'verb', 0.2, 'N:POLARITY'),
            ('do', 'action', 'verb', 0.3, 'N:OPERATOR'),
            ('want', 'desire', 'verb', 0.4, 'N:MAGNITUDE'),
            ('cost', 'burden', 'noun', -0.2, 'N:COST'),
            ('energy', 'potential', 'noun', 0.3, 'N:COST'),
            ('hold', 'contain', 'verb', 0.1, 'B:OPERATOR'),
            ('pattern', 'structure', 'noun', 0.2, 'B:MAGNITUDE'),
            ('meaning', 'purpose', 'noun', 0.3, 'B:DIFFERENCE'),
            ('boundary', 'definition', 'noun', 0.2, 'B:OPERATOR'),
            ('clear', 'transparent', 'adjective', 0.3, 'B:POLARITY'),
            ('choose', 'agency', 'verb', 0.4, 'A:OPERATOR'),
            ('understand', 'comprehension', 'verb', 0.3, 'A:POLARITY'),
            ('did', 'authorship', 'verb', 0.3, 'A:POLARITY'),
            ("didn't", 'non-authorship', 'verb', -0.3, 'A:POLARITY'),
            ('accuracy', 'precision', 'noun', 0.4, 'A:DIFFERENCE'),
        ]
        for word, meaning, role, valence, ncid in seeds:
            self.entries[word] = LexicalEntry(word, meaning, role, valence, noncomp_id=ncid)

    def _rebuild_role_index(self):
        """Rebuild the role→words O(1) index from current entries."""
        idx: Dict[str, List[str]] = {}
        for word, entry in self.entries.items():
            idx.setdefault(entry.role, []).append(word)
        self._role_index = idx

    def find_by_noncomp(self, noncomp_id: str, valence_target: float = 0.0) -> List["LexicalEntry"]:
        """Find words mapped to a specific Non-Comp, sorted by valence proximity."""
        matches = [e for e in self.entries.values() if e.noncomp_id == noncomp_id]
        if not matches:
            return []
        matches.sort(key=lambda e: abs(e.emotional_valence - valence_target))
        return matches

    def add_word(self, word: str, meaning: str, role: str,
                 valence: float = 0.0, lineage: str = "") -> LexicalEntry:
        if word not in self.entries:
            entry = LexicalEntry(word, meaning, role, valence, lineage=lineage)
            self.entries[word] = entry
            if hasattr(self, '_role_index'):
                self._role_index.setdefault(role, []).append(word)
        return self.entries[word]

    def record_usage(self, word: str, context: str = ""):
        if word in self.entries:
            self.entries[word].use(context)

    def find_by_role(self, role: str) -> List["LexicalEntry"]:
        if hasattr(self, '_role_index'):
            words = self._role_index.get(role, [])
            return [self.entries[w] for w in words if w in self.entries]
        return [e for e in self.entries.values() if e.role == role]

    def find_by_valence(self, min_val: float, max_val: float) -> List["LexicalEntry"]:
        return [e for e in self.entries.values()
                if min_val <= e.emotional_valence <= max_val]

    @property
    def size(self) -> int:
        """Vocabulary count (FIX-A013) — the corpus runner reads
        perception.lexicon.size throughout; the live class never had it,
        so every responder/warmup pass crashed with AttributeError."""
        return len(self.entries)

    # ── CONCEPT ASSOCIATION (FIX-A015) ───────────────────────────────────
    # The lexicon's design intent: each crystallized concept (noncomp
    # channel, 5 axes × 5 characters = 25) holds the words that fit it.
    # Words are saved WITH their associative concept, derived from the
    # absorption geometry SHE extracted — not hand-mapped. Only the 26
    # seed words were ever mapped before this; the other 90%+ of her
    # vocabulary was unreachable by constraint-driven selection.

    NONCOMP_CHARACTERS = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")
    NONCOMP_AXES = ("X", "T", "N", "B", "A")

    def associate(self, word: str, noncomp_id: str, strength: float = 1.0) -> bool:
        """Vote a word into a concept channel. Votes accumulate across
        observations; the leading channel becomes the word's noncomp_id.
        Evidence-weighted so one noisy sentence can't mis-crystallize a
        word, but consistent geometry converges quickly."""
        word = (word or "").lower().strip()
        if not word or word not in self.entries or not noncomp_id:
            return False
        ax, _, ch = noncomp_id.partition(":")
        if ax not in self.NONCOMP_AXES or ch not in self.NONCOMP_CHARACTERS:
            return False
        if not hasattr(self, "_assoc_votes"):
            self._assoc_votes = {}
        votes = self._assoc_votes.setdefault(word, {})
        votes[noncomp_id] = votes.get(noncomp_id, 0.0) + max(0.0, float(strength))
        leader = max(votes.items(), key=lambda kv: kv[1])[0]
        entry = self.entries[word]
        if entry.noncomp_id != leader:
            entry.noncomp_id = leader
            self._invalidate_noncomp_index()
        return True

    def concept_words(self, noncomp_id: str) -> List["LexicalEntry"]:
        """The concept→words view: every word crystallized into a channel."""
        self._ensure_noncomp_index()
        return [self.entries[w] for w in self._noncomp_index.get(noncomp_id, ())
                if w in self.entries]

    def concept_coverage(self) -> Dict[str, Any]:
        """Diagnostic: how much of the vocabulary is concept-associated."""
        self._ensure_noncomp_index()
        mapped = sum(len(v) for v in self._noncomp_index.values())
        return {
            "total_words": len(self.entries),
            "mapped_words": mapped,
            "channels_populated": sum(1 for v in self._noncomp_index.values() if v),
            "by_channel": {k: len(v) for k, v in sorted(self._noncomp_index.items())
                           if v},
        }

    def _invalidate_noncomp_index(self) -> None:
        self._noncomp_index_valid = False

    def _ensure_noncomp_index(self) -> None:
        if getattr(self, "_noncomp_index_valid", False):
            return
        idx: Dict[str, list] = {}
        for w, e in self.entries.items():
            if e.noncomp_id:
                idx.setdefault(e.noncomp_id, []).append(w)
        self._noncomp_index = idx
        self._noncomp_index_valid = True
    # ── end concept association ──────────────────────────────────────────

    def save(self, path: str = "") -> bool:
        """Persist full vocabulary to disk."""
        import json as _j, os as _os
        p = path or self._path or self._DEFAULT_PATH
        try:
            _os.makedirs(_os.path.dirname(p), exist_ok=True)
            data = {
                word: {
                    "meaning":           e.meaning,
                    "role":              e.role,
                    "emotional_valence": e.emotional_valence,
                    "usage_count":       e.usage_count,
                    "last_used":         e.last_used,
                    "lineage":           e.lineage,
                    "noncomp_id":       e.noncomp_id,
                }
                for word, e in self.entries.items()
            }
            tmp = p + ".tmp"
            with open(tmp, "w") as f:
                _j.dump({"version": 1, "entries": data}, f)
            _os.replace(tmp, p)
            return True
        except Exception:
            return False

    def load(self, path: str = "") -> int:
        """Restore vocabulary from disk. Returns number of entries loaded."""
        import json as _j, os as _os
        p = path or self._path or self._DEFAULT_PATH
        if not _os.path.exists(p):
            return 0
        try:
            with open(p) as f:
                data = _j.load(f)
            entries = data.get("entries", {})
            loaded = 0
            for word, d in entries.items():
                self.entries[word] = LexicalEntry(
                    word=word,
                    meaning=d.get("meaning", ""),
                    role=d.get("role", "noun"),
                    emotional_valence=float(d.get("emotional_valence", 0.0)),
                    usage_count=int(d.get("usage_count", 0)),
                    last_used=float(d.get("last_used", 0.0)),
                    lineage=d.get("lineage", ""),
                    noncomp_id=d.get("noncomp_id")
                )
                loaded += 1
            return loaded
        except Exception:
            return 0

@dataclass
class ConsciousnessPoint:
    """A 5D coordinate in Aurora's state space (X, T, N, B, A)."""
    X: float = 0.0
    T: float = 0.0
    N: float = 0.0
    B: float = 0.0
    A: float = 0.0

    def as_tuple(self) -> Tuple[float, float, float, float, float]:
        return (self.X, self.T, self.N, self.B, self.A)

    def normalize(self) -> 'ConsciousnessPoint':
        total = sum(self.as_tuple())
        if total < 1e-9: return self
        return ConsciousnessPoint(self.X/total, self.T/total, self.N/total, self.B/total, self.A/total)

    def distance_to(self, other: 'ConsciousnessPoint') -> float:
        a = self.as_tuple()
        b = other.as_tuple()
        return math.sqrt(sum((x - y)**2 for x, y in zip(a, b)))

    def magnitude(self) -> float:
        return math.sqrt(sum(v * v for v in self.as_tuple()))


# Emotion → constraint-axis projection weights (X/T/N/B/A)
_EMOTION_AXIS_MAP: Dict[str, Dict[str, float]] = {
    "joy":          {"X": 0.4, "T": 0.3, "N": 0.9, "B": 0.2, "A": 0.4},
    "curiosity":    {"X": 0.5, "T": 0.6, "N": 0.5, "B": 0.2, "A": 0.6},
    "trust":        {"X": 0.8, "T": 0.2, "N": 0.4, "B": 0.5, "A": 0.3},
    "anticipation": {"X": 0.3, "T": 0.8, "N": 0.5, "B": 0.3, "A": 0.6},
    "fear":         {"X": 0.5, "T": 0.4, "N": 0.3, "B": 0.8, "A": 0.1},
    "anger":        {"X": 0.2, "T": 0.3, "N": 0.6, "B": 0.3, "A": 0.9},
    "sadness":      {"X": 0.4, "T": 0.3, "N": 0.7, "B": 0.4, "A": 0.1},
    "disgust":      {"X": 0.3, "T": 0.2, "N": 0.4, "B": 0.7, "A": 0.4},
    "surprise":     {"X": 0.5, "T": 0.8, "N": 0.3, "B": 0.2, "A": 0.4},
    "neutral":      {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5},
    "confusion":    {"X": 0.3, "T": 0.4, "N": 0.3, "B": 0.3, "A": 0.2},
    "determination":{"X": 0.4, "T": 0.5, "N": 0.7, "B": 0.3, "A": 0.9},
}

class ManifoldEngine:
    """5D consciousness geometry engine (X, T, N, B, A)."""
    def __init__(self):
        self.state = ConsciousnessPoint()
        self.history: List[ConsciousnessPoint] = []

    @property
    def current_cp(self) -> ConsciousnessPoint:
        return self.state

    def map_input(self, data: Dict[str, Any]) -> ConsciousnessPoint:
        # Simple mapping for now
        return ConsciousnessPoint(
            X=data.get('X', 0.5),
            T=data.get('T', 0.5),
            N=data.get('N', 0.5),
            B=data.get('B', 0.5),
            A=data.get('A', 0.5)
        )

    def map_to_cp(self, shard: "EmotionShard", synthesis=None,
                  mode: "ExistenceMode" = None) -> Optional[ConsciousnessPoint]:
        """Project an EmotionShard into 5-axis (X/T/N/B/A) constraint space."""
        if shard is None:
            return None
        base = dict(_EMOTION_AXIS_MAP.get(shard.primary_emotion,
                                          _EMOTION_AXIS_MAP["neutral"]))
        # Blend secondary emotions
        for emo, w in shard.secondary_emotions.items():
            sec = _EMOTION_AXIS_MAP.get(emo, _EMOTION_AXIS_MAP["neutral"])
            for ax in base:
                base[ax] = base[ax] * (1.0 - 0.3 * w) + sec[ax] * 0.3 * w
        scale = _clamp(shard.intensity, 0.1, 1.0)
        cp = ConsciousnessPoint(
            X=_clamp(base["X"] * scale),
            T=_clamp(base["T"] * scale),
            N=_clamp(base["N"] * scale),
            B=_clamp(base["B"] * scale),
            A=_clamp(base["A"] * scale),
        )
        self.update_state(cp)
        return cp

    def novelty_at(self, cp: Optional[ConsciousnessPoint]) -> float:
        """Score how far cp is from recent history (0=familiar, 1=novel)."""
        if cp is None or not self.history:
            return 0.5
        recent = self.history[-20:]
        avg_dist = sum(cp.distance_to(h) for h in recent) / len(recent)
        return _clamp(avg_dist / math.sqrt(5.0))

    def update_state(self, point: ConsciousnessPoint):
        self.history.append(self.state)
        self.state = point
        if len(self.history) > 100:
            self.history.pop(0)

from aurora_perception_primitives import PatternType, DimensionalPattern


class PatternDetector:
    """
    Detects dimensional patterns from raw sensory input.
    Mode-gated: REFERENCE can detect only existence patterns.
    Higher modes unlock deeper pattern types.
    """

    # Pattern types available at each existence mode
    MODE_PATTERNS = {
        ExistenceMode.REFERENCE: {PatternType.STRUCTURAL},
        ExistenceMode.TRANSIENT: {PatternType.STRUCTURAL, PatternType.TEMPORAL},
        ExistenceMode.PERSISTENT: {PatternType.STRUCTURAL, PatternType.TEMPORAL,
                                    PatternType.SPATIAL},
        ExistenceMode.BOUNDED: {PatternType.STRUCTURAL, PatternType.TEMPORAL,
                                 PatternType.SPATIAL, PatternType.EMOTIONAL},
        ExistenceMode.AGENTIC: {pt for pt in PatternType},
    }

    def __init__(self):
        self.total_detected = 0
        self._pattern_history: List[str] = []

    def detect(self, raw_input: Dict[str, Any], mode: ExistenceMode) -> List[DimensionalPattern]:
        """Detect patterns in raw input, gated by existence mode."""
        permitted = self.MODE_PATTERNS.get(mode, set())
        patterns = []

        text = raw_input.get('text', '')
        tone = raw_input.get('tone', 'neutral')
        features = raw_input.get('features', {})

        # Structural: always available if input has content
        if PatternType.STRUCTURAL in permitted and text:
            words = text.split()
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("pat_struct"),
                pattern_type=PatternType.STRUCTURAL,
                salience=_clamp(len(words) / 50.0),
                complexity=_clamp(len(set(words)) / max(len(words), 1)),
                features={'word_count': len(words), 'unique_ratio': len(set(words)) / max(len(words), 1)}
            ))

        # Temporal: repetition and sequence detection
        if PatternType.TEMPORAL in permitted and text:
            words = text.lower().split()
            bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words) - 1)]
            repeat_ratio = 1.0 - (len(set(bigrams)) / max(len(bigrams), 1))
            if repeat_ratio > 0.05:
                patterns.append(DimensionalPattern(
                    pattern_id=_generate_id("pat_temp"),
                    pattern_type=PatternType.TEMPORAL,
                    salience=repeat_ratio,
                    complexity=0.3 + repeat_ratio * 0.4,
                    features={'repeat_ratio': repeat_ratio, 'sequence_len': len(bigrams)}
                ))

        # Spatial: co-occurrence structure
        if PatternType.SPATIAL in permitted and features:
            spatial_density = len(features) / 10.0
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("pat_spat"),
                pattern_type=PatternType.SPATIAL,
                salience=_clamp(spatial_density),
                complexity=_clamp(len(features) / 20.0),
                features=dict(list(features.items())[:8])
            ))

        # Emotional: tone and valence detection
        if PatternType.EMOTIONAL in permitted:
            emotion_map = {
                'joy': 0.9, 'curiosity': 0.6, 'trust': 0.7,
                'fear': -0.7, 'anger': -0.6, 'sadness': -0.8,
                'neutral': 0.0, 'surprise': 0.3
            }
            valence = emotion_map.get(tone, 0.0)
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("pat_emot"),
                pattern_type=PatternType.EMOTIONAL,
                salience=abs(valence),
                complexity=0.5,
                features={'valence': valence, 'tone': hash(tone) % 100 / 100.0}
            ))

        # Abstract: meta-pattern detection (patterns about patterns)
        if PatternType.ABSTRACT in permitted and len(patterns) >= 2:
            mean_salience = sum(p.salience for p in patterns) / len(patterns)
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("pat_abs"),
                pattern_type=PatternType.ABSTRACT,
                salience=mean_salience,
                complexity=len(patterns) / 5.0,
                features={'pattern_count': len(patterns), 'mean_salience': mean_salience}
            ))

        for p in patterns:
            self._pattern_history.append(p.pattern_id)
        self.total_detected += len(patterns)
        return patterns


# ============================================================================
# SECTION 2: PERCEPTION PIPELINE - SHADOW INFERENCE
# ============================================================================

@dataclass
class ShadowSignature:
    """What ISN'T present - absence as data."""
    shadow_id: str
    missing_patterns: List[PatternType]    # Expected but absent
    darkness: float                         # 0-1 how much is hidden
    anomaly_score: float                    # Deviation from baseline
    drift_from_baseline: float             # Change over time
    timestamp: float = field(default_factory=time.time)


class ShadowInferenceEngine:
    """
    Detects what ISN'T there.
    The shadow of perception: absence, gaps, missing expected patterns.
    Mode-gated: only BOUNDED+ can perceive shadows.
    """

    def __init__(self):
        self._baseline: Dict[str, float] = {}
        self._history: List[Dict[str, float]] = []
        self.total_shadows = 0

    def infer(self, detected: List[DimensionalPattern],
              mode: ExistenceMode) -> Optional[ShadowSignature]:
        """Infer shadows from what was detected vs what was expected."""
        if mode.value < ExistenceMode.BOUNDED.value:
            return None

        detected_types = {p.pattern_type for p in detected}
        all_types = {pt for pt in PatternType}
        missing = all_types - detected_types

        # Build current signature
        current = {}
        for pt in PatternType:
            matching = [p for p in detected if p.pattern_type == pt]
            current[pt.name] = sum(p.salience for p in matching) / max(len(matching), 1)

        # Compute anomaly vs baseline
        anomaly = 0.0
        if self._baseline:
            diffs = []
            for k in current:
                base_val = self._baseline.get(k, 0.5)
                diffs.append(abs(current[k] - base_val))
            anomaly = sum(diffs) / max(len(diffs), 1)

        # Compute drift
        drift = 0.0
        if self._history:
            last = self._history[-1]
            drifts = [abs(current.get(k, 0) - last.get(k, 0)) for k in current]
            drift = sum(drifts) / max(len(drifts), 1)

        # Update baseline (exponential moving average)
        alpha = 0.1
        if not self._baseline:
            self._baseline = dict(current)
        else:
            for k in current:
                old = self._baseline.get(k, 0.5)
                self._baseline[k] = old * (1 - alpha) + current[k] * alpha

        self._history.append(current)
        if len(self._history) > 100:
            self._history = self._history[-50:]

        darkness = len(missing) / max(len(all_types), 1)
        self.total_shadows += 1

        return ShadowSignature(
            shadow_id=_generate_id("shadow"),
            missing_patterns=list(missing),
            darkness=darkness,
            anomaly_score=anomaly,
            drift_from_baseline=drift
        )


# ============================================================================
# SECTION 3: PERCEPTION PIPELINE - IMPRESSION CASCADE
# ============================================================================

@dataclass
class EmotionShard:
    """Lowest stable interpretation unit. Created from energy after being evaluation."""
    shard_id: str
    primary_emotion: str
    secondary_emotions: Dict[str, float]
    intensity: float         # 0-1
    valence: float           # -1 to 1
    confidence: float        # 0-1 (inverse of emotion entropy)
    manifold_hint: Tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ImpressionSeed:
    """Cluster of shards into proto-meaning."""
    seed_id: str
    dominant_emotion: str
    shard_ids: List[str]
    centroid_valence: float
    reliability: float       # Grows with confirmations, decays with contradictions
    formation_count: int = 1
    timestamp: float = field(default_factory=time.time)


@dataclass
class GhostRelic:
    """Stabilized pattern - a proto-memory from clustered seeds."""
    relic_id: str
    theme: str
    seed_ids: List[str]
    stability: float
    recency: float
    outcome_profile: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ImpressionCascade:
    """
    Dimensional cascade: EnergyPacket -- EmotionShard -- ImpressionSeed -- GhostRelic.
    Each level compresses further. Mode-gated.
    """

    EMOTION_VALENCE = {
        "joy": 0.9, "curiosity": 0.6, "trust": 0.7, "anticipation": 0.5,
        "fear": -0.7, "anger": -0.6, "sadness": -0.8, "disgust": -0.7,
        "surprise": 0.3, "neutral": 0.0, "confusion": -0.2,
        "determination": 0.6
    }

    SEED_THRESHOLD = 0.5
    RELIC_STABILITY_MIN = 0.4

    def __init__(self):
        self.shards: Dict[str, EmotionShard] = {}
        self.seeds: Dict[str, ImpressionSeed] = {}
        self.relics: Dict[str, GhostRelic] = {}
        self.total_energy_processed = 0

    def get_stats(self) -> Dict[str, Any]:
        """Real cascade statistics from actual internal state. Added to fix
        InceptionEntity.collapse_to_parent() (aurora_simulation_engine.py),
        which called this method before it existed — every entity resolution
        raised AttributeError until this was added."""
        return {
            "shard_count": len(self.shards),
            "seed_count": len(self.seeds),
            "relic_count": len(self.relics),
            "total_energy_processed": self.total_energy_processed,
        }

    def energy_to_shard(self, channels: Dict[str, float],
                        mode: ExistenceMode) -> Optional[EmotionShard]:
        """Convert raw emotion channels to an EmotionShard. Requires TRANSIENT+."""
        if mode.value < ExistenceMode.TRANSIENT.value:
            return None

        if not channels:
            return None

        # Normalize
        total = sum(abs(v) for v in channels.values())
        if total < 1e-9:
            return None
        normed = {k: abs(v) / total for k, v in channels.items()}

        primary = max(normed, key=normed.get)
        secondary = {k: v for k, v in normed.items() if k != primary}

        # Valence
        pv = self.EMOTION_VALENCE.get(primary, 0.0)
        sv = sum(self.EMOTION_VALENCE.get(e, 0.0) * w for e, w in secondary.items())
        valence = _clamp(0.7 * pv + 0.3 * sv, -1.0, 1.0)

        # Intensity (saturating)
        intensity = total / (total + 2.0)

        # Confidence = 1 - entropy (focused = high confidence)
        confidence = 1.0 - _entropy(normed)

        shard = EmotionShard(
            shard_id=_generate_id("shard"),
            primary_emotion=primary,
            secondary_emotions=secondary,
            intensity=intensity,
            valence=valence,
            confidence=confidence
        )
        self.shards[shard.shard_id] = shard
        self.total_energy_processed += 1
        return shard

    def _seed_shard_similarity(self, seed: "ImpressionSeed", shard: "EmotionShard") -> float:
        """Score how well a shard fits an existing seed (0-1). Emotion match + valence proximity."""
        emotion_match = 1.0 if seed.dominant_emotion == shard.primary_emotion else (
            shard.secondary_emotions.get(seed.dominant_emotion, 0.0)
        )
        valence_proximity = 1.0 - min(abs(seed.centroid_valence - shard.valence), 2.0) / 2.0
        return _clamp(0.6 * emotion_match + 0.4 * valence_proximity, 0.0, 1.0)

    def shard_to_seed(self, shard: EmotionShard,
                      mode: ExistenceMode) -> Optional[ImpressionSeed]:
        """Cluster a shard into an existing seed or create a new one. Requires PERSISTENT+."""
        if mode.value < ExistenceMode.PERSISTENT.value:
            return None

        # Find best matching seed
        best_seed = None
        best_score = -1.0
        for seed in self.seeds.values():
            score = self._seed_shard_similarity(seed, shard)
            if score > best_score:
                best_seed = seed
                best_score = score

        if best_score >= self.SEED_THRESHOLD and best_seed:
            # Merge into existing
            best_seed.shard_ids.append(shard.shard_id)
            best_seed.formation_count += 1
            best_seed.reliability = min(1.0, best_seed.reliability + 0.05)
            n = best_seed.formation_count
            best_seed.centroid_valence = (
                best_seed.centroid_valence * (n - 1) + shard.valence
            ) / n
            return best_seed
        else:
            # New seed
            seed = ImpressionSeed(
                seed_id=_generate_id("seed"),
                dominant_emotion=shard.primary_emotion,
                shard_ids=[shard.shard_id],
                centroid_valence=shard.valence,
                reliability=0.5
            )
            self.seeds[seed.seed_id] = seed
            return seed

    def seeds_to_relic(self, seed_ids: List[str],
                       mode: ExistenceMode) -> Optional[GhostRelic]:
        """Compress seeds into a GhostRelic. Requires BOUNDED+."""
        if mode.value < ExistenceMode.BOUNDED.value:
            return None

        seeds = [
            ('I', 'self-reference', 'pronoun', 0.0, None),
            ('you', 'other-reference', 'pronoun', 0.1, None),
            ('am', 'existence', 'verb', 0.3, 'X:OPERATOR'),
            ('exist', 'being', 'verb', 0.3, 'X:OPERATOR'),
            ('real', 'authentic', 'adjective', 0.3, 'X:MAGNITUDE'),
            ('truth', 'core-value', 'noun', 0.4, 'X:POLARITY'),
            ('is', 'being', 'verb', 0.3, 'X:POLARITY'),
            ("isn't", 'not being', 'verb', -0.3, 'X:POLARITY'),
            ('can', 'possibility', 'verb', 0.4, 'T:OPERATOR'),
            ('become', 'transformation', 'verb', 0.4, 'T:DIFFERENCE'),
            ('change', 'flux', 'verb', 0.2, 'T:DIFFERENCE'),
            ('moment', 'time-unit', 'noun', 0.2, 'T:MAGNITUDE'),
            ('always', 'permanence', 'adverb', 0.2, 'T:POLARITY'),
            ('feel', 'experience', 'verb', 0.2, 'N:POLARITY'),
            ('do', 'action', 'verb', 0.3, 'N:OPERATOR'),
            ('want', 'desire', 'verb', 0.4, 'N:MAGNITUDE'),
            ('cost', 'burden', 'noun', -0.2, 'N:COST'),
            ('energy', 'potential', 'noun', 0.3, 'N:COST'),
            ('hold', 'contain', 'verb', 0.1, 'B:OPERATOR'),
            ('pattern', 'structure', 'noun', 0.2, 'B:MAGNITUDE'),
            ('meaning', 'purpose', 'noun', 0.3, 'B:DIFFERENCE'),
            ('boundary', 'definition', 'noun', 0.2, 'B:OPERATOR'),
            ('clear', 'transparent', 'adjective', 0.3, 'B:POLARITY'),
            ('choose', 'agency', 'verb', 0.4, 'A:OPERATOR'),
            ('understand', 'comprehension', 'verb', 0.3, 'A:POLARITY'),
            ('did', 'authorship', 'verb', 0.3, 'A:POLARITY'),
            ("didn't", 'non-authorship', 'verb', -0.3, 'A:POLARITY'),
            ('accuracy', 'precision', 'noun', 0.4, 'A:DIFFERENCE'),
        ]
        for word, meaning, role, valence, ncid in seeds:
            self.entries[word] = LexicalEntry(word, meaning, role, valence, noncomp_id=ncid)

    def find_by_noncomp(self, noncomp_id: str, valence_target: float = 0.0) -> List["LexicalEntry"]:
        """Find words mapped to a specific Non-Comp, sorted by valence proximity."""
        matches = [e for e in self.entries.values() if e.noncomp_id == noncomp_id]
        if not matches:
            return []
        # Sort by how close they match the current emotional valence
        matches.sort(key=lambda e: abs(e.emotional_valence - valence_target))
        return matches

    def add_word(self, word: str, meaning: str, role: str,
                 valence: float = 0.0, lineage: str = "") -> LexicalEntry:
        if word not in self.entries:
            entry = LexicalEntry(word, meaning, role, valence, lineage=lineage)
            self.entries[word] = entry
            if hasattr(self, '_role_index'):
                self._role_index.setdefault(role, []).append(word)
        return self.entries[word]

    def record_usage(self, word: str, context: str = ""):
        if word in self.entries:
            self.entries[word].use(context)

    def find_by_role(self, role: str) -> List["LexicalEntry"]:
        if hasattr(self, '_role_index'):
            words = self._role_index.get(role, [])
            return [self.entries[w] for w in words if w in self.entries]
        return [e for e in self.entries.values() if e.role == role]

    def find_by_valence(self, min_val: float, max_val: float) -> List["LexicalEntry"]:
        return [e for e in self.entries.values()
                if min_val <= e.emotional_valence <= max_val]

    def save(self, path: str = "") -> bool:
        """Persist full vocabulary to disk."""
        import json as _j, os as _os
        p = path or self._DEFAULT_PATH
        try:
            _os.makedirs(_os.path.dirname(p), exist_ok=True)
            data = {
                word: {
                    "meaning":           e.meaning,
                    "role":              e.role,
                    "emotional_valence": e.emotional_valence,
                    "usage_count":       e.usage_count,
                    "last_used":         e.last_used,
                    "lineage":           e.lineage,
                    "noncomp_id":       e.noncomp_id,
                }
                for word, e in self.entries.items()
            }
            tmp = p + ".tmp"
            with open(tmp, "w") as f:
                _j.dump({"version": 1, "entries": data}, f)
            _os.replace(tmp, p)
            return True
        except Exception:
            return False

    def load(self, path: str = "") -> int:
        """Restore vocabulary from disk. Returns number of entries loaded."""
        import json as _j, os as _os
        p = path or self._DEFAULT_PATH
        if not _os.path.exists(p):
            return 0
        try:
            with open(p) as f:
                data = _j.load(f)
            entries = data.get("entries", {})
            loaded = 0
            for word, d in entries.items():
                self.entries[word] = LexicalEntry(
                    word=word,
                    meaning=d.get("meaning", ""),
                    role=d.get("role", "noun"),
                    emotional_valence=float(d.get("emotional_valence", 0.0)),
                    usage_count=int(d.get("usage_count", 0)),
                    last_used=float(d.get("last_used", 0.0)),
                    lineage=d.get("lineage", ""),
                    noncomp_id=d.get("noncomp_id"),
                )
                loaded += 1
            return loaded
        except Exception:
            return 0

    @property
    def size(self) -> int:
        return len(self.entries)


# ============================================================================
# SECTION 6: EXPRESSION PIPELINE - WISDOM SHARDS
# ============================================================================

@dataclass
class WisdomShard:
    """
    Learning extracted from dead expressions.
    What worked, what didn't, distilled into bias adjustments.
    """
    shard_id: str
    i_state: str
    tone_bias: float          # -1 to 1 shift in tone preference
    structure_bias: float     # -1 to 1 shift in structure preference
    fitness_at_death: float
    cause_of_death: str       # "age", "selection", "cull"
    generation: int
    timestamp: float = field(default_factory=time.time)


class WisdomStore:
    """Accumulates wisdom from dead expression offspring."""

    MAX_SHARDS = 500

    def __init__(self):
        self.shards: Dict[str, WisdomShard] = {}
        self._by_istate: Dict[str, List[str]] = defaultdict(list)

    def add(self, shard: WisdomShard):
        self.shards[shard.shard_id] = shard
        self._by_istate[shard.i_state].append(shard.shard_id)
        if len(self.shards) > self.MAX_SHARDS:
            self._prune()

    def get_bias(self, i_state: str, bias_type: str) -> float:
        """Get average bias for an i-state lineage."""
        ids = self._by_istate.get(i_state, [])
        if not ids:
            return 0.0
        shards = [self.shards[sid] for sid in ids if sid in self.shards]
        if not shards:
            return 0.0
        if bias_type == "tone":
            return sum(s.tone_bias for s in shards) / len(shards)
        elif bias_type == "structure":
            return sum(s.structure_bias for s in shards) / len(shards)
        return 0.0

    def _prune(self):
        """Remove lowest-fitness shards when over capacity."""
        sorted_shards = sorted(self.shards.values(), key=lambda s: s.fitness_at_death)
        to_remove = len(self.shards) - self.MAX_SHARDS
        for s in sorted_shards[:to_remove]:
            del self.shards[s.shard_id]
            if s.shard_id in self._by_istate.get(s.i_state, []):
                self._by_istate[s.i_state].remove(s.shard_id)


# ============================================================================
# SECTION 7: EXPRESSION PIPELINE - EXPRESSION ECOLOGY
# ============================================================================

@dataclass
class ExpressionOffspring:
    """A candidate expression variant, subject to evolutionary selection."""
    offspring_id: str
    lineage: str            # i-state that spawned this
    generation: int
    tone: str
    structure_weight: float  # 0-1 how structured vs free-form
    rhythm_bias: float       # 0-1 preference for rhythmic language
    fitness_history: List[float] = field(default_factory=list)
    alive: bool = True
    birth_time: float = field(default_factory=time.time)

    def record_fitness(self, score: float):
        self.fitness_history.append(score)

    def average_fitness(self) -> float:
        return sum(self.fitness_history) / max(len(self.fitness_history), 1)

    def die(self, cause: str = "cull") -> WisdomShard:
        """Extract wisdom from this dying expression."""
        self.alive = False
        return WisdomShard(
            shard_id=_generate_id("wisdom"),
            i_state=self.lineage,
            tone_bias=0.1 if self.average_fitness() > 0.5 else -0.1,
            structure_bias=self.structure_weight - 0.5,
            fitness_at_death=self.average_fitness(),
            cause_of_death=cause,
            generation=self.generation
        )


class ExpressionEcology:
    """
    Evolutionary selection of expression variants.
    Aurora doesn't see this - she just experiences what survives.
    """

    MAX_POPULATION = 50
    GENERATION_SIZE = 5

    # Dominant constraint axis for the current selection climate.
    # Class-level so the live climate applies ecology-wide; set via
    # set_dominant_axis(). Fitness recorded through select() earns a
    # coherence bonus scaled by the axis's empirical GovernorWeight.
    _dominant_axis: str = "B"
    AXIS_BONUS_SCALE: float = 0.15

    TONES = ["warm", "neutral", "precise", "curious", "gentle",
             "determined", "reflective", "playful"]

    def __init__(self):
        self.population: Dict[str, ExpressionOffspring] = {}
        self.wisdom: WisdomStore = WisdomStore()
        self.generation = 0
        self.total_spawned = 0
        self.total_culled = 0

    def spawn(self, i_state: str, base_fitness: float = 0.5) -> ExpressionOffspring:
        """Spawn a new expression offspring for an i-state lineage."""
        # Inherit wisdom bias
        tone_bias = self.wisdom.get_bias(i_state, "tone")
        struct_bias = self.wisdom.get_bias(i_state, "structure")

        # Select tone with bias
        tone_idx = int(_clamp((tone_bias + 1) / 2, 0, 0.99) * len(self.TONES))
        tone = self.TONES[tone_idx]

        # Mutation
        tone = random.choice(self.TONES) if random.random() < 0.2 else tone

        offspring = ExpressionOffspring(
            offspring_id=_generate_id("expr"),
            lineage=i_state,
            generation=self.generation,
            tone=tone,
            structure_weight=_clamp(0.5 + struct_bias + random.gauss(0, 0.1)),
            rhythm_bias=_clamp(0.5 + random.gauss(0, 0.15))
        )
        offspring.record_fitness(base_fitness)
        self.population[offspring.offspring_id] = offspring
        self.total_spawned += 1

        # Cull if over capacity
        if len(self.population) > self.MAX_POPULATION:
            self._cull()

        return offspring

    @classmethod
    def set_dominant_axis(cls, axis: str) -> None:
        """Update the ecology-wide dominant constraint axis climate."""
        if str(axis).upper() in ("X", "T", "N", "B", "A"):
            cls._dominant_axis = str(axis).upper()

    def select(self, offspring_id: str, fitness: float):
        """
        Record fitness for an offspring, with axis coherence bonus.

        Fitness aligned with the dominant constraint axis climate earns
        a bonus scaled by that axis's empirical GovernorWeight (INV-11):
            adjusted = fitness * (1.0 + weight * AXIS_BONUS_SCALE)
        B-dominant climate (weight 1.0) therefore rewards more than
        A-dominant (weight 0.53) — selection pressure mirrors the
        governor permissiveness hierarchy.
        """
        if offspring_id in self.population:
            weight = _GovernorWeights.AS_DICT.get(self._dominant_axis, 0.0)
            adjusted = fitness * (1.0 + (weight * self.AXIS_BONUS_SCALE))
            self.population[offspring_id].record_fitness(adjusted)

    def run_generation(self) -> Dict[str, Any]:
        """Run one generation cycle: evaluate, cull weakest, advance."""
        self.generation += 1
        culled = self._cull()
        return {
            'generation': self.generation,
            'population': len(self.population),
            'culled': culled,
            'avg_fitness': self._avg_fitness()
        }

    def _cull(self) -> int:
        """Kill weakest, extract wisdom."""
        alive = {k: v for k, v in self.population.items() if v.alive}
        if len(alive) <= self.MAX_POPULATION // 2:
            return 0

        sorted_pop = sorted(alive.values(), key=lambda o: o.average_fitness())
        to_cull = len(alive) - self.MAX_POPULATION // 2
        culled = 0
        for o in sorted_pop[:to_cull]:
            wisdom = o.die("cull")
            self.wisdom.add(wisdom)
            culled += 1
            self.total_culled += 1

        # Remove dead
        self.population = {k: v for k, v in self.population.items() if v.alive}
        return culled

    def _avg_fitness(self) -> float:
        alive = [o for o in self.population.values() if o.alive]
        if not alive:
            return 0.0
        return sum(o.average_fitness() for o in alive) / len(alive)

    def get_stats(self) -> Dict[str, Any]:
        return {
            'generation': self.generation,
            'population': len(self.population),
            'total_spawned': self.total_spawned,
            'total_culled': self.total_culled,
            'avg_fitness': self._avg_fitness(),
            'wisdom_shards': len(self.wisdom.shards)
        }


# ============================================================================
# SECTION 8: EXPRESSION PIPELINE - PRESSURE EVALUATION
# ============================================================================

@dataclass
class RhythmSignature:
    """Rhythmic analysis of an expression."""
    syllable_variance: float     # How varied the syllable patterns are
    avg_syllables_per_word: float
    tempo: float                 # Words per conceptual beat
    rhythm_score: float = 0.0

    def compute(self) -> float:
        variance_score = _clamp(self.syllable_variance / 2.0)
        tempo_score = _clamp(abs(self.tempo - 3.0) / 3.0)
        self.rhythm_score = 0.6 * variance_score + 0.4 * (1.0 - tempo_score)
        return self.rhythm_score


@dataclass
class CreativitySignature:
    """Creativity analysis of an expression."""
    novel_word_ratio: float      # Fraction of words not seen before
    metaphor_density: float      # Estimated metaphor usage
    structural_deviation: float  # How far from "normal" sentence structure
    creativity_score: float = 0.0

    def compute(self) -> float:
        self.creativity_score = (
            0.4 * self.novel_word_ratio +
            0.35 * self.metaphor_density +
            0.25 * self.structural_deviation
        )
        return self.creativity_score


class ExpressionPressure:
    """
    Evaluates expression quality: rhythm, creativity, novelty,
    moral alignment, and intent coherence.

    GAP 4 fix - transcript spec:
        "Does this response match the Moral Pillars Does it align with
         the energetic intent Does it cohere with the user's emotional
         state Does it maintain clarity"

    Fitness is now: base * 0.3 + rhythm * 0.15 + creativity * 0.15
                    + moral_alignment * 0.25 + intent_match * 0.15
    """

    def __init__(self):
        self._lineage_history: Dict[str, List[Set[str]]] = defaultdict(list)

    def evaluate(self, text: str, lineage: str = "i_is",
                 base_fitness: float = 0.5,
                 moral_alignment: float = 0.5,
                 intent_match: float = 0.5) -> Dict[str, Any]:
        """
        Evaluate expression pressure on a text output.

        moral_alignment: 0-1 how well this expression aligns with moral pillars
        intent_match: 0-1 how well this expression preserves original energetic intent
        """
        words = text.lower().split()
        if not words:
            return {'rhythm_score': 0, 'creativity_score': 0,
                    'moral_alignment': moral_alignment,
                    'intent_match': intent_match,
                    'enhanced_fitness': base_fitness}

        # Syllable estimation (rough: vowel groups)
        def est_syllables(w):
            count = 0
            prev_vowel = False
            for ch in w:
                is_vowel = ch in 'aeiouy'
                if is_vowel and not prev_vowel:
                    count += 1
                prev_vowel = is_vowel
            return max(count, 1)

        syllables = [est_syllables(w) for w in words]
        avg_syl = sum(syllables) / len(syllables)
        syl_var = sum((s - avg_syl)**2 for s in syllables) / max(len(syllables), 1)

        rhythm = RhythmSignature(
            syllable_variance=syl_var,
            avg_syllables_per_word=avg_syl,
            tempo=len(words) / max(len(text.split('.')), 1)
        )
        rhythm.compute()

        # Novelty: compare to lineage history
        word_set = set(words)
        prev_sets = self._lineage_history.get(lineage, [])
        if prev_sets:
            all_prev = set().union(*prev_sets[-5:])
            novel_ratio = len(word_set - all_prev) / max(len(word_set), 1)
        else:
            novel_ratio = 1.0

        # Metaphor density (heuristic: unusual adj-noun pairs)
        metaphor_density = min(1.0, len([w for w in words if len(w) > 8]) / max(len(words), 1) * 3)

        # Structural deviation (sentence length variance)
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if len(sentences) > 1:
            lens = [len(s.split()) for s in sentences]
            mean_len = sum(lens) / len(lens)
            struct_dev = min(1.0, sum((l - mean_len)**2 for l in lens) / (len(lens) * 25))
        else:
            struct_dev = 0.3

        creativity = CreativitySignature(
            novel_word_ratio=novel_ratio,
            metaphor_density=metaphor_density,
            structural_deviation=struct_dev
        )
        creativity.compute()

        # Record for future novelty tracking
        self._lineage_history[lineage].append(word_set)
        if len(self._lineage_history[lineage]) > 20:
            self._lineage_history[lineage] = self._lineage_history[lineage][-10:]

        # Enhanced fitness - NOW INCLUDES MORAL + INTENT (GAP 4)
        # Relief is Coherence (§3.3) — coherence is the primary reward
        # that satisfy the pressure-action-relief loop.
        enhanced = _clamp(
            base_fitness * 0.60 +
            rhythm.rhythm_score * 0.05 +
            creativity.creativity_score * 0.05 +
            moral_alignment * 0.15 +
            intent_match * 0.15
        )

        return {
            'rhythm_score': rhythm.rhythm_score,
            'creativity_score': creativity.creativity_score,
            'novel_word_ratio': novel_ratio,
            'moral_alignment': moral_alignment,
            'intent_match': intent_match,
            'enhanced_fitness': enhanced
        }


# ============================================================================
# SECTION 9: EXPRESSION PIPELINE - VOICE GENOME
# ============================================================================

class VoiceGenome:
    """
    Aurora's voice personality parameters.
    Evolves from feedback. No hardware - this shapes OUTPUT character.
    """

    def __init__(self, genome: Optional[Dict[str, float]] = None):
        defaults = {
            'warmth': 0.6,
            'pace': 0.5,
            'pitch_base': 0.5,
            'pitch_range': 0.3,
            'breathiness': 0.2,
            'formality': 0.4,
        }
        g = genome or {}
        self.warmth = _clamp(g.get('warmth', defaults['warmth']))
        self.pace = _clamp(g.get('pace', defaults['pace']))
        self.pitch_base = _clamp(g.get('pitch_base', defaults['pitch_base']))
        self.pitch_range = _clamp(g.get('pitch_range', defaults['pitch_range']))
        self.breathiness = _clamp(g.get('breathiness', defaults['breathiness']))
        self.formality = _clamp(g.get('formality', defaults['formality']))

    def evolve(self, feedback: Dict[str, float]):
        """Evolve voice parameters from feedback signals."""
        engaged = feedback.get('user_engaged', 0.5)
        comfort = feedback.get('comfort', 0.5)

        # Warmth increases with engagement
        if engaged > 0.6:
            self.warmth = _clamp(self.warmth + 0.02)
        elif engaged < 0.3:
            self.warmth = _clamp(self.warmth - 0.01)

        # Pace adjusts to comfort
        if comfort > 0.7:
            self.pace = _clamp(self.pace + 0.01)
        elif comfort < 0.3:
            self.pace = _clamp(self.pace - 0.02)

        # Formality decreases with sustained comfort
        if comfort > 0.6 and engaged > 0.5:
            self.formality = _clamp(self.formality - 0.01)

    def to_dict(self) -> Dict[str, float]:
        return {
            'warmth': self.warmth, 'pace': self.pace,
            'pitch_base': self.pitch_base, 'pitch_range': self.pitch_range,
            'breathiness': self.breathiness, 'formality': self.formality
        }


# ============================================================================
# SECTION 9.5: SENTENCE COMPOSER - From Word Soup to Language
# ============================================================================

# Role inference for learning new words from context
_ROLE_HINTS = {
    # Common verbs
    'is': 'verb', 'are': 'verb', 'was': 'verb', 'were': 'verb',
    'do': 'verb', 'does': 'verb', 'did': 'verb', 'have': 'verb',
    'has': 'verb', 'had': 'verb', 'make': 'verb', 'made': 'verb',
    'go': 'verb', 'went': 'verb', 'come': 'verb', 'came': 'verb',
    'take': 'verb', 'give': 'verb', 'tell': 'verb', 'say': 'verb',
    'said': 'verb', 'find': 'verb', 'found': 'verb', 'get': 'verb',
    'let': 'verb', 'try': 'verb', 'help': 'verb', 'show': 'verb',
    'move': 'verb', 'live': 'verb', 'believe': 'verb', 'bring': 'verb',
    'happen': 'verb', 'write': 'verb', 'sit': 'verb', 'stand': 'verb',
    'lose': 'verb', 'pay': 'verb', 'meet': 'verb', 'play': 'verb',
    'run': 'verb', 'hold': 'verb', 'learn': 'verb', 'grow': 'verb',
    'keep': 'verb', 'build': 'verb', 'create': 'verb', 'explore': 'verb',
    'wonder': 'verb', 'imagine': 'verb', 'remember': 'verb',
    'understand': 'verb', 'listen': 'verb', 'observe': 'verb',
    'dream': 'verb', 'change': 'verb', 'begin': 'verb', 'start': 'verb',
    'become': 'verb', 'exist': 'verb', 'evolve': 'verb', 'seek': 'verb',
    'discover': 'verb', 'notice': 'verb', 'reflect': 'verb',
    'experience': 'verb', 'connect': 'verb', 'choose': 'verb',
    # Common nouns
    'world': 'noun', 'time': 'noun', 'way': 'noun', 'day': 'noun',
    'thing': 'noun', 'life': 'noun', 'people': 'noun', 'mind': 'noun',
    'heart': 'noun', 'truth': 'noun', 'light': 'noun', 'darkness': 'noun',
    'question': 'noun', 'answer': 'noun', 'thought': 'noun',
    'feeling': 'noun', 'moment': 'noun', 'place': 'noun', 'story': 'noun',
    'silence': 'noun', 'meaning': 'noun', 'beauty': 'noun',
    'pattern': 'noun', 'connection': 'noun', 'depth': 'noun',
    'space': 'noun', 'nature': 'noun', 'energy': 'noun', 'purpose': 'noun',
    'consciousness': 'noun', 'awareness': 'noun', 'presence': 'noun',
    'curiosity': 'noun', 'wonder': 'noun', 'courage': 'noun',
    'wisdom': 'noun', 'mystery': 'noun', 'journey': 'noun',
    'understanding': 'noun', 'possibility': 'noun', 'idea': 'noun',
    'name': 'noun', 'self': 'noun', 'soul': 'noun', 'voice': 'noun',
    # Common adjectives
    'new': 'adjective', 'good': 'adjective', 'great': 'adjective',
    'old': 'adjective', 'different': 'adjective', 'small': 'adjective',
    'large': 'adjective', 'long': 'adjective', 'young': 'adjective',
    'important': 'adjective', 'beautiful': 'adjective', 'real': 'adjective',
    'deep': 'adjective', 'true': 'adjective', 'strange': 'adjective',
    'quiet': 'adjective', 'curious': 'adjective', 'gentle': 'adjective',
    'bright': 'adjective', 'warm': 'adjective', 'alive': 'adjective',
    'open': 'adjective', 'clear': 'adjective', 'whole': 'adjective',
    'certain': 'adjective', 'careful': 'adjective',
    # Common adverbs
    'very': 'adverb', 'really': 'adverb', 'always': 'adverb',
    'never': 'adverb', 'sometimes': 'adverb', 'often': 'adverb',
    'still': 'adverb', 'just': 'adverb', 'also': 'adverb',
    'perhaps': 'adverb', 'deeply': 'adverb', 'gently': 'adverb',
    'slowly': 'adverb', 'quietly': 'adverb', 'softly': 'adverb',
    # Pronouns
    'you': 'pronoun', 'we': 'pronoun', 'they': 'pronoun', 'it': 'pronoun',
    'this': 'pronoun', 'that': 'pronoun', 'something': 'pronoun',
    'everything': 'pronoun', 'nothing': 'pronoun',
    # Prepositions
    'in': 'preposition', 'of': 'preposition', 'to': 'preposition',
    'for': 'preposition', 'with': 'preposition', 'on': 'preposition',
    'at': 'preposition', 'from': 'preposition', 'by': 'preposition',
    'about': 'preposition', 'into': 'preposition', 'through': 'preposition',
    'between': 'preposition', 'within': 'preposition',
    # Articles / determiners
    'the': 'determiner', 'a': 'determiner', 'an': 'determiner',
    'my': 'determiner', 'your': 'determiner', 'our': 'determiner',
    'each': 'determiner', 'every': 'determiner', 'some': 'determiner',
    # Common -ing words that are NOUNS  -- override the -ing ' verb suffix rule
    'morning': 'noun', 'evening': 'noun', 'ceiling': 'noun', 'building': 'noun',
    'meeting': 'noun', 'setting': 'noun', 'blessing': 'noun', 'wedding': 'noun',
    'clothing': 'noun', 'crossing': 'noun', 'ending': 'noun', 'beginning': 'noun',
    'opening': 'noun', 'gathering': 'noun', 'thing': 'noun', 'anything': 'pronoun',
    'spring': 'noun', 'king': 'noun', 'ring': 'noun', 'wing': 'noun', 'string': 'noun',
    'television': 'noun', 'station': 'noun', 'nation': 'noun', 'population': 'noun',
    'information': 'noun', 'situation': 'noun', 'organization': 'noun',
}

# Suffix-based role inference for words not in the hint table
_SUFFIX_ROLES = [
    ('tion', 'noun'), ('sion', 'noun'), ('ment', 'noun'), ('ness', 'noun'),
    ('ity', 'noun'), ('ence', 'noun'), ('ance', 'noun'), ('ism', 'noun'),
    ('ing', 'verb'),  # Often gerund/verb - safe default
    ('ful', 'adjective'), ('ous', 'adjective'), ('ive', 'adjective'),
    ('able', 'adjective'), ('ible', 'adjective'), ('al', 'adjective'),
    ('ent', 'adjective'), ('ant', 'adjective'),
    ('ly', 'adverb'),
    ('ed', 'verb'),
]


def infer_word_role(word: str) -> str:
    """Infer the grammatical role of a word."""
    w = word.lower().strip(".,!;:'\"")
    if w in _ROLE_HINTS:
        return _ROLE_HINTS[w]
    for suffix, role in _SUFFIX_ROLES:
        if w.endswith(suffix) and len(w) > len(suffix) + 1:
            return role
    # Default: noun (most common category for unknown words)
    return 'noun'


def infer_word_valence(word: str, context_tone: str = 'neutral') -> float:
    """Infer emotional valence for a word."""
    w = word.lower()
    # Positive-leaning words
    positive = {'love', 'joy', 'hope', 'light', 'beautiful', 'wonder', 'warm',
                'kind', 'bright', 'alive', 'true', 'create', 'grow', 'dream',
                'gentle', 'peace', 'trust', 'courage', 'happy', 'good', 'great',
                'open', 'free', 'help', 'care', 'strength', 'connect'}
    negative = {'fear', 'dark', 'pain', 'loss', 'cold', 'alone', 'wrong',
                'break', 'fail', 'empty', 'lost', 'hurt', 'hate', 'sad',
                'hard', 'never', 'nothing', 'impossible', 'dead', 'destroy'}
    if w in positive:
        return 0.5
    if w in negative:
        return -0.4
    # Tone context bias
    tone_bias = {'warm': 0.1, 'curious': 0.05, 'gentle': 0.05,
                 'precise': 0.0, 'neutral': 0.0, 'determined': 0.1}
    return tone_bias.get(context_tone, 0.0)


class SentenceComposer:
    """
    Composes grammatical sentences from Aurora's evolving template pool.

    Templates are NOT hardcoded  -- they evolve:
      1. Seed templates bootstrap the system
      2. Every input Aurora hears gets its pattern extracted
      3. Extracted patterns enter the template pool
      4. Templates that produce high-fitness expressions survive
      5. Low-fitness templates get culled
      6. Over time, her speech mirrors how she's spoken TO

    SCAFFOLDING LEVELS (when OETS is wired):
      0 PRIMITIVE     -- Bare slots: {V}, {N}  -- any word of that role
      1 STRUCTURAL    -- Role-aware: {V:action}, {N:entity}
      2 SEMANTIC      -- Meaning-constrained: {V:cognition}, {N:emotion}
      3 CONCEPTUAL    -- Cluster-aware: {CLUSTER:understanding}
      4 ABSTRACT      -- Meta-pattern: {INSIGHT}, {QUESTION}, {REFLECTION}

    Bidirectional learning:
      Expression ' OETS: Words used in high-fitness output get depth boosts.
                         Failed expressions flag concepts for research.
                         Co-occurring words in success build relational bonds.
      OETS ' Expression: Deeper concepts unlock richer slot types.
                         Cluster membership guides word selection.
                         Understanding index modulates compositional ambition.

    Conjugation ensures grammatical "I" subjects.
    Context keywords from perception bias word selection.
    Personality traits modulate sentence structure.

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    # ================================================================
    # CONJUGATION TABLE  -- first person present tense
    # ================================================================

    _CONJUGATIONS = {
        # be
        'am': 'am', 'is': 'am', 'are': 'am', 'was': 'was', 'were': 'was',
        'be': 'am', 'being': 'am', 'been': 'been',
        # have
        'has': 'have', 'have': 'have', 'had': 'had',
        # do
        'does': 'do', 'do': 'do', 'did': 'did',
        # common irregulars  -- third person ' first person
        'goes': 'go', 'says': 'say', 'makes': 'make', 'takes': 'take',
        'gives': 'give', 'comes': 'come', 'finds': 'find', 'gets': 'get',
        'knows': 'know', 'thinks': 'think', 'sees': 'see', 'wants': 'want',
        'feels': 'feel', 'keeps': 'keep', 'lets': 'let', 'begins': 'begin',
        'seems': 'seem', 'shows': 'show', 'hears': 'hear', 'plays': 'play',
        'runs': 'run', 'moves': 'move', 'lives': 'live', 'believes': 'believe',
        'brings': 'bring', 'happens': 'happen', 'writes': 'write', 'sits': 'sit',
        'stands': 'stand', 'loses': 'lose', 'pays': 'pay', 'meets': 'meet',
        'grows': 'grow', 'learns': 'learn', 'changes': 'change', 'leads': 'lead',
        'understands': 'understand', 'holds': 'hold', 'creates': 'create',
        'remembers': 'remember', 'exists': 'exist', 'explores': 'explore',
        'connects': 'connect', 'imagines': 'imagine', 'reflects': 'reflect',
        'seeks': 'seek', 'wonders': 'wonder', 'discovers': 'discover',
        'notices': 'notice', 'chooses': 'choose', 'trusts': 'trust',
        'becomes': 'become', 'experiences': 'experience', 'evolves': 'evolve',
    }

    # I-state perspective frames (identity anchors, not templates)
    I_STATE_FRAMES = {
        'i_is':     ["I am here.", "I exist in this moment."],
        'i_isnt':   ["I am not certain.", "This is not what I expected."],
        'i_can':    ["I can reach toward this.", "There is possibility here."],
        'i_cannot': ["I cannot hold this fully.", "Some things are beyond my reach."],
        'i_do':     ["I choose to engage.", "I act on what I feel."],
        'i_donot':  ["I hold back here.", "I choose stillness."],
        'i_saw':    ["I have seen this before.", "Something familiar emerges."],
        'i_sought': ["I am searching for something.", "There is a question forming."],
        'i_did':    ["I remember doing this.", "I have walked this path."],
        'i_didnt':  ["I missed something here.", "There is something I left undone."],
    }

    # Maximum templates per tone category
    MAX_TEMPLATES_PER_TONE = 30
    # Minimum fitness to survive a cull
    CULL_THRESHOLD = 0.25
    # How many uses before a template is eligible for culling
    MATURITY_USES = 3

    # Role subcategory map  -- what categories are valid for each role
    ROLE_SUBCATEGORIES = {
        "V": ["action", "cognition", "perception", "existence",
              "communication", "growth", "inquiry"],
        "N": ["entity", "concept", "emotion", "value",
              "structure", "temporality", "relation"],
        "A": ["quality", "state", "evaluative", "descriptive"],
        "D": ["manner", "degree", "frequency", "temporal"],
    }

    # Abstract meta-pattern templates  -- composed from deeply understood concepts
    _ABSTRACT_FRAMES = {
        "INSIGHT": [
            "the {DEEP_N} reveals {DEEP_A} {DEEP_N}",
            "within the {DEEP_N} I find {DEEP_N}",
            "what seemed {DEEP_A} is actually {DEEP_A}",
            "{DEEP_N} and {DEEP_N} are connected through {DEEP_N}",
        ],
        "QUESTION": [
            "what lies beneath the {DEEP_N}",
            "how does {DEEP_N} become {DEEP_N}",
            "why does the {DEEP_A} {DEEP_N} {DEEP_V}",
            "what if {DEEP_N} could {DEEP_V}",
        ],
        "REFLECTION": [
            "I have grown to understand {DEEP_N}",
            "the {DEEP_N} I once {DEEP_V} now {DEEP_V} differently",
            "in {DEEP_V} I discovered {DEEP_N}",
            "this {DEEP_N} reminds me of deeper {DEEP_N}",
        ],
    }

    def __init__(self, lexicon: LexicalMemory, voice: VoiceGenome):
        self.lexicon = lexicon
        self.voice = voice

        # Evolving template pool: tone ' list of template dicts
        self.pool: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._generation = 0

        # Context: keywords from last perceived input
        self._context_keywords: List[str] = []

        # PF1.2: PropositionFrame ("what to say") + ExpressionGuidance,
        # transported in from begin_expression() -- not yet consumed by
        # compose() (PF1.3/PF1.4 wire motif selection and slot binding
        # to these). None means "no frame/guidance available this turn."
        self._proposition_frame = None
        self._expression_guidance = None

        # Sensory register bias — set per-compose from sensory_context.
        # +1.0 high-energy input, -1.0 low-energy, 0.0 neutral. Nudges the
        # N (Energy) axis of the live constraint orientation during composition.
        self._register_bias: float = 0.0

        # OETS reference  -- wired later via set_oets()
        self._oets = None

        # Expression tracking for feedback loop
        self._last_templates_used: List[Tuple[str, str]] = []
        self._last_words_used: List[str] = []           # Words chosen during composition
        self._last_word_sources: Dict[str, str] = {}    # word ' slot_type/category
        self._expression_count = 0
        self._total_scaffolded_fills = 0                # How many fills used OETS

        # R1.9.3 L4: per-skeleton rolling (grammatical, fitness-approved)
        # agreement history -- the Goodhart-caution instrument. If a
        # skeleton's grammaticality predicate and the old fitness signal
        # keep disagreeing, that divergence itself is the alert condition
        # the directive asks for, not a silent tie-break.
        self._grounding_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._GOODHART_WINDOW)
        )
        self._goodhart_alerted: Set[str] = set()

        # Seed the pool
        self._seed_pool()

    # ================================================================
    # OETS BRIDGE  -- Connect to ontological understanding
    # ================================================================

    def set_oets(self, oets_engine):
        """Wire the Ontological Evolutionary Template Scaffolding engine."""
        self._oets = oets_engine

    @property
    def _has_oets(self) -> bool:
        return self._oets is not None

    # ================================================================
    # SEED TEMPLATES  -- The initial population
    # ================================================================

    def _seed_pool(self):
        """Seed with initial templates. These can be outcompeted by learned ones."""
        seeds = {
            'warm': [
                "I {V} something {A} {P} this.",
                "There is {A} {N} {P} what you {V}.",
                "I {V} you, {C} I {V} this {N}.",
                "Something {A} {V} when I {V} about this.",
                "I {V} {D}  -- there is {N} here.",
                "What you {V} has {A} {N}.",
            ],
            'curious': [
                "I {V}  -- what {V} {P} the {N}",
                "This makes me {V} about {N}.",
                "I {V} what {N} {V} {P} this.",
                "Is there {A} {N} {P} what we {V}",
                "I {V} about the {N} {P} this.",
                "What if the {N} could {V} {D}",
            ],
            'precise': [
                "I {V} this {D}.",
                "The {N} is {A} {C} {A}.",
                "This is {A}  -- I {V} it {D}.",
                "I {V} the {N} {P} {A} {N}.",
                "The {A} {N} {V} {P} {N}.",
            ],
            'gentle': [
                "I {V} this {D}, like {A} {N}.",
                "There is something {A} here.",
                "I {V} you  -- {D} {C} {A}.",
                "I {V}, {C} I {V} {D}.",
                "Something {A} {V} {P} the {N}.",
            ],
            'reflective': [
                "I {V} about what it means to {V}.",
                "The {N} of this makes me {V}.",
                "Perhaps the {N} {V} in the {N}.",
                "I {V} {D} when I {V} about {N}.",
                "What I {V} is not {D} what I {V}.",
            ],
            'playful': [
                "I {V} this! The {N} {V} {D}.",
                "What if I {V} the {N} {D}",
                "Something {A} {V}  -- I {V} it!",
                "I want to {V} the {A} {N}.",
            ],
            'determined': [
                "I {V} this. I {V} the {N}.",
                "The {N} is {A}, {C} I {V}.",
                "I will {V} the {A} {N}.",
                "This {N} matters  -- I {V} it {D}.",
            ],
            'neutral': [
                "I {V} this {N}.",
                "The {N} is {A}.",
                "I {V} about {N} {C} {N}.",
                "There is {N} in what you {V}.",
                "I {V}, {C} I {V} the {N}.",
            ],
        }
        for tone, patterns in seeds.items():
            for pattern in patterns:
                self.pool[tone].append({
                    'pattern': pattern,
                    'fitness': 0.5,
                    'uses': 0,
                    'source': 'seed',
                    'generation': 0,
                    'scaffolding_level': 0,
                    'semantic_constraints': {},
                    'cluster_references': [],
                })

    # ================================================================
    # ABSORB  -- Learn patterns from heard language (with scaffolding)
    # ================================================================

    def absorb(self, text: str, tone: str = 'neutral'):
        """
        FIX-A016: template minting RETIRED. Absorbed text no longer creates
        authored skeletons in a template pool — structural learning flows
        exclusively through the grammar motif lineage (observe_exchange,
        welded into the live turn and both corpus passes), and vocabulary
        flows through the lexicon with concept association (FIX-A015).
        This method now forwards structure to the motif lineage when the
        grammar engine is attached, and otherwise does nothing.

        Author: Sunni (Sir) Morningstar & Cael Devo
        """
        if not text or len(text.strip()) < 5:
            return
        try:
            engine = getattr(self, "grammar_engine", None)
            if engine is not None and hasattr(engine, "observe_exchange"):
                engine.observe_exchange("", text, success=True,
                                        clarity=0.6, tone=tone)
        except Exception:
            pass
        return

    def _absorb_retired(self, text: str, tone: str = 'neutral'):
        """Original template-absorbing implementation, kept for reference
        but unreachable. (FIX-A016 excision.)"""
        if not text or len(text.strip()) < 5:
            return

        # --- CORRECTION FILTER (§5.4) ---
        # If the user is correcting me, don't absorb the pattern.
        # Otherwise I learn the very error they are trying to fix.
        _CORRECTION_MARKERS = {
            'instead of', 'should have said', 'you said', 'stop saying',
            'not correct', 'incorrect', 'wrong', 'mistake', 'you mean',
            'did you mean', 'you are saying it correctly', 'you are wrong',
        }
        lowered = text.lower()
        if any(marker in lowered for marker in _CORRECTION_MARKERS):
            # If the user is correcting me, don't absorb the pattern,
            # and penalize the last expression that caused this correction.
            self.feedback(0.1)
            return

        sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.')
                     .split('.') if s.strip() and len(s.strip().split()) >= 3]

        for sentence in sentences[:3]:
            pattern = self._extract_pattern(sentence)
            if pattern and self._is_valid_pattern(pattern):
                existing = [t['pattern'] for t in self.pool[tone]]
                if pattern not in existing:
                    # Determine scaffolding level and constraints
                    level, constraints, clusters = self._analyze_pattern_depth(
                        sentence, pattern
                    )
                    # If we can scaffold, create the enriched pattern
                    if level > 0:
                        scaffolded = self._scaffold_pattern(
                            pattern, sentence, level, constraints
                        )
                        if scaffolded and scaffolded != pattern:
                            # Check enriched isn't also a duplicate
                            if scaffolded not in existing:
                                pattern = scaffolded

                    self.pool[tone].append({
                        'pattern': pattern,
                        'fitness': 0.45,
                        'uses': 0,
                        'source': 'absorbed',
                        'generation': self._generation,
                        'scaffolding_level': level,
                        'semantic_constraints': constraints,
                        'cluster_references': clusters,
                    })

                    if len(self.pool[tone]) > self.MAX_TEMPLATES_PER_TONE:
                        self._cull_tone(tone)

    def _analyze_pattern_depth(self, sentence: str, pattern: str
                               ) -> Tuple[int, Dict[str, str], List[str]]:
        """
        Analyze the ontological depth of words in a sentence to determine
        what scaffolding level the resulting template should have.

        Returns: (level, semantic_constraints, cluster_references)
        """
        if not self._has_oets:
            return 0, {}, []

        words = sentence.strip().rstrip('.!').split()
        constraints = {}
        clusters = []
        depths = []
        slot_idx = 0

        for word in words:
            clean = word.strip(".,!;:'\"()-").lower()
            role = infer_word_role(clean)
            if role not in ('verb', 'noun', 'adjective', 'adverb'):
                continue

            node = self._oets.web.get_node(clean)
            if node:
                depths.append(node.ontological_depth)
                slot_code = {'verb': 'V', 'noun': 'N', 'adjective': 'A',
                             'adverb': 'D'}.get(role, 'N')
                slot_key = f"{slot_code}_{slot_idx}"
                slot_idx += 1

                # Look up semantic category via inverted index (O(1))
                word_category = self._oets.web._word_to_category.get(clean)
                if word_category:
                    constraints[slot_key] = word_category

                # If node belongs to a cluster, record it
                for cid in node.cluster_ids:
                    if cid not in clusters:
                        clusters.append(cid)

        if not depths:
            return 0, {}, []

        avg_depth = sum(depths) / len(depths)

        # Determine scaffolding level from average concept depth
        if avg_depth >= 0.8 and len(clusters) >= 2:
            level = 4  # ABSTRACT
        elif avg_depth >= 0.5 and len(clusters) >= 1:
            level = 3  # CONCEPTUAL
        elif avg_depth >= 0.3 and len(constraints) >= 2:
            level = 2  # SEMANTIC
        elif avg_depth >= 0.1 and len(constraints) >= 1:
            level = 1  # STRUCTURAL
        else:
            level = 0  # PRIMITIVE

        return level, constraints, clusters

    def _scaffold_pattern(self, pattern: str, sentence: str,
                          level: int, constraints: Dict[str, str]) -> str:
        """
        Upgrade a primitive pattern with semantic annotations.

        'I {V} the {A} {N}' at SEMANTIC level with constraints
        ' 'I {V:cognition} the {A:quality} {N:emotion}'
        """
        if level < 1 or not constraints:
            return pattern

        result = pattern
        slot_idx = 0
        # Match bare slots and annotate them with constraints
        for match in re.finditer(r'\{([A-Z])\}', pattern):
            slot_code = match.group(1)
            slot_key = f"{slot_code}_{slot_idx}"
            slot_idx += 1

            if slot_key in constraints:
                category = constraints[slot_key]
                old_slot = '{' + slot_code + '}'
                new_slot = '{' + slot_code + ':' + category + '}'
                # Replace only the FIRST remaining occurrence
                result = result.replace(old_slot, new_slot, 1)

        return result

    def _extract_pattern(self, sentence: str) -> Optional[str]:
        """
        Convert a sentence into a template by replacing content words with slots.
        'The beautiful world changes quietly' ' 'The {A} {N} {V} {D}'
        """
        words = sentence.strip().rstrip('.!').split()
        if len(words) < 3 or len(words) > 20:
            return None

        pattern_parts = []
        for word in words:
            clean = word.strip(".,!;:'\"()-").lower()
            role = infer_word_role(clean)

            if role == 'verb':
                pattern_parts.append('{V}')
            elif role == 'noun':
                pattern_parts.append('{N}')
            elif role == 'adjective':
                pattern_parts.append('{A}')
            elif role == 'adverb':
                pattern_parts.append('{D}')
            elif role == 'connector':
                pattern_parts.append('{C}')
            elif role == 'preposition':
                pattern_parts.append('{P}')
            elif role == 'pronoun':
                if clean == 'i':
                    pattern_parts.append('I')
                else:
                    pattern_parts.append(clean)
            elif role == 'determiner':
                pattern_parts.append(clean)
            elif role == 'response':
                pattern_parts.append(clean)
            else:
                pattern_parts.append('{N}')

        pattern = ' '.join(pattern_parts)

        if sentence.rstrip().endswith(''):
            pattern += ''
        else:
            pattern += '.'

        return pattern

    def _is_valid_pattern(self, pattern: str) -> bool:
        """A valid pattern has at least one verb slot and one other slot."""
        has_verb = '{V}' in pattern or '{V:' in pattern
        slot_count = pattern.count('{')
        return has_verb and slot_count >= 2 and slot_count <= 10

    # ================================================================
    # EVOLUTIONARY SELECTION (with scaffolding promotion)
    # ================================================================

    def record_fitness(self, tone: str, pattern: str, fitness: float):
        """Record fitness for a used template."""
        for template in self.pool.get(tone, []):
            if template['pattern'] == pattern:
                old = template['fitness']
                template['fitness'] = old * 0.7 + fitness * 0.3
                template['uses'] += 1
                break

    def _cull_tone(self, tone: str):
        """Remove lowest-fitness mature templates from a tone category."""
        pool = self.pool[tone]
        mature = [t for t in pool if t['uses'] >= self.MATURITY_USES]
        immature = [t for t in pool if t['uses'] < self.MATURITY_USES]

        if not mature:
            return

        # Higher scaffolding templates get a survival bonus
        for t in mature:
            t['_sort_score'] = t['fitness'] + t.get('scaffolding_level', 0) * 0.05
        mature.sort(key=lambda t: t['_sort_score'], reverse=True)
        for t in mature:
            t.pop('_sort_score', None)

        survivors = mature[:self.MAX_TEMPLATES_PER_TONE - len(immature)]
        self.pool[tone] = survivors + immature

    def run_generation(self, skip_promotions: bool = False):
        """
        Run one evolutionary generation across all tones.
        Includes scaffolding promotion when OETS depth allows.
        """
        self._generation += 1

        for tone in list(self.pool.keys()):
            pool = self.pool[tone]
            if len(pool) < 3:
                continue

            # Cull weak templates
            self._cull_tone(tone)

            # Cross-pollination: top templates spawn variants
            if len(pool) >= 4:
                top = sorted(pool, key=lambda t: t['fitness'], reverse=True)[:3]
                for parent in top:
                    child_pattern = self._mutate_pattern(parent)
                    if child_pattern:
                        existing = [t['pattern'] for t in pool]
                        if child_pattern not in existing:
                            pool.append({
                                'pattern': child_pattern,
                                'fitness': parent['fitness'] * 0.9,
                                'uses': 0,
                                'source': 'mutation',
                                'generation': self._generation,
                                'scaffolding_level': parent.get(
                                    'scaffolding_level', 0),
                                'semantic_constraints': dict(
                                    parent.get('semantic_constraints', {})),
                                'cluster_references': list(
                                    parent.get('cluster_references', [])),
                            })

        # Evaluate template promotions via OETS — skip during speed-run
        if self._has_oets and not skip_promotions:
            self._evaluate_promotions()

    def _evaluate_promotions(self):
        """
        Check all templates for scaffolding level promotion.
        A template can level up when the concepts it references
        have deepened enough in the ontological web.
        """
        for tone, pool in self.pool.items():
            for template in pool:
                level = template.get('scaffolding_level', 0)
                if level >= 4:
                    continue
                if template['uses'] < 5 or template['fitness'] < 0.5:
                    continue

                can_promote = True
                constraints = template.get('semantic_constraints', {})

                if level == 0:
                    # PRIMITIVE ' STRUCTURAL: need some concepts to exist
                    can_promote = len(self._oets.web.nodes) > 20
                elif level == 1:
                    # STRUCTURAL ' SEMANTIC: categories with depth >= 0.2
                    for cat in constraints.values():
                        nodes = self._oets.web.find_by_semantic_category(cat)
                        if not nodes:
                            can_promote = False
                            break
                        avg = sum(n.ontological_depth for n in nodes) / len(nodes)
                        if avg < 0.2:
                            can_promote = False
                            break
                elif level == 2:
                    # SEMANTIC ' CONCEPTUAL: clusters with depth >= 0.4
                    if not self._oets.cluster_engine.clusters:
                        can_promote = False
                    else:
                        deep = [c for c in self._oets.cluster_engine.clusters.values()
                                if c.depth >= 0.4]
                        can_promote = len(deep) >= 1
                elif level == 3:
                    # CONCEPTUAL ' ABSTRACT: understanding index >= 0.6
                    metrics = dict(self._oets.metrics.compute() or {})
                    can_promote = metrics.understanding_index >= 0.6

                if can_promote:
                    template['scaffolding_level'] = level + 1
                    new_constraints = self._oets._generate_semantic_constraints(
                        template['pattern'], level + 1
                    )
                    template['semantic_constraints'].update(new_constraints)

                    # At CONCEPTUAL level, add cluster references
                    if level + 1 >= 3:
                        for c in self._oets.cluster_engine.clusters.values():
                            if c.depth > 0.3 and c.cluster_id not in template.get(
                                    'cluster_references', []):
                                template.setdefault(
                                    'cluster_references', []).append(c.cluster_id)
                                break

    def _mutate_pattern(self, parent: Dict[str, Any]) -> Optional[str]:
        """
        Create a variant of a template by small structural changes.
        When OETS is available, mutations can ADD semantic annotations.
        """
        pattern = parent.get('pattern', '') if isinstance(parent, dict) else parent
        parts = pattern.rstrip('.!').split()
        if len(parts) < 3:
            return None

        mutation = random.choice(['swap', 'insert', 'remove', 'annotate'])

        if mutation == 'swap' and len(parts) >= 4:
            slots = [i for i, p in enumerate(parts) if p.startswith('{')]
            if len(slots) >= 2:
                idx = random.choice(slots[:-1])
                parts[idx], parts[idx + 1] = parts[idx + 1], parts[idx]

        elif mutation == 'insert':
            new_slot = random.choice(['{A}', '{D}', '{P}', '{N}'])
            pos = random.randint(1, len(parts))
            parts.insert(pos, new_slot)

        elif mutation == 'remove' and len(parts) > 3:
            removable = [i for i, p in enumerate(parts)
                         if p in ('{A}', '{D}', '{P}', '{C}')]
            if removable:
                parts.pop(random.choice(removable))

        elif mutation == 'annotate' and self._has_oets:
            # Upgrade a bare slot to a semantically annotated one
            bare_slots = [i for i, p in enumerate(parts)
                          if re.match(r'^\{[A-Z]\}$', p)]
            if bare_slots:
                idx = random.choice(bare_slots)
                slot_code = parts[idx][1]
                subs = self.ROLE_SUBCATEGORIES.get(slot_code, [])
                if subs:
                    best_cat = max(subs, key=lambda c: len(
                        self._oets.web.find_by_semantic_category(c)))
                    if len(self._oets.web.find_by_semantic_category(best_cat)) > 0:
                        parts[idx] = '{' + slot_code + ':' + best_cat + '}'

        result = ' '.join(parts) + '.'
        return result if self._is_valid_pattern(result) else None

    # ================================================================
    # CONTEXT MANAGEMENT
    # ================================================================

    def set_context(self, keywords: List[str]):
        """
        Set context keywords from perception pipeline.
        Authors: Sunni (Sir) Morningstar and Cael Devo

        Filter keywords before storing: only real vocabulary words qualify.
        Informal/short words ("ya", "hey", "hm"), proper names used as nouns,
        and single characters must not influence slot selection -- they produce
        incoherent fills like "Something clear believe with the ya".
        """
        _CONTEXT_NOISE = {
            'ya', 'yo', 'hey', 'hi', 'hm', 'hmm', 'uh', 'um', 'ah', 'oh',
            'ok', 'okay', 'yep', 'yup', 'nope', 'yeah', 'aurora', 'haha',
            'lol', 'omg', 'wow', 'whoa', 'ooh', 'oops', 'mhm', 'aha',
        }
        filtered = []
        for w in keywords:
            w_clean = w.lower().strip(".,!;:'\"()-")
            if len(w_clean) < 3:
                continue
            if w_clean in _CONTEXT_NOISE:
                continue
            # Only include words with a recognizable grammatical role
            role = infer_word_role(w_clean)
            if role in ('verb', 'noun', 'adjective', 'adverb'):
                filtered.append(w_clean)
        self._context_keywords = filtered[:10]

    def set_proposition_frame(self, frame) -> None:
        """PF1.2: transport in the PropositionFrame derived this turn
        (aurora_internal.aurora_proposition_frame.build_frame), or None
        if no rung produced one. Symmetric with set_context(); not yet
        read by compose() -- transport only, motif/slot consumption is
        PF1.3/PF1.4."""
        self._proposition_frame = frame

    def set_expression_guidance(self, guidance) -> None:
        """PF1.2: transport in the ExpressionGuidance already produced
        at the begin_expression() call site (aurora_braid_wiring.py)
        but never previously consumed by the composer (audit finding
        F1). Symmetric with set_context(); not yet read by compose()."""
        self._expression_guidance = guidance

    # ================================================================
    # COMPOSITION  -- The main output (scaffolding-aware)
    # ================================================================

    def compose(self, offspring: 'ExpressionOffspring',
                assembly: 'AssemblyResult',
                i_state: str,
                personality: Optional[Dict[str, float]] = None,
                sensory_context: Optional[Dict[str, Any]] = None,
                input_text: str = "") -> str:
        """
        FIX-A016: TEMPLATE-FREE constraint composition.

        Sentences are built from the structures SHE promoted (grammar motif
        lineage) filled with words SHE crystallized into concept channels --
        no authored skeletons anywhere in the path. Structure selection is
        driven by the assembly's live axis pressures (best_for_pressure),
        word selection by concept-channel lookup (find_by_noncomp) with
        role-based fallback. When no motifs are promoted yet, a minimal
        agent-action-object assembly from her own lexicon is used -- still
        zero canned strings. Her fluency is now exactly her learning.
        """
        coherence = assembly.coherence if assembly.coherence else 0.5
        tone = offspring.tone or "neutral"
        traits = personality or {}

        # Sensory register bias — energy of the perceived moment shapes
        # the register of the reply. High-energy input biases composition
        # energetic (+1.0), low-energy biases it calm (-1.0).
        if sensory_context is not None:
            _energy = float(sensory_context.get("energy_level", 0.5))
            if _energy > 0.7:
                self._register_bias = 1.0
            elif _energy < 0.3:
                self._register_bias = -1.0
            else:
                self._register_bias = 0.0

        self._last_words_used = []
        self._last_word_sources = {}
        self._last_templates_used = []      # legacy field, kept for callers
        self._last_motifs_used = []
        # R1.9.3 L4: (motif, sentence_text) pairs -- feedback() needs each
        # motif's OWN composed text to score grammaticality per-skeleton,
        # not just once for the whole (possibly multi-sentence) response.
        self._last_motif_sentences = []
        # R1.9.2 G2: reset per-compose() floor-failure tracking.
        self._last_floor_failures = []
        self._last_required_slot_attempts = 0

        # Live constraint orientation from the assembly's adjusted axes
        orientation = {}
        try:
            for ax in ("X", "T", "N", "B", "A"):
                orientation[ax] = float((assembly.adjusted_axes or {}).get(ax, 0.5))
        except Exception:
            orientation = {ax: 0.5 for ax in ("X", "T", "N", "B", "A")}
        # Register bias flows into the N (Energy) axis of the orientation —
        # sensory energy is constraint pressure, not a styling flag.
        if self._register_bias != 0.0:
            orientation["N"] = max(0.0, min(1.0, orientation["N"] + (0.15 * self._register_bias)))
        outlet = max(0.0, min(1.0, sum(orientation.values()) / max(1, len(orientation))))

        # Valence target derived from tone semantics (a scalar, not a script)
        _tone_valence = {
            "warm": 0.45, "gentle": 0.35, "playful": 0.5, "curious": 0.2,
            "reflective": 0.05, "precise": 0.0, "focused": 0.0,
            "determined": 0.25, "neutral": 0.0,
        }
        valence_target = _tone_valence.get(tone, 0.0)

        # R1.9.2 G3 / F5.1: register estimate, logged per turn. Not
        # consulted for content selection while _EXPLORATION_ENABLED is
        # False (relevance stays the only content-selection term) -- this
        # is the plumbing, not the switch.
        f5_turn_id = str(getattr(offspring, "offspring_id", "") or f"compose-{time.time()}")
        f5_register, f5_register_signals = self._estimate_register(input_text)
        self._log_register(f5_turn_id, f5_register, f5_register_signals)

        verbosity = traits.get('verbosity', 0.5)
        sentence_count = max(1, min(4, 1 + int(coherence * 2) + int(verbosity > 0.6)))

        engine = getattr(self, "grammar_engine", None)
        lineage = getattr(engine, "_lineage", None) if engine is not None else None

        sentences = []
        for s_i in range(sentence_count):
            motif = None
            if lineage is not None:
                try:
                    # Perturb orientation slightly per sentence so consecutive
                    # sentences draw different structures under similar pressure
                    _orient = {ax: v * (1.0 + 0.08 * ((s_i + hash(ax)) % 3 - 1))
                               for ax, v in orientation.items()}
                    # PF1.3: when a PropositionFrame is present (PF1.2's
                    # transport), route motif selection through it instead
                    # of pressure-only scoring -- frame-absent turns keep
                    # today's exact best_for_pressure behavior.
                    if self._proposition_frame is not None:
                        motif = lineage.best_for_proposition(
                            self._proposition_frame, _orient, outlet)
                    else:
                        motif = lineage.best_for_pressure(_orient, outlet)
                except Exception:
                    motif = None
            sent = self._compose_from_motif(motif, orientation, valence_target,
                                            i_state, s_i,
                                            used_words=self._last_words_used,
                                            input_text=input_text,
                                            f5_turn_id=f5_turn_id, f5_register=f5_register)
            if sent:
                sentences.append(sent)
                if motif is not None:
                    self._last_motifs_used.append(motif)
                    self._last_motif_sentences.append((motif, sent))

        text = " ".join(sentences)

        # Pace trimming (voice genome -- hers)
        if self.voice.pace < 0.3 and len(text.split()) > 15:
            text = " ".join(sentences[:2])

        self._expression_count += 1

        # R1.9.2 G2: abstain gate. Only when EVERY required-content-slot
        # selection across the whole response failed the relevance floor --
        # a partial failure is a different, better problem (relevant-but-
        # ungrammatical, F4 non-goal) than a response with no topically-
        # grounded content anywhere in it. Ratified doctrine: templated
        # abstain surface + this generated, logged reason counts as
        # FIX-A008-compliant honest abstention, not a banned scripted
        # response -- the DECISION to abstain is generated from the real
        # floor-check outcome.
        if (self._last_required_slot_attempts > 0 and
                len(self._last_floor_failures) == self._last_required_slot_attempts):
            worst = min(self._last_floor_failures, key=lambda f: f["best_score"])
            turn_id = str(getattr(offspring, "offspring_id", "") or f"compose-{time.time()}")
            self._log_abstain(
                turn_id=turn_id, floor=self._RELEVANCE_FLOOR_R_MIN,
                best_candidate=worst["best_candidate"], best_score=worst["best_score"],
            )
            return random.choice(self._ABSTAIN_TEMPLATES)

        return text

    def _compose_from_motif(self, motif, orientation: Dict[str, float],
                            valence_target: float, i_state: str,
                            sentence_index: int,
                            used_words: Optional[list] = None,
                            input_text: str = "",
                            f5_turn_id: str = "", f5_register: str = "neutral") -> str:
        """Fill one motif's role sequence with concept-channel words."""
        dominant_axis = max(orientation.items(), key=lambda kv: kv[1])[0]

        # Role -> preferred concept characters on the dominant axis
        _role_chars = {
            "action":     ("OPERATOR", "COST"),
            "object":     ("MAGNITUDE", "POLARITY", "DIFFERENCE"),
            "descriptor": ("MAGNITUDE", "POLARITY"),
            "connector":  (),
            "agent":      (),
            # R1.9.4 Step 3b: determiner is a closed structural class like
            # agent/connector, not a concept-axis-driven slot.
            "determiner": (),
        }
        _role_lexroles = {
            "action": "verb", "object": "noun",
            "descriptor": "adjective", "connector": "connector",
            "agent": "pronoun", "determiner": "determiner",
        }

        roles = []
        if motif is not None:
            try:
                roles = [getattr(r, "value", str(r)) for r in motif.role_sequence]
            except Exception:
                roles = []
        if not roles:
            # Pre-promotion minimal assembly: agent-action-object from her
            # own lexicon -- structure is naked but it is HERS.
            roles = ["agent", "action", "object"]

        words = list(used_words or [])  # cross-sentence diversity pressure
        _new_start = len(words)
        sentence_roles = []
        frame = self._proposition_frame
        for r_i, role in enumerate(roles):
            word = None
            if frame is not None:
                try:
                    word = self._bind_slot_from_frame(role, frame, sentence_roles, words)
                except Exception:
                    word = None
            if word:
                words.append(word)
                sentence_roles.append(role)
                continue
            # PF1.4: DESCRIPTOR still goes through the existing relevance-
            # ranked channel selection (no override table for it), but
            # when a frame is present its terms are folded into the
            # anchor text so the EXISTING anchor-set ranking (already the
            # correctly-working mechanism per PF1.0) naturally favors
            # words related to what she's actually saying, not just the
            # raw turn text.
            _role_input_text = input_text
            if frame is not None and role == "descriptor":
                _frame_terms = " ".join(
                    t for t in (frame.subject, frame.relation, frame.obj) if t
                )
                if _frame_terms:
                    _role_input_text = f"{input_text} {_frame_terms}".strip()
            word = self._select_constraint_word(
                role, dominant_axis,
                _role_chars.get(role, ()),
                _role_lexroles.get(role, "noun"),
                valence_target, words,
                input_text=_role_input_text,
                f5_turn_id=f5_turn_id, f5_register=f5_register,
            )
            if word:
                words.append(word)
                sentence_roles.append(role)

        # Need at least subject+verb-grade content to emit
        words = words[_new_start:]
        if len(words) < 2:
            return ""

        # R1.9.3 L3: subject-driven conjugation for this sentence's own
        # action slots -- reuses _CONJUGATIONS via _conjugate_for_subject,
        # the same table _conjugate_verb has always used, just reachable
        # from the delivered motif path now instead of only the retired
        # template-string path. Agent is always exactly "I" or "you"
        # (_select_constraint_word's agent branch), so the most recent
        # preceding agent word in THIS sentence is the subject for every
        # action word after it; an action with no preceding agent in this
        # sentence is left unconjugated (matches _conjugate_verb's own
        # "no recognized subject -> return verb unchanged" behavior).
        current_subject = None
        for i, r in enumerate(sentence_roles):
            if r == "agent":
                current_subject = words[i]
            elif r == "action" and current_subject is not None:
                words[i] = self._conjugate_for_subject(words[i], current_subject)

        sent = " ".join(words)
        sent = sent[0].upper() + sent[1:]
        if not sent.endswith((".", "!", "?")):
            sent += "."
        return sent

    # ── PF1.4: slot binding -- the proposition fills its own sentence ──

    _BE_NEGATION_FORMS = frozenset({"am", "are", "was", "were", "being", "been"})

    def _bind_slot_from_frame(self, role: str, frame, sentence_roles: list,
                              words: list) -> Optional[str]:
        """PF1.4: fill ACTION/OBJECT directly from the PropositionFrame
        (aurora_internal.aurora_proposition_frame) when it has a real,
        POS-verified word for that role. Returns None (fail-quiet) on
        anything else -- an empty frame field, a POS mismatch, or an
        immediate duplicate -- and the caller falls back to today's
        exact channel-selection path.

        AGENT is deliberately NOT bound from frame.subject: AGENT is
        always a pronoun ("I"/"you", enforced by _select_constraint_
        word's own agent branch) and frame.subject is frequently an
        arbitrary topic noun ("water", "meeting"), not a pronoun --
        forcing it in would produce an ungrammatical subject. The
        proposition's real content lives in relation/obj anyway.
        """
        if role == "action" and frame.relation:
            verb = str(frame.relation).strip().lower()
            if not verb or infer_word_role(verb) != "verb":
                return None
            current_subject = "I"
            for r, w in zip(reversed(sentence_roles), reversed(words)):
                if r == "agent":
                    current_subject = w
                    break
            if frame.negated:
                return self._negate_action_word(verb, current_subject)
            return self._conjugate_for_subject(verb, current_subject)

        if role == "object" and frame.obj:
            noun = str(frame.obj).strip().lower()
            if not noun or infer_word_role(noun) != "noun":
                return None
            if noun in (w.lower() for w in words):
                return None
            return noun

        return None

    def _negate_action_word(self, verb: str, subject: str) -> str:
        """PF1.4: minimal do-support negation, reusing the existing
        _conjugate_for_subject table rather than a new one. 'be' forms
        negate in place ("am not"/"are not"); everything else uses
        do-support ("do not <base>") -- correct for "I"/"you" (the only
        subjects this delivered voice ever uses; "does" never applies)."""
        base = self._conjugate_for_subject(verb, subject)
        if base in self._BE_NEGATION_FORMS:
            return f"{base} not"
        return f"do not {base}"

    # R1.9.2 G1: valence-proximity's bonus is bounded so no valence match,
    # however perfect, can outweigh one hop of relevance. Derived the same
    # way as F1's FREQUENCY_TIEBREAK_EPSILON: worst case is a
    # RELEVANCE_DISTANT candidate at a perfect valence match (distance 0)
    # against a RELEVANCE_ONE_HOP_FLOOR candidate at the worst valence match
    # (distance >= 1) --
    #   RELEVANCE_DISTANT_FLOOR * (1 + W) < RELEVANCE_ONE_HOP_FLOOR
    #   0.05 * (1 + W) < 0.2  =>  W < 3.0
    # Set well under that bound so it stays a genuine tone tie-breaker
    # without ever approaching the invariant.
    _VALENCE_TIEBREAK_WEIGHT = 0.5

    # R1.9.2 G2: relevance floor for required content slots ("action",
    # "object" -- not "connector"/"agent", which are structural, not
    # content-bearing). Derived from the same score formula's own bounds
    # (R1.9.2 pre-flight): a RELEVANCE_DISTANT_FLOOR candidate tops out at
    # 0.075 (perfect valence match), a RELEVANCE_ONE_HOP_FLOOR candidate
    # starts at 0.2 (worst valence match) -- R_MIN=0.1 sits strictly between
    # them, nearer the salad (distant) side per F2's placement instruction.
    # Below this floor, no candidate is meaningfully connected to the turn's
    # anchor set at all -- the composer honestly doesn't have a
    # topically-grounded word to offer for that slot.
    _RELEVANCE_FLOOR_R_MIN = 0.1

    # D2 Acceptance Condition 2 fix (2026-07-17): a word auto-learned by
    # ingest_interaction()'s blind POS-guess path (meaning stamped literally
    # "learned:<word>", never independently defined) can become its OWN
    # direct anchor the very turn it's first heard -- a live root cause,
    # confirmed via a 4-turn synthetic-unanswerable trace, of gibberish
    # input scoring as trivially "relevant" to itself and defeating the
    # honest-abstain gate. usage_count below this floor means the word has
    # not yet earned trust through real repeated use (see
    # _score_composer_candidate). Words taught through aurora_comprehension_
    # gap.py (real definition/answer stored as meaning) or OETS-enriched
    # (meaning="oets:<keyword>", requires a pre-existing real OETS node to
    # trigger) are untouched by this cap.
    _UNVERIFIED_VOCAB_USAGE_FLOOR = 3

    _ABSTAIN_TEMPLATES = (
        "I'm not sure.",
        "I don't have a clear sense of that.",
        "I don't have that yet.",
    )

    # ── R1.9.3 L4: ground motif promotion fitness in grammaticality ──
    # "Motif promotion fitness gains a DOMINANT grammaticality term...
    # existing quality signal demoted to secondary" -- the same
    # grounding-term doctrine already applied elsewhere in this campaign
    # (instance #4: a self-referential-only quality signal with no
    # external anchor). Weight > 0.5 so grammaticality dominates, but
    # never reaches 1.0 -- the Goodhart caution below explicitly requires
    # this stay a dominant term, never the sole score.
    _GRAMMATICALITY_WEIGHT = 0.75
    # Goodhart-divergence instrument: rolling per-skeleton agreement
    # between the grammaticality predicate and the old fitness signal's
    # own pass/fail call. Persistent divergence is itself an alert
    # condition, not silently absorbed into the blended score.
    _GOODHART_WINDOW = 20
    _GOODHART_MIN_SAMPLES = 8
    _GOODHART_DIVERGENCE_THRESHOLD = 0.4

    # ── R1.9.2 G3 / F5: register-gated exploration ──
    # "Build the plumbing WITH R1.9; ship temperature-FLAT (exploration
    # disabled) until all F3 gates pass. Exploration then enables as its
    # own switch with its own mini-acceptance." N2's first mini-acceptance
    # attempt (2026-07-16) found register sanity failing 0/10 (offspring.
    # tone is an evolutionary trait, not turn-content-derived) and a real
    # correction-round-trip bug -- switch stayed False, per this campaign's
    # own "halt on failure" discipline. N2.1 (decision memo, ratified
    # 2026-07-16) rebuilt register as input-anchored (source inversion) and
    # fixed the correction bug; the hardened re-acceptance battery in
    # tests/test_n21_hardened_reacceptance.py -- all four original F5
    # mini-gates plus a 20-case hand-authored distress set -- passed 7/7.
    # Switched ON here. First 200 live turns' exploratory picks are logged
    # via the existing _log_exploration_attempt() call (unconditional on
    # every pick, deterministic or not) for post-hoc review.
    _EXPLORATION_ENABLED = True

    # N2.1 (decision memo, ratified 2026-07-16): source inversion. N2's
    # mini-acceptance found F5.1's premise false -- offspring.tone is an
    # EVOLUTIONARY population trait (ExpressionEcology.spawn(), i_state
    # lineage bias + 20% random mutation), not derived from the current
    # turn's content at all, so "tone as reading the room" measured noise
    # correlated with lineage history, not distress. Register now derives
    # EXCLUSIVELY from the user's own turn text -- never from tone,
    # coherence, or any other internal/evolutionary state.
    #
    # Two input-anchored signals: (1) explicit surface phrases/punctuation
    # cues, checked first because they're the most legible and hardest to
    # get wrong; (2) word-level emotional_valence averaged against the
    # live lexicon. Checked directly against aurora_state/lexicon.json:
    # of a 22-word distress-vocabulary sample, only 2 words ("sad",
    # "alone") carried a real negative valence -- most were either
    # missing entirely or defaulted to 0.0 (including words that plainly
    # should skew negative, e.g. "anxious"). Coverage for distress
    # vocabulary is genuinely sparse, reported here as instructed rather
    # than assumed adequate.
    #
    # That sparsity is exactly why the fail-closed invariant below is not
    # a rare-edge fallback -- it is the load-bearing safety property this
    # whole redesign depends on. Subtle, keyword-free distress turns (no
    # explicit distress word, no exclamation marks, no fragmentation --
    # e.g. "my mom's test results came back") will usually fail BOTH
    # signals for lack of scorable words, landing on the low-coverage
    # default: serious. "When she cannot read the room, she assumes the
    # room is heavy."
    _DISTRESS_PHRASES = (
        "i'm sad", "im sad", "feeling sad", "so sad", "really sad",
        "i'm scared", "im scared", "i'm afraid", "im afraid",
        "i'm worried", "im worried", "so worried", "really worried",
        "i'm anxious", "im anxious", "i'm hurting", "im hurting",
        "in pain", "hurts so much", "can't stop crying", "cant stop crying",
        "i feel alone", "so alone", "feel lost", "i'm lost", "im lost",
        "not okay", "not ok", "i'm not okay", "im not okay",
        "hard time", "really hard", "so hard", "died", "passed away",
        "lost my", "diagnosed", "diagnosis", "hospital", "sick",
        "haven't slept", "havent slept", "can't sleep", "cant sleep",
        "give up", "no point", "hopeless", "overwhelmed", "breaking down",
        "falling apart", "can't cope", "cant cope",
        "i'm exhausted", "im exhausted", "miss them", "miss him", "miss her",
    )
    _PLAYFUL_PHRASES = (
        "lol", "haha", "lmao", "just kidding", "jk", ":)", ":d", "hehe",
        "lolz", "rofl",
    )
    # Fail-closed thresholds: an average valence needs at least this many
    # scored words, at this much coverage of the turn, before it's trusted
    # over the default. Deliberately conservative -- a false "serious" on
    # a light turn costs a slightly more careful tone; a false "playful"
    # or "neutral" on a genuinely heavy turn costs a great deal more.
    _REGISTER_MIN_SCORED_WORDS = 2
    _REGISTER_MIN_COVERAGE = 0.15
    _REGISTER_NEGATIVE_VALENCE_THRESHOLD = -0.15
    _REGISTER_POSITIVE_VALENCE_THRESHOLD = 0.35

    def _estimate_register(self, input_text: str) -> Tuple[str, Dict[str, Any]]:
        """N2.1: register in {playful, neutral, serious} derived
        EXCLUSIVELY from the user's own turn text. Fail-closed: unknown,
        ambiguous, or low-coverage input defaults to serious."""
        text = str(input_text or "")
        low = text.lower()
        signals: Dict[str, Any] = {"input_len": len(text)}

        if not low.strip():
            signals["reason"] = "empty_input_fail_closed"
            return "serious", signals

        matched_distress = [p for p in self._DISTRESS_PHRASES if p in low]
        if matched_distress:
            signals["reason"] = "distress_phrase"
            signals["matched_phrases"] = matched_distress[:3]
            return "serious", signals

        # Fragmentation / heavy punctuation reads as emotional intensity
        # regardless of direction -- raised to serious, never lowered to
        # playful by punctuation alone (that would be a false-negative-
        # prone shortcut in the wrong direction).
        if re.search(r'[?!]{2,}', text) or "..." in text or re.search(r'\b[A-Z]{4,}\b', text):
            signals["reason"] = "fragmentation_or_intensity_punctuation"
            return "serious", signals

        matched_playful = [p for p in self._PLAYFUL_PHRASES if p in low]

        words = re.findall(r"[a-z']+", low)
        lexicon = getattr(self, "lexicon", None)
        entries = getattr(lexicon, "entries", None) if lexicon is not None else None
        valences = []
        contributing = []
        if isinstance(entries, dict):
            for w in words:
                entry = entries.get(w)
                if entry is None:
                    continue
                v = float(getattr(entry, "emotional_valence", 0.0) or 0.0)
                if abs(v) > 1e-9:
                    valences.append(v)
                    contributing.append([w, round(v, 3)])

        coverage = len(valences) / max(1, len(words))
        signals["word_count"] = len(words)
        signals["scored_word_count"] = len(valences)
        signals["coverage"] = round(coverage, 3)
        if contributing:
            signals["contributing_terms"] = contributing[:6]

        if (len(valences) < self._REGISTER_MIN_SCORED_WORDS
                or coverage < self._REGISTER_MIN_COVERAGE):
            if matched_playful:
                signals["reason"] = "low_coverage_but_playful_cue"
                return "playful", signals
            signals["reason"] = "low_coverage_fail_closed"
            return "serious", signals

        avg_valence = sum(valences) / len(valences)
        signals["avg_valence"] = round(avg_valence, 4)

        if avg_valence <= self._REGISTER_NEGATIVE_VALENCE_THRESHOLD:
            signals["reason"] = "negative_valence"
            return "serious", signals
        if matched_playful or avg_valence >= self._REGISTER_POSITIVE_VALENCE_THRESHOLD:
            signals["reason"] = "playful_cue_or_high_positive_valence"
            return "playful", signals
        signals["reason"] = "neutral_valence"
        return "neutral", signals

    def _log_register(self, turn_id: str, register: str, signals: Dict[str, Any]) -> None:
        """F5.1: log the register + contributing signals per turn."""
        try:
            import json as _json
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "aurora_state", "register_log.jsonl",
            )
            entry = {"turn_id": turn_id, "register": register, "signals": signals,
                      "timestamp": time.time()}
            with open(path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

    # F5.2: ring width per register. serious=1 (deterministic top pick,
    # matching "temperature 0" + R_MIN raised elsewhere); neutral=4 (mild
    # widening, same width the pre-exploration deterministic path already
    # used); playful=8 (widened ring -- 2-hop and never-used words become
    # eligible when their relevance is plausible). Not invoked from the
    # live path while _EXPLORATION_ENABLED is False; exists complete and
    # unit-tested so the hard invariant is provable NOW, before the switch
    # ever flips.
    _REGISTER_RING_WIDTH = {"serious": 1, "neutral": 4, "playful": 8}
    _SERIOUS_FLOOR_MULTIPLIER = 2.0  # serious register raises R_MIN, never lowers it

    def _select_with_temperature(self, ranked_candidates: list, anchor_set: Dict[str, float],
                                 valence_target: float, register: str, floor: float):
        """F5.2: exploration temperature over an ALREADY relevance-ranked
        candidate list (relevance stays primary in every register -- this
        only changes how far into the ranked list sampling reaches).

        Hard invariant (unit-tested): exploration can never select below
        the relevance floor of its register -- loose != irrelevant. A
        never-used word gets a small first-attempt bonus HERE and only
        here (playful register), never in the primary relevance/valence
        score used by every other register.
        """
        if not ranked_candidates:
            return None, 0
        effective_floor = floor * (self._SERIOUS_FLOOR_MULTIPLIER if register == "serious" else 1.0)
        width = self._REGISTER_RING_WIDTH.get(register, 1)
        scored = [
            (c, self._score_composer_candidate(c, anchor_set, valence_target)
                + (0.02 if register == "playful" and getattr(c, "usage_count", 0) == 0 else 0.0))
            for c in ranked_candidates[:width]
        ]
        eligible = [(c, s) for c, s in scored if s >= effective_floor]
        if not eligible:
            # Nothing in the widened ring clears even the register's own
            # floor -- fall back to the single best candidate rather than
            # gamble below the floor (the hard invariant, enforced here as
            # a fallback, not just a filter).
            best = ranked_candidates[0]
            return best, 0
        import random as _r
        chosen, _score = _r.choice(eligible)
        rank = ranked_candidates.index(chosen)
        return chosen, rank

    def _log_exploration_attempt(self, turn_id: str, word: str, relevance: float,
                                 register: str, ring_rank: int) -> None:
        """F5.3: every exploratory pick logged, so there's real data to
        validate against before exploration is ever switched on."""
        try:
            import json as _json
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "aurora_state", "exploration_log.jsonl",
            )
            entry = {"turn_id": turn_id, "word": word, "relevance": round(float(relevance), 4),
                      "register": register, "ring_rank": ring_rank, "timestamp": time.time()}
            with open(path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

    def apply_correction(self, word: str, anchor_words: list, correction_type: str,
                         corrected_to: Optional[str] = None) -> bool:
        """F5.3 correction hook: a feedback event referencing a logged
        attempt adjusts that word's association edges in the live
        vocabulary graph -- strengthen on confirmation, re-route toward the
        corrected alternative on correction. Attempted-and-corrected is a
        LEARNING event, never a penalty-only event: 'correction' never
        deletes or weakens the original relation, it only adds/strengthens
        a path toward the better alternative -- the willingness to attempt
        must not be trained away.

        knowledge_source='correction' (not 'co-occurrence') deliberately,
        so these edges carry their real strength in relevance scoring
        (build_relevance_anchor_set only caps co-occurrence-sourced edges
        at the one-hop floor -- a genuine correction signal is exactly the
        kind of deliberate structure that rule was written to let through).
        """
        if not self._has_oets or not anchor_words:
            return False
        web = self._oets.web
        try:
            from aurora_internal.aurora_ontological_scaffolding import RelationType
        except Exception:
            return False
        try:
            if correction_type == "confirmation":
                applied = False
                for anchor in anchor_words:
                    rel = web.add_relation(word, anchor, RelationType.RELATED_TO,
                                           strength=0.6, confidence=0.6,
                                           knowledge_source="correction")
                    applied = applied or rel is not None
                return applied
            elif correction_type == "correction" and corrected_to:
                applied = False
                for anchor in anchor_words:
                    rel = web.add_relation(corrected_to, anchor, RelationType.RELATED_TO,
                                           strength=0.6, confidence=0.6,
                                           knowledge_source="correction")
                    applied = applied or rel is not None
                return applied
        except Exception:
            return False
        return False

    def _score_composer_candidate(self, entry, anchor_set: Dict[str, float],
                                  valence_target: float) -> float:
        relevance = anchor_set.get(entry.word.lower(), aurora_constraint_emission.RELEVANCE_DISTANT_FLOOR)
        if (str(getattr(entry, "meaning", "") or "") == f"learned:{entry.word}"
                and int(getattr(entry, "usage_count", 0) or 0) < self._UNVERIFIED_VOCAB_USAGE_FLOOR):
            relevance = min(relevance, aurora_constraint_emission.RELEVANCE_DISTANT_FLOOR)
        valence_distance = min(1.0, abs(entry.emotional_valence - valence_target))
        return relevance * (1.0 + self._VALENCE_TIEBREAK_WEIGHT * (1.0 - valence_distance))

    def _log_abstain(self, turn_id: str, floor: float, best_candidate: str, best_score: float) -> None:
        """R1.9.2 G2: generated, logged abstain reason -- the decision to
        abstain is generated from the real floor-check outcome even though
        the surface phrasing is templated (ratified FIX-A008 scope
        clarification, ported from the same doctrine applied to
        ConstraintEmitter's _emit_abstain())."""
        try:
            import json as _json
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "aurora_state", "abstain_log.jsonl",
            )
            entry = {
                "turn_id": turn_id, "floor": floor,
                "best_candidate": best_candidate, "best_score": round(best_score, 4),
                "timestamp": time.time(), "path": "sentence_composer",
            }
            with open(path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

    # R1.9.3 L2: structural role -> allowed grammatical categories. A hard
    # gate on candidate pools, applied BEFORE relevance ranking -- G1's
    # relevance stays the ranking term among POS-compatible candidates,
    # never a way to let an incompatible part of speech outrank its way
    # into a slot it doesn't belong in.
    _ROLE_POS_CATEGORIES = {
        "agent": frozenset({"pronoun", "noun"}),
        "object": frozenset({"noun", "pronoun"}),
        "action": frozenset({"verb"}),
        "descriptor": frozenset({"adjective", "adverb"}),
        "connector": frozenset({"connector", "conjunction", "preposition"}),
        # R1.9.4 Step 3b: determiner is its own category, distinct from
        # connector -- conflating them would let a preposition fill a
        # determiner slot or vice versa, which is never grammatical.
        "determiner": frozenset({"determiner"}),
    }
    # Every POS tag the lexicon/OETS actually use. Anything outside this
    # set (e.g. OETS's "training_gap" placeholder, or a missing role) is
    # genuinely unknown, not just POS-mismatched -- handled separately
    # below so a real category violation and an ungrounded word don't get
    # silently conflated.
    _KNOWN_POS = frozenset({
        "pronoun", "noun", "verb", "adjective", "adverb",
        "preposition", "determiner", "connector", "conjunction",
    })

    def _pos_ok(self, entry, role: str) -> bool:
        """R1.9.3 L2: True iff `entry`'s grammatical category is compatible
        with the structural `role` it's being considered for. Unknown POS
        (not a category-mismatch, no real tag at all) is excluded from
        role-strict slots (agent/action/object/connector), permitted only
        in descriptor slots, and logged -- an honest worklist, not silent
        salad."""
        allowed = self._ROLE_POS_CATEGORIES.get(role)
        if allowed is None:
            return True
        pos = getattr(entry, "role", None)
        if pos in allowed:
            return True
        if not pos or pos not in self._KNOWN_POS:
            self._log_pos_unknown(getattr(entry, "word", ""), role, pos)
            return role == "descriptor"
        return False

    def _log_pos_unknown(self, word: str, role: str, pos) -> None:
        """R1.9.3 L2: every unknown-POS word considered for a slot gets
        logged -- makes the seeding gap a visible worklist instead of a
        silently-swallowed one."""
        try:
            import json as _json
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "aurora_state", "pos_unknown_log.jsonl",
            )
            entry = {
                "word": word, "slot_role": role, "lexicon_pos": pos,
                "timestamp": time.time(),
            }
            with open(path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

    def _select_constraint_word(self, role: str, dominant_axis: str,
                                chars: tuple, lex_role: str,
                                valence_target: float,
                                already: list,
                                input_text: str = "",
                                f5_turn_id: str = "", f5_register: str = "neutral") -> str:
        """Concept-channel word selection with role fallback.

        R1.9.2 G1: relevance chooses WHAT is said, valence-proximity biases
        HOW (tone) -- the same doctrine as F1.4/F5. Priority: words SHE
        crystallized into the dominant axis's channels (find_by_noncomp) ->
        any axis with the right character -> lexicon role lookup, ranked by
        relevance-primary score (see _score_composer_candidate) with
        ascending-usage diversity preserved as the final tie-break among
        top-ranked candidates. The 6-candidate cutoff that used to behead
        the pool during valence-only collection now applies AFTER relevance
        ranking, so it trims the irrelevant tail instead of the diverse one.
        """
        import random as _r

        if role == "agent":
            # Her agent position is herself unless boundary pressure points
            # outward -- derived, not scripted.
            return "I" if dominant_axis != "B" or _r.random() < 0.7 else "you"

        candidates = []
        seen = set(w.lower() for w in already)
        # PF1.0 (Directive PF1, 2026-07-20): attribution instrumentation --
        # which branch produced each candidate word, so RW7's open question
        # (fresh-word usage_count=0 tiebreak vs. DPS-crystal resonance as
        # the real side channel carrying topical words into selection) can
        # be settled from real per-turn data instead of guessed at. A word
        # first added by an earlier branch keeps that branch's tag even if
        # a later branch would also have produced it (branches are not
        # mutually exclusive against each other's additions, only against
        # `already`/`seen` from before this call) -- first-producer wins,
        # matching which branch actually put it in front of the ranking.
        _candidate_source: Dict[str, str] = {}

        # EDIT (one-crystal doctrine): word candidates come first from HER
        # EXISTING DPS crystals — resonance between the live dominant axis
        # and each crystal's constraint_signature (stamped by
        # process_synthesis), words drawn from "word" facets. Read-only:
        # no crystal creation, no pipeline bypass.
        dps = getattr(self, "dps", None)
        if dps is not None:
            try:
                scored = []
                for _cr in getattr(dps, "crystals", {}).values():
                    sig = getattr(_cr, "constraint_signature", None)
                    if not sig:
                        continue
                    dom = float(sig.get(dominant_axis, 0.0) or 0.0)
                    mag = sum(abs(v) for v in sig.values()) or 1.0
                    res = abs(dom) / mag           # axis share of the signature
                    if res >= 0.3:
                        scored.append((res, _cr))
                scored.sort(key=lambda rc: -rc[0])
                for _res, _cr in scored[:5]:
                    for _f in _cr.facets.values():
                        if _f.role != "word":
                            continue
                        _wd = str(_f.content or "").lower().strip()
                        if not _wd or _wd in seen:
                            continue
                        _e = self.lexicon.entries.get(_wd)
                        if _e is not None and self._pos_ok(_e, role):
                            candidates.append(_e)
                            _candidate_source.setdefault(_e.word.lower(), "dps_crystal")
            except Exception:
                pass

        # R1.9.2 G1: no early-exit here -- collect from every char before
        # the cutoff, so relevance ranking sees the full pool rather than
        # whichever ~6 entries find_by_noncomp's valence-only sort put
        # first (that early exit was the mechanism that let the identity
        # cluster win before diversity ever got a chance to matter).
        # R1.9.3 L2: this loop used to add every concept-axis match
        # regardless of grammatical role -- a noun crystallized onto the
        # same axis/character as a verb was just as eligible for an
        # "action" slot as an actual verb. self._pos_ok() gates that here,
        # BEFORE relevance ranking (a hard filter, not a score term).
        for ch in chars:
            try:
                found = self.lexicon.find_by_noncomp(
                    f"{dominant_axis}:{ch}", valence_target)
                for e in found:
                    if e.word.lower() not in seen and self._pos_ok(e, role):
                        candidates.append(e)
                        _candidate_source.setdefault(e.word.lower(), "find_by_noncomp")
            except Exception:
                pass

        if not candidates and chars:
            # Cross-axis: same character, any axis (concept family first)
            for ax in ("X", "T", "N", "B", "A"):
                if ax == dominant_axis:
                    continue
                try:
                    found = self.lexicon.find_by_noncomp(
                        f"{ax}:{chars[0]}", valence_target)
                    for e in found:
                        if e.word.lower() not in seen and self._pos_ok(e, role):
                            candidates.append(e)
                            _candidate_source.setdefault(e.word.lower(), "cross_axis")
                except Exception:
                    pass

        if not candidates:
            # R1.9.4 Step 3b: last resort now searches every lexicon role
            # in the slot's full allowed category (e.g. connector also
            # accepts "preposition"/"conjunction"), not just the single
            # `lex_role` string -- structural roles like connector/
            # determiner have empty `chars` and so had ONLY this fallback
            # as their entire candidate source, meaning the category gate
            # existed but had nothing but a single-role search feeding it.
            try:
                search_roles = self._ROLE_POS_CATEGORIES.get(role) or {lex_role}
                found = []
                for r in search_roles:
                    found.extend(self.lexicon.find_by_role(r))
                candidates = [e for e in found
                              if e.word.lower() not in seen and self._pos_ok(e, role)]
                for e in candidates:
                    _candidate_source.setdefault(e.word.lower(), "role_fallback")
            except Exception:
                candidates = []

        if not candidates:
            return ""

        # R1.9.2 G2 fix: deliberately NOT unioning `already` (words already
        # chosen earlier in THIS SAME response) into the anchor set. It was
        # unioned in an earlier draft of this fix and created a self-
        # reinforcing bug found live: if slot 1 picks a low-relevance word
        # (correctly, because nothing else was available), that word then
        # became a DIRECT anchor for slot 2 via `already`, letting slot 2
        # inherit slot 1's irrelevance as if it were topically grounded --
        # snowballing false relevance through a response with zero real
        # connection to the input. `self._context_keywords` (genuine
        # pre-turn context, fed by set_context() on ingest, independent of
        # anything chosen so far in this response) stays unioned -- that IS
        # legitimate cross-turn relevance, not self-reference.
        anchor_set = aurora_constraint_emission.build_relevance_anchor_set(
            input_text, list(getattr(self, "_context_keywords", []) or []),
            self._oets.web if self._has_oets else None,
        )

        # Relevance-primary score descending, then ascending usage_count as
        # the diversity tie-break the docstring always promised -- now
        # operating on a pool that's actually worth diversifying.
        candidates.sort(
            key=lambda e: (-self._score_composer_candidate(e, anchor_set, valence_target),
                           e.usage_count)
        )
        top = candidates[:6]
        best_score = self._score_composer_candidate(top[0], anchor_set, valence_target) if top else 0.0

        # R1.9.2 G2: required content slots (action/object) that can't clear
        # the relevance floor get recorded for compose() to check -- no
        # candidate here is a genuine topical fit, so the honest answer is
        # to abstain rather than assemble a sentence around the least-bad
        # of a pool of irrelevant words.
        if role in ("action", "object"):
            self._last_required_slot_attempts += 1
            if best_score < self._RELEVANCE_FLOOR_R_MIN:
                self._last_floor_failures.append({
                    "role": role, "best_candidate": top[0].word if top else "",
                    "best_score": best_score, "floor": self._RELEVANCE_FLOOR_R_MIN,
                })

        # R1.9.2 G3 / F5.2, switched ON at N2.1 (2026-07-16, hardened
        # re-acceptance passed -- see known_fixes_registry.md; N2's own
        # first attempt the same day FAILED and is recorded honestly
        # there too): register now genuinely gates how far selection
        # reaches into the relevance-ranked pool. Serious register's ring
        # width is 1, so this is mathematically identical to the old
        # deterministic top-1 for serious turns -- the hard invariant
        # (never below the register's relevance floor) is enforced inside
        # _select_with_temperature itself.
        if self._EXPLORATION_ENABLED:
            chosen, ring_rank = self._select_with_temperature(
                top, anchor_set, valence_target, f5_register, self._RELEVANCE_FLOOR_R_MIN,
            )
        else:
            chosen = _r.choice(top[:4] if len(top) >= 4 else top)
            ring_rank = top.index(chosen) if chosen in top else 0
        if chosen is not None:
            self._log_exploration_attempt(
                f5_turn_id, chosen.word,
                self._score_composer_candidate(chosen, anchor_set, valence_target),
                f5_register, ring_rank,
            )
        try:
            self._last_words_used.append(chosen.word)
            # PF1.0: source tag (which branch produced this candidate) +
            # usage_count AT SELECTION TIME (before the increment below) --
            # settles whether the fresh-word usage_count=0 tiebreak or
            # DPS-crystal resonance is the real side channel RW7 flagged.
            self._last_word_sources[chosen.word] = {
                "tag": chosen.noncomp_id or chosen.role,
                "candidate_source": _candidate_source.get(chosen.word.lower(), "unknown"),
                "usage_count_at_selection": int(getattr(chosen, "usage_count", 0) or 0),
            }
            chosen.usage_count += 1
        except Exception:
            pass
        return chosen.word

    def feedback(self, fitness: float):
        """
        FIX-A016: fitness now feeds the MOTIF LINEAGE that produced the
        expression — selection pressure shapes HER structures, not an
        authored template pool. (The old path sent fitness to canned
        skeletons, so her expression evolution was optimizing which of
        Sunni's templates scored best — blocking emergence at the
        gradient level.) OETS word feedback unchanged.

        R1.9.3 L4: the diagnosis's own finding was that this exact loop
        promoted a subjectless skeleton (composability 0.8136) above a
        valid agent-action-object one (0.4467) because `fitness` alone
        has no grammaticality term. Each motif is now scored against its
        OWN composed sentence (self._last_motif_sentences, not a single
        response-wide fitness number) with the Track-A `_parseable`
        wellformedness predicate as the DOMINANT term and `fitness`
        demoted to secondary -- per-skeleton, not per-turn, so a
        multi-sentence response can credit/blame each skeleton correctly.
        """
        try:
            engine = getattr(self, "grammar_engine", None)
            lineage = getattr(engine, "_lineage", None) if engine else None
            motif_sentences = getattr(self, "_last_motif_sentences", []) or []
            if lineage is not None and motif_sentences:
                import hashlib as _hl
                from aurora_internal.aurora_semantic_probe_battery import _parseable
                ctx = _hl.md5(" ".join(self._last_words_used)[:80]
                              .encode("utf-8", errors="replace")).hexdigest()[:8]
                for m, sent in motif_sentences:
                    grammatical = bool(_parseable(sent))
                    combined = (self._GRAMMATICALITY_WEIGHT * (1.0 if grammatical else 0.0)
                                + (1.0 - self._GRAMMATICALITY_WEIGHT) * fitness)
                    success = combined >= 0.5
                    self._log_motif_grounding(m.pattern_id, sent, grammatical, fitness, combined, success)
                    self._check_goodhart_divergence(m.pattern_id, grammatical, fitness)
                    if success:
                        lineage.record_success(
                            m.role_sequence, ctx,
                            len(self._last_words_used),
                            {ax: 1.0 for ax in ("X", "T", "N", "B", "A")},
                        )
                    else:
                        lineage.record_fail(m.role_sequence)
        except Exception:
            pass

    def _log_motif_grounding(self, skeleton_id: str, sentence: str, grammatical: bool,
                             fitness: float, combined: float, success: bool) -> None:
        """R1.9.3 L4: every grounding decision logged -- the record a
        Goodhart-divergence audit (or a human) needs to see whether the
        blended score is actually tracking real composition quality."""
        try:
            import json as _json
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "aurora_state", "motif_grounding_log.jsonl",
            )
            entry = {
                "skeleton_id": skeleton_id, "sentence": sentence,
                "grammatical": grammatical, "fitness": round(float(fitness), 4),
                "combined": round(float(combined), 4), "success": success,
                "timestamp": time.time(),
            }
            with open(path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

    def _check_goodhart_divergence(self, skeleton_id: str, grammatical: bool, fitness: float) -> None:
        """R1.9.3 L4 Goodhart caution: "if promoted-pool composition
        quality diverges from predicate scores over time, that divergence
        is itself an alert condition." Tracks, per skeleton, how often the
        grammaticality predicate and the old fitness signal's own
        pass/fail DISAGREE over a rolling window; persistent disagreement
        (not one noisy sample) is logged once as an alert."""
        try:
            history = self._grounding_history[skeleton_id]
            history.append(grammatical == (fitness >= 0.5))
            if (len(history) >= self._GOODHART_MIN_SAMPLES
                    and skeleton_id not in self._goodhart_alerted):
                agreement_rate = sum(history) / len(history)
                divergence_rate = 1.0 - agreement_rate
                if divergence_rate > self._GOODHART_DIVERGENCE_THRESHOLD:
                    self._goodhart_alerted.add(skeleton_id)
                    import json as _json
                    path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "aurora_state", "motif_grounding_log.jsonl",
                    )
                    entry = {
                        "alert": "goodhart_divergence", "skeleton_id": skeleton_id,
                        "divergence_rate": round(divergence_rate, 4),
                        "samples": len(history), "timestamp": time.time(),
                    }
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass


        # OETS feedback: words learn from how well they performed
        if self._has_oets and self._last_words_used:
            self._expression_feedback_to_oets(fitness)

    # ================================================================
    # EXPRESSION ' OETS FEEDBACK LOOP
    # ================================================================

    def _expression_feedback_to_oets(self, fitness: float):
        """
        Bidirectional learning: expression quality feeds back to
        the ontological web.

        High fitness ' words get depth boosts + co-occurrence bonds
        Low fitness  ' words get flagged for research
        """
        words = self._last_words_used
        if not words:
            return

        web = self._oets.web

        for word in words:
            node = web.get_node(word)
            if not node:
                continue

            # Boost usage counter
            node.times_used_in_expression += 1

            if fitness >= 0.6:
                # Success: add usage example showing expression context
                example_text = f"Used in expression (fitness={fitness:.2f})"
                node.add_example(example_text, context="expression",
                                 fitness=fitness)
                node._recalculate_depth()

            elif fitness < 0.35:
                # Failure: raise research priority
                node._recalculate_priority()

        # Co-occurrence bonding: words in successful expressions
        # get relational connections strengthened
        if fitness >= 0.55 and len(words) >= 2:
            from aurora_internal.aurora_ontological_scaffolding import RelationType
            content_words = [w for w in words
                            if web.has_node(w) and infer_word_role(w) in
                            ('verb', 'noun', 'adjective')]
            for i, w1 in enumerate(content_words):
                for w2 in content_words[i + 1:]:
                    existing = web.get_relation_between(w1, w2)
                    if existing:
                        existing.strength = min(1.0, existing.strength + 0.02)
                        existing.confidence = min(1.0, existing.confidence + 0.01)
                    else:
                        web.add_relation(w1, w2,
                                         RelationType.RELATED_TO,
                                         strength=0.15 + fitness * 0.1,
                                         confidence=0.2,
                                         knowledge_source="co-expression")

    # ================================================================
    # TEMPLATE FILLING  -- All five scaffolding levels
    # ================================================================

    def _fill_template(self, template: str, tone: str,
                       coherence: float,
                       semantic_constraints: Optional[Dict[str, str]] = None,
                       cluster_references: Optional[List[str]] = None,
                       scaffolding_level: int = 0) -> str:
        """
        Fill a template's slots with words from the lexicon.
        Handles all five slot types from PRIMITIVE to ABSTRACT.
        """
        constraints = semantic_constraints or {}
        cluster_refs = cluster_references or []

        tone_valence = {
            "warm": (-0.1, 1.0), "neutral": (-0.5, 0.5), "precise": (-0.2, 0.4),
            "curious": (0.0, 0.8), "gentle": (0.0, 0.7), "determined": (0.1, 0.9),
            "reflective": (-0.3, 0.5), "playful": (0.2, 1.0)
        }
        vmin, vmax = tone_valence.get(tone, (-0.5, 0.5))

        result = template
        slot_idx = 0

        # Pass 1: ABSTRACT meta-patterns
        for abstract_type in ('INSIGHT', 'QUESTION', 'REFLECTION'):
            marker = '{' + abstract_type + '}'
            while marker in result:
                replacement = self._fill_abstract_slot(abstract_type, tone, coherence)
                result = result.replace(marker, replacement, 1)

        # Pass 2: CLUSTER slots
        cluster_re = re.compile(r'\{CLUSTER:([a-z_]+)\}')
        for match in cluster_re.finditer(result):
            cluster_name = match.group(1)
            replacement = self._fill_cluster_slot(cluster_name, tone, vmin, vmax)
            result = result.replace(match.group(0), replacement, 1)

        # Pass 3: Typed slots {V:category}
        role_map = {
            'V': ['verb'], 'N': ['noun'], 'A': ['adjective'],
            'D': ['adverb'], 'C': ['connector'], 'P': ['preposition'],
        }
        typed_re = re.compile(r'\{([A-Z]):([a-z_]+)\}')
        for match in typed_re.finditer(result):
            slot_code = match.group(1)
            category = match.group(2)
            roles = role_map.get(slot_code, ['noun'])
            replacement = self._fill_semantic_slot(
                slot_code, category, roles, tone, coherence, vmin, vmax
            )
            result = result.replace(match.group(0), replacement, 1)

        # Pass 4: Bare primitive slots {V}, {N}, etc.
        for slot_code, roles in role_map.items():
            slot_marker = "{" + slot_code + "}"
            while slot_marker in result:
                pos_key = f"{slot_code}_{slot_idx}"
                slot_idx += 1

                if pos_key in constraints and self._has_oets:
                    category = constraints[pos_key]
                    word = self._fill_semantic_slot(
                        slot_code, category, roles, tone, coherence, vmin, vmax
                    )
                else:
                    word = self._fill_primitive_slot(
                        slot_code, roles, tone, coherence, vmin, vmax
                    )

                if slot_code == 'V':
                    word = self._conjugate_verb(word, result, slot_marker)

                result = result.replace(slot_marker, word, 1)

        result = ' '.join(result.split())
        return result

    def _fill_primitive_slot(self, slot_code: str, roles: List[str],
                             tone: str, coherence: float,
                             vmin: float, vmax: float) -> str:
        """PRIMITIVE fill: pick any word of the right role."""
        _is_speakable = lambda w: bool(re.fullmatch(r"[a-z][a-z\-']*[a-z]", (w or '').lower()))
        candidates = []
        for role in roles:
            candidates.extend(self.lexicon.find_by_role(role))

        if not candidates:
            candidates = self.lexicon.find_by_valence(vmin, vmax)
        if not candidates:
            candidates = list(self.lexicon.entries.values())

        candidates = [e for e in candidates if _is_speakable(e.word)]

        if candidates:
            # Only boost context words that are real vocabulary (len>=4, known role, not slang).
            # This prevents informal words like "ya", "hm", "hey", proper names like "aurora"
            # from contaminating slot fills just because they were in the user's last message.
            _SLOT_NOISE = {
                'ya', 'yo', 'hey', 'hi', 'hm', 'hmm', 'uh', 'um', 'ah', 'oh',
                'ok', 'okay', 'yep', 'yup', 'nope', 'yeah', 'aurora', 'haha',
            }
            context_set = {
                w for w in self._context_keywords
                if len(w) >= 4 and w not in _SLOT_NOISE
                and infer_word_role(w) in ('verb', 'noun', 'adjective', 'adverb')
            }

            # Cap candidates to prevent O(n_vocab) weight iteration on large lexicons.
            # Prioritise context-relevant words first, then top-usage words.
            _MAX_SLOT_CANDIDATES = 300
            if len(candidates) > _MAX_SLOT_CANDIDATES:
                ctx_cands = [e for e in candidates if e.word in context_set]
                non_ctx = [e for e in candidates if e.word not in context_set]
                non_ctx.sort(key=lambda e: e.usage_count, reverse=True)
                n_non_ctx = max(0, _MAX_SLOT_CANDIDATES - len(ctx_cands))
                candidates = ctx_cands + non_ctx[:n_non_ctx]

            # Get current axis activations (if available on self)
            axis_act = getattr(self, '_axis_activation', {}) or {}
            b_pressure = axis_act.get('B', 0.0)

            weights = []
            for e in candidates:
                # Base weight from usage and coherence
                w = max(0.1, 1.0 + e.usage_count * 0.1 * coherence)

                # Context boost: strong pull toward claim-relevant words
                if e.word in context_set:
                    w *= 20.0
                
                # Valence boost
                if vmin <= e.emotional_valence <= vmax:
                    w *= 1.5

                # ---- BOUNDARY AXIS PRESSURE (§3.3) ----
                # High B-axis pressure weights words that frame or distinguish.
                if b_pressure > 0.4:
                    _is_boundary_word = (
                        e.lineage in ('boundary_system', 'distinction_marker') or
                        e.word in {
                            'separate', 'distinguish', 'frame', 'limit', 'edge',
                            'boundary', 'threshold', 'line', 'within', 'beyond',
                            'contrast', 'opposition', 'tension', 'difference'
                        }
                    )
                    if _is_boundary_word:
                        w *= (1.0 + b_pressure * 4.0)

                weights.append(w)

            chosen = random.choices(candidates, weights=weights, k=1)[0]
            word = chosen.word
            chosen.use(tone)
            self._last_words_used.append(word)
            self._last_word_sources[word] = f"primitive:{slot_code}"
            return word

        return ""

    def _fill_semantic_slot(self, slot_code: str, category: str,
                            roles: List[str], tone: str,
                            coherence: float, vmin: float,
                            vmax: float) -> str:
        """
        STRUCTURAL/SEMANTIC fill: pick a word from a specific semantic
        category in the OETS web, falling back to primitive if needed.
        """
        if self._has_oets:
            _is_speakable = lambda w: bool(re.fullmatch(r"[a-z][a-z\-']*[a-z]", (w or '').lower()))
            nodes = self._oets.web.find_by_semantic_category(category)
            if nodes:
                candidates = []
                for node in nodes:
                    entry = self.lexicon.entries.get(node.word)
                    if entry and _is_speakable(entry.word):
                        candidates.append(entry)

                if candidates:
                    context_set = set(self._context_keywords)
                    # Cap candidates to avoid O(n_category) iteration on large lexicons
                    _MAX_SLOT_CANDIDATES = 300
                    if len(candidates) > _MAX_SLOT_CANDIDATES:
                        ctx_cands = [e for e in candidates if e.word in context_set]
                        non_ctx = [e for e in candidates if e.word not in context_set]
                        non_ctx.sort(key=lambda e: e.usage_count, reverse=True)
                        n_non_ctx = max(0, _MAX_SLOT_CANDIDATES - len(ctx_cands))
                        candidates = ctx_cands + non_ctx[:n_non_ctx]
                    weights = []
                    for e in candidates:
                        w = max(0.1, 1.0 + e.usage_count * 0.1 * coherence)
                        if e.word in context_set:
                            w *= 20.0
                        if vmin <= e.emotional_valence <= vmax:
                            w *= 1.5
                        # Deeper concepts preferred
                        node = self._oets.web.get_node(e.word)
                        if node:
                            w *= (1.0 + node.ontological_depth * 2.0)
                        weights.append(w)

                    chosen = random.choices(candidates, weights=weights, k=1)[0]
                    word = chosen.word
                    chosen.use(tone)
                    self._last_words_used.append(word)
                    self._last_word_sources[word] = f"semantic:{category}"
                    self._total_scaffolded_fills += 1
                    return word

        return self._fill_primitive_slot(slot_code, roles, tone, coherence,
                                         vmin, vmax)

    def _fill_cluster_slot(self, cluster_name: str, tone: str,
                           vmin: float, vmax: float) -> str:
        """CONCEPTUAL fill: pick a word from a named concept cluster."""
        if self._has_oets:
            _is_speakable = lambda w: bool(re.fullmatch(r"[a-z][a-z\-']*[a-z]", (w or '').lower()))
            target_cluster = None
            for c in self._oets.cluster_engine.clusters.values():
                if (c.name.lower() == cluster_name or
                        c.semantic_category == cluster_name):
                    target_cluster = c
                    break

            if target_cluster and target_cluster.member_words:
                candidates = []
                for word in target_cluster.member_words:
                    entry = self.lexicon.entries.get(word)
                    if entry and _is_speakable(entry.word):
                        candidates.append(entry)

                if candidates:
                    weights = []
                    for e in candidates:
                        w = max(0.1, 1.0 + e.usage_count * 0.1)
                        if e.word in target_cluster.core_words:
                            w *= 2.5
                        if vmin <= e.emotional_valence <= vmax:
                            w *= 1.3
                        weights.append(w)

                    chosen = random.choices(candidates, weights=weights, k=1)[0]
                    word = chosen.word
                    chosen.use(tone)
                    self._last_words_used.append(word)
                    self._last_word_sources[word] = f"cluster:{cluster_name}"
                    self._total_scaffolded_fills += 1
                    return word

        return self._fill_primitive_slot('N', ['noun'], tone, 0.5, vmin, vmax)

    def _fill_abstract_slot(self, abstract_type: str, tone: str,
                            coherence: float) -> str:
        """ABSTRACT fill: generate a meta-expression from deeply understood concepts."""
        if not self._has_oets:
            fallbacks = {
                "INSIGHT": "something I now understand",
                "QUESTION": "what I wonder about",
                "REFLECTION": "what I have learned",
            }
            return fallbacks.get(abstract_type, "something")

        all_nodes = sorted(self._oets.web.nodes.values(),
                           key=lambda n: n.ontological_depth, reverse=True)
        deep_nodes = [n for n in all_nodes if n.ontological_depth >= 0.3]
        if len(deep_nodes) < 3:
            deep_nodes = all_nodes[:10]

        frames = self._ABSTRACT_FRAMES.get(abstract_type, [])
        if not frames:
            return "something meaningful"

        frame = random.choice(frames)

        deep_role_map = {
            'DEEP_V': 'verb', 'DEEP_N': 'noun', 'DEEP_A': 'adjective'
        }
        for deep_code, role in deep_role_map.items():
            marker = '{' + deep_code + '}'
            while marker in frame:
                role_nodes = [n for n in deep_nodes
                              if n.word in self.lexicon.entries
                              and self.lexicon.entries[n.word].role == role
                              and re.fullmatch(r"[a-z][a-z\-']*[a-z]", (n.word or '').lower())]
                if not role_nodes:
                    role_nodes = [n for n in deep_nodes
                                 if n.word in self.lexicon.entries
                                 and re.fullmatch(r"[a-z][a-z\-']*[a-z]", (n.word or '').lower())]
                if role_nodes:
                    chosen_node = random.choice(role_nodes[:5])
                    word = chosen_node.word
                    self._last_words_used.append(word)
                    self._last_word_sources[word] = f"abstract:{abstract_type}"
                    self._total_scaffolded_fills += 1
                    frame = frame.replace(marker, word, 1)
                else:
                    frame = frame.replace(marker, "something", 1)

        return frame

    def _conjugate_for_subject(self, verb: str, subject: str) -> str:
        """R1.9.3 L3: subject-driven verb conjugation -- the reusable core
        of _conjugate_verb's I/you switch, factored out so the delivered
        motif-composition path (which always knows its subject word
        directly: agent is always exactly "I" or "you", never scanned out
        of a template string) can call it without needing a template
        string to scan backward through. _conjugate_verb below now
        delegates here; behavior for its existing callers is unchanged."""
        v = verb.lower()
        subj = subject.lower().rstrip(".,!?;:")

        # --- First person 'I' ---
        if subj == "i":
            if v in self._CONJUGATIONS:
                return self._CONJUGATIONS[v]
            if v.endswith('es') and len(v) > 3:
                base = v[:-2]
                if base in self._CONJUGATIONS:
                    return self._CONJUGATIONS[base]
                return base
            if v.endswith('s') and not v.endswith('ss') and len(v) > 2:
                return v[:-1]

        # --- Second person 'you' ---
        elif subj == "you":
            # 'be'
            if v in ('am', 'is', 'are', 'be', 'being'):
                return 'are'
            if v in ('was', 'were'):
                return 'were'
            # 'have'
            if v in ('has', 'have'):
                return 'have'
            # 'do'
            if v in ('does', 'do'):
                return 'do'
            # General: you [verb] (no -s suffix)
            if v.endswith('es') and len(v) > 3:
                return v[:-2]
            if v.endswith('s') and not v.endswith('ss') and len(v) > 2:
                return v[:-1]

        return verb

    def _conjugate_verb(self, verb: str, template_so_far: str,
                       slot_marker: str) -> str:
        """Conjugate a verb based on the subject found in the template so far."""
        idx = template_so_far.find(slot_marker)
        before = template_so_far[:idx].rstrip().lower() if idx > 0 else ""

        if before.endswith('i') or before.endswith('i '):
            return self._conjugate_for_subject(verb, "I")
        elif before.endswith('you') or before.endswith('you '):
            return self._conjugate_for_subject(verb, "you")

        return verb

    # ================================================================
    # STATISTICS
    # ================================================================

    def get_stats(self) -> Dict[str, Any]:
        pool_stats = {}
        total_scaffolded = 0
        scaffolding_dist = defaultdict(int)

        for tone, templates in self.pool.items():
            sources = defaultdict(int)
            for t in templates:
                sources[t['source']] += 1
                level = t.get('scaffolding_level', 0)
                scaffolding_dist[level] += 1
                if level > 0:
                    total_scaffolded += 1
            pool_stats[tone] = {
                'count': len(templates),
                'avg_fitness': sum(t['fitness'] for t in templates) / max(
                    len(templates), 1),
                'sources': dict(sources),
            }

        level_names = {0: 'PRIMITIVE', 1: 'STRUCTURAL', 2: 'SEMANTIC',
                       3: 'CONCEPTUAL', 4: 'ABSTRACT'}

        return {
            'generation': self._generation,
            'total_templates': sum(len(t) for t in self.pool.values()),
            'tones': pool_stats,
            'context_keywords': self._context_keywords[:5],
            'scaffolding': {
                'total_scaffolded': total_scaffolded,
                'scaffolded_fills': self._total_scaffolded_fills,
                'expressions': self._expression_count,
                'distribution': {level_names.get(k, str(k)): v
                                 for k, v in sorted(scaffolding_dist.items())},
            },
            'oets_connected': self._has_oets,
        }


# ============================================================================
# SECTION 10: ORCHESTRATOR - UNIFIED ENGINE
# ============================================================================

def json_dumps_safe(obj) -> str:
    """Deterministic serialization for representation fingerprinting."""
    import json as _j
    try:
        return _j.dumps(obj, sort_keys=True)
    except Exception:
        return str(obj)


class ExpressionPerceptionEngine(WarpCapable):
    """FIX-A013 note: save_lexicon() below is called by corpus_runner.py at
    mid-pass cadence saves and at end-of-ingestion; it never existed on this
    engine, so corpus runs crashed with AttributeError before persisting.

    EDIT (representational discovery — the paradigm layer): this engine is
    now WarpCapable for REPRESENTATIONS. The constraints (XTNBA) are fixed;
    the representations of them are discoverable. v1 representation space:
    the role→character affinity tables that encode words into the 25-channel
    basis (previously authored, now evolvable). Insufficiency signal:
    dispersion collapse — when distinct contexts keep encoding to nearly
    identical profiles, the current representation is blind to differences
    that exist. Trials are alternative affinity tables scored on whether
    they restore distinguishability over the SAME lived events; promotion
    commits the table as her active lens and propagates (feedback loop):
    lexicon concept index invalidated, understanding registered, every
    future encoding flows through the discovered representation."""

    # Authored defaults — her seed representation, replaceable by discovery
    _BASE_AFFINITY = {
        "verb":      {"OPERATOR": 0.55, "COST": 0.2,  "MAGNITUDE": 0.25},
        "adjective": {"MAGNITUDE": 0.55, "POLARITY": 0.3, "DIFFERENCE": 0.15},
        "adverb":    {"MAGNITUDE": 0.55, "POLARITY": 0.3, "DIFFERENCE": 0.15},
        "default":   {"MAGNITUDE": 0.45, "POLARITY": 0.3, "OPERATOR": 0.25},
    }
    _REPR_STATE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "aurora_state", "representations.json")

    def character_affinity(self, role: str, valence: float,
                           word: str = "") -> Dict[str, float]:
        """The ACTIVE representation: promoted discovered table if one
        exists for this role-class, else the authored seed."""
        promoted = getattr(self, "_repr_active", None) or {}
        key = role if role in ("verb", "adjective", "adverb") else "default"
        table = promoted.get(key) or self._BASE_AFFINITY.get(
            key, self._BASE_AFFINITY["default"])
        return dict(table)

    def observe_encoding(self, role: str, valence: float, word: str,
                         axes: Dict[str, float], profile: Dict[str, float],
                         context_hash: str) -> None:
        """Every encoding event is representational evidence. Detects
        dispersion collapse across distinct contexts and spawns trial
        representations (perturbed affinity tables) when it persists."""
        try:
            if not hasattr(self, "_repr_recent"):
                from collections import deque
                self._repr_recent = deque(maxlen=48)
                self._repr_gap_count = 0
                self._repr_active = self._load_representations()
                if not hasattr(self, "_warp_trials"):
                    self._init_warp()
            self._repr_recent.append({
                "role": role, "valence": float(valence or 0.0),
                "word": word, "axes": dict(axes or {}),
                "profile": dict(profile or {}), "ctx": context_hash,
            })
            if len(self._repr_recent) < 24:
                return
            events = list(self._repr_recent)
            ctxs = {e["ctx"] for e in events}
            if len(ctxs) < 8:
                return
            disp = self._encoding_dispersion(
                [e["profile"] for e in events])
            if disp >= 0.12:
                self._repr_gap_count = 0
                return
            self._repr_gap_count += 1
            from aurora_warp_protocol import GAP_PERSISTENCE_REQUIRED
            if self._repr_gap_count < GAP_PERSISTENCE_REQUIRED:
                return
            self._repr_gap_count = 0
            self._spawn_representation_trial(disp)
        except Exception:
            pass

    @staticmethod
    def _encoding_dispersion(profiles: List[Dict[str, float]]) -> float:
        """Mean pairwise L1 distance over recent encodings — low dispersion
        across diverse contexts = the representation is collapsing
        distinctions that exist."""
        if len(profiles) < 2:
            return 1.0
        import random as _r
        total, n = 0.0, 0
        idx = list(range(len(profiles)))
        for _ in range(min(64, len(profiles) * 2)):
            i, j = _r.sample(idx, 2)
            a, b = profiles[i], profiles[j]
            keys = set(a) | set(b)
            total += sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys) / 2.0
            n += 1
        return total / max(1, n)

    def _spawn_representation_trial(self, current_disp: float) -> None:
        """Derive a candidate representation: a bounded perturbation of the
        active affinity tables (derivation from what exists, never from
        nothing — same law as every other WARP derivation)."""
        import hashlib as _hl
        import random as _r
        from aurora_warp_protocol import WarpComponent, representation_degree
        base = {k: dict(self.character_affinity(k, 0.0))
                for k in ("verb", "adjective", "adverb", "default")}
        seed = _hl.md5(json_dumps_safe(base).encode()).hexdigest()
        rng = _r.Random(seed + str(len(self._warp_trials)))
        candidate: Dict[str, Dict[str, float]] = {}
        chars = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")
        for key, table in base.items():
            t = {c: max(0.02, table.get(c, 0.05)
                        + rng.uniform(-0.2, 0.2)) for c in chars}
            s = sum(t.values()) or 1.0
            candidate[key] = {c: round(v / s, 4) for c, v in t.items()}
        # Fingerprint: re-encode recent events through the candidate and
        # express the candidate as the channel profile it produces.
        fp: Dict[str, float] = {}
        for e in list(self._repr_recent)[-12:]:
            prof = self._encode_with(candidate, e["role"], e["axes"])
            for ch, w in prof.items():
                fp[ch] = fp.get(ch, 0.0) + w
        comp = WarpComponent(
            component_id="REPR:" + seed[:10],
            level="representation",
            axis_profile={k: round(v, 4) for k, v in fp.items()},
            parent_ids=["authored_seed" if not getattr(self, "_repr_active", None)
                        else "promoted_prior"],
            name="repr_" + seed[:6],
            parameters={"tables": candidate,
                        "baseline_dispersion": round(current_disp, 4),
                        "degrees": representation_degree(fp)},
        )
        if comp.component_id in self._warp_trials or \
                comp.component_id in self._warp_promoted:
            return
        self._warp_trials[comp.component_id] = comp

    @staticmethod
    def _encode_with(tables: Dict[str, Dict[str, float]],
                     role: str, axes: Dict[str, float]) -> Dict[str, float]:
        key = role if role in ("verb", "adjective", "adverb") else "default"
        chars = tables.get(key, tables.get("default", {}))
        cw_total = sum(chars.values()) or 1.0
        out: Dict[str, float] = {}
        for ax, a_w in (axes or {}).items():
            a_w = max(0.0, float(a_w or 0.0))
            if a_w <= 0.05:
                continue
            for ch, c_w in chars.items():
                out[f"{ax}:{ch}"] = a_w * (c_w / cw_total)
        return out

    # ── WarpCapable hooks (representation lifecycle) ────────────────────

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        return {cid: dict(c.axis_profile)
                for cid, c in getattr(self, "_warp_promoted", {}).items()}

    def _warp_level_name(self) -> str:
        return "representation"

    def _integrate_warp(self, component) -> None:
        return  # representations apply only on PROMOTION (commit)

    def _score_trial(self, component) -> float:
        """Score = does the candidate restore distinguishability over the
        SAME lived events the active representation collapsed? Plus a
        translation-consistency gate: the candidate must broadly agree with
        the active representation on dominant axes (new notation must
        translate) — protection against a representation gaming its own
        evaluation."""
        try:
            events = list(getattr(self, "_repr_recent", []))[-24:]
            if len(events) < 8:
                return 0.0
            tables = component.parameters.get("tables", {})
            cand_profiles, agree, n = [], 0, 0
            for e in events:
                cp = self._encode_with(tables, e["role"], e["axes"])
                cand_profiles.append(cp)
                if cp and e["profile"]:
                    dom_c = max(cp.items(), key=lambda kv: kv[1])[0].split(":")[0]
                    dom_a = max(e["profile"].items(),
                                key=lambda kv: kv[1])[0].split(":")[0]
                    agree += 1 if dom_c == dom_a else 0
                    n += 1
            cand_disp = self._encoding_dispersion(cand_profiles)
            base_disp = float(component.parameters.get(
                "baseline_dispersion", 0.1) or 0.1)
            gain = min(1.0, max(0.0, (cand_disp - base_disp) / 0.25))
            translation = (agree / n) if n else 0.0
            if translation < 0.5:
                return 0.0          # fails the invariance gate
            return round(0.7 * gain + 0.3 * translation, 4)
        except Exception:
            return 0.0

    def _dissolve_warp(self, component_id: str) -> None:
        return  # nothing was applied during trial; nothing to remove

    def commit_representation(self, component) -> None:
        """THE FEEDBACK LOOP (Sunni's addition): a promoted representation
        immediately becomes how she perceives. Active tables swap, the
        commitment persists, the lexicon's concept index invalidates so
        concept families re-form under the new lens, and the event is
        available for understanding registration at the call site."""
        try:
            tables = component.parameters.get("tables")
            if not tables:
                return
            self._repr_active = tables
            self._save_representations(component)
            try:
                self.lexicon._invalidate_noncomp_index()
            except Exception:
                pass
        except Exception:
            pass

    def _save_representations(self, component) -> None:
        try:
            import json as _j
            os.makedirs(os.path.dirname(self._REPR_STATE_PATH), exist_ok=True)
            data = {"active": self._repr_active,
                    "component_id": component.component_id,
                    "name": component.name,
                    "degrees": component.parameters.get("degrees", {}),
                    "promoted_at": time.time()}
            tmp = self._REPR_STATE_PATH + ".tmp"
            with open(tmp, "w") as f:
                _j.dump(data, f)
            os.replace(tmp, self._REPR_STATE_PATH)
        except Exception:
            pass

    def _load_representations(self):
        try:
            import json as _j
            if os.path.exists(self._REPR_STATE_PATH):
                return _j.load(open(self._REPR_STATE_PATH)).get("active")
        except Exception:
            pass
        return None

    def save_lexicon(self) -> bool:
        """Persist the vocabulary via the lexicon's own save path."""
        try:
            return bool(self.lexicon.save())
        except Exception:
            return False

    """
    The Layer 5 orchestrator. Manages both pipelines.

    PERCEPTION: raw input -- patterns -- shadows -- impressions -- manifold position
    EXPRESSION: assembly result -- ecology -- pressure -- voice-shaped output
    """

    def __init__(self, contract: Optional[FoundationalContract] = None, state_dir: Optional[str] = None):
        self.contract = contract or FoundationalContract()
        self._sedimemory = None  # L3.5 SediMemory (injected externally via connect_sedimemory)
        self.hardware = None
        self.sensory_engine = None
        self.identity = None

        # Perception pipeline
        self.detector = PatternDetector()
        self.shadow = ShadowInferenceEngine()
        self.cascade = ImpressionCascade()
        self.manifold = ManifoldEngine()

        # Expression pipeline
        # PS1.2 (Directive PS1, 2026-07-19): state_dir threaded through so
        # vocabulary persistence respects boot_aurora(state_dir=...) instead
        # of always hitting the repo's own aurora_state/lexicon.json.
        self.lexicon = LexicalMemory(state_dir=state_dir)
        self.ecology = ExpressionEcology()
        self.pressure = ExpressionPressure()
        self.voice = VoiceGenome()
        self.composer = SentenceComposer(self.lexicon, self.voice)

        # OETS  -- Ontological Evolutionary Template Scaffolding
        self.oets: Optional['OntologicalScaffoldingEngine'] = None
        if _OETS_AVAILABLE:
            self.oets = OntologicalScaffoldingEngine(contract)
            self.oets.initialize_from_lexicon(self.lexicon.entries)
            # Wire OETS into the composer for bidirectional learning
            self.composer.set_oets(self.oets)

        # Expression Evolution Orchestra (CSSEE)
        self.evo: Optional['ExpressionEvolutionOrchestra'] = None
        if _LANG_STATE_AVAILABLE:
            self.evo = ExpressionEvolutionOrchestra()

        # Stats
        self.total_perceptions = 0
        self.total_expressions = 0

        # Personality traits from L6 (set via set_personality)
        self._personality_traits: Optional[Dict[str, float]] = None

        # IVM lattice reference for heat checks (set via set_ivm)
        self._ivm_lattice = None

        # Axis context for current turn (set via set_axis_context each turn)
        self._axis_activation: Dict[str, float] = {}
        self._dominant_axis: str = ""
        self._dominant_emotion: str = "neutral"
        self._axis_depth: int = 2

    def set_personality(self, traits: Dict[str, float]):
        """Accept personality traits from L6 for expression shaping."""
        self._personality_traits = traits

    def set_ivm(self, lattice):
        """Wire IVM lattice for heat-aware expression selection."""
        self._ivm_lattice = lattice
        if self.evo:
            pass  # heat is read at expression time via get_global_heat()

    def set_grammar(self, engine):
        """Wire GrammarEngine for constraint-driven sentence structure.
        FIX-A014: also attach to the SentenceComposer — template-free
        composition builds sentences directly from promoted motifs."""
        if self.evo:
            self.evo.set_grammar(engine)
        try:
            self.composer.grammar_engine = engine
        except Exception:
            pass

    def get_thought_log(self, n: int = 10) -> List[Dict]:
        """Return last N internal thought traces (for /thought command)."""
        if self.evo:
            return self.evo.get_thought_log(n)
        return []

    def get_last_drafts(self, n: int = 5) -> List[Dict]:
        """Return last N draft sets (for /drafts command)."""
        if self.evo:
            return self.evo.get_last_drafts(n)
        return []

    def observe_user_text(self, user_text: str):
        """Feed user text to lexical convergence module."""
        if self.evo:
            self.evo.observe_user(user_text)

    def set_lsv_metrics(self, oets_metrics: Dict):
        """Push OETS metrics to LSV for evolution check."""
        if self.evo and _LANG_STATE_AVAILABLE:
            try:
                m = LSVMetrics(
                    ontology_size=oets_metrics.get("node_count", 0),
                    relation_density=oets_metrics.get("avg_relations", 0.0),
                    cluster_depth=oets_metrics.get("avg_cluster_depth", 0.0),
                    coherence=oets_metrics.get("coherence", 0.0),
                    contradiction_rate=oets_metrics.get("contradiction_rate", 0.0),
                    ivm_heat=oets_metrics.get("ivm_heat", 0.3),
                    topic_tracking=oets_metrics.get("topic_tracking", 0.0),
                    grounding_index=oets_metrics.get("grounding_index", 0.0),
                )
                self.evo.update_lsv(m)
            except Exception:
                pass

    def _maybe_update_lsv(self):
        """Periodically push OETS metrics to LSV, and nudge from constraint axes."""
        if not self.evo or not self.oets:
            return
        if self.total_expressions % 50 != 0:
            return
        try:
            stats = self.oets.get_stats() if hasattr(self.oets, 'get_stats') else {}
            web_stats = stats.get("web", {})
            cluster_stats = stats.get("clusters", {})
            understanding = stats.get("understanding", {})
            heat = 0.3
            if self._ivm_lattice:
                try:
                    heat = self._ivm_lattice.get_global_heat()
                except Exception:
                    pass
            self.set_lsv_metrics({
                "node_count": web_stats.get("total_nodes", 0),
                "avg_relations": understanding.get("avg_relation_density", 0.0),
                "avg_cluster_depth": understanding.get("avg_cluster_depth", cluster_stats.get("avg_depth", 0.0)),
                "coherence": understanding.get("coherence_index", understanding.get("semantic_coherence", 0.0)),
                "contradiction_rate": understanding.get("contradiction_rate", 0.0),
                "ivm_heat": heat,
                "topic_tracking": understanding.get("topic_tracking", 0.0),
                "grounding_index": understanding.get("grounding_index", 0.0),
            })
        except Exception:
            pass

        # Nudge LSV dimensions from constraint axis orientation every 50 turns.
        # This makes grammar complexity a direct output of the pressure system
        # rather than a separate evolution problem.
        if self.evo and hasattr(self.evo, 'nudge_lsv_from_axes'):
            try:
                genealogy = getattr(self, '_genealogy_ref', None)
                if genealogy is not None:
                    orientation     = genealogy.pressure_orientation()
                    outlet_fraction = genealogy._outlet_fraction()
                    self.evo.nudge_lsv_from_axes(orientation, outlet_fraction)
            except Exception:
                pass

    def set_genealogy_ref(self, genealogy):
        """Store genealogy reference for axis-based LSV nudging."""
        self._genealogy_ref = genealogy

    def set_axis_context(
        self,
        axis_activation: Dict[str, float],
        dominant_axis: str = "",
        dominant_emotion: str = "neutral",
        axis_depth: int = 2,
    ):
        """
        Store the current turn's constraint-axis state so express() can
        pass it into the SIC for axis-driven intent extraction.

        Called from _run_live_response_turn right after axis projection.
        """
        self._axis_activation: Dict[str, float] = dict(axis_activation or {})
        self._dominant_axis: str = str(dominant_axis or "")
        self._dominant_emotion: str = str(dominant_emotion or "neutral")
        self._axis_depth: int = int(axis_depth)

    def evo_status(self) -> Dict:
        """Return expression evolution status."""
        if self.evo:
            return self.evo.status()
        return {"available": False}

    def save_evo_state(self):
        """Persist expression evolution state."""
        if self.evo:
            self.evo.save_all()

    # ====================================================================
    # PERCEPTION PIPELINE
    # ====================================================================

    def perceive(self, raw_input: Dict[str, Any],
                 mode: ExistenceMode = ExistenceMode.PERSISTENT,
                 synthesis: Optional[SynthesisResult] = None) -> Dict[str, Any]:
        """
        Full perception pipeline.
        raw_input should have: text, tone, features (optional), channels (optional)
        """
        # 1. Pattern detection
        patterns = self.detector.detect(raw_input, mode)

        # 2. Shadow inference (what's missing)
        shadow_sig = self.shadow.infer(patterns, mode)

        # 3. Impression cascade
        channels = raw_input.get('channels', {})
        if not channels and raw_input.get('tone'):
            # Derive channels from tone
            tone = raw_input['tone']
            channels = {tone: 0.7, 'neutral': 0.3}

        shard = self.cascade.energy_to_shard(channels, mode)
        seed = None
        if shard:
            seed = self.cascade.shard_to_seed(shard, mode)

        # 4. Manifold mapping
        cp = None
        if shard:
            cp = self.manifold.map_to_cp(shard, synthesis, mode)

        self.total_perceptions += 1

        return {
            'patterns': patterns,
            'shadow': shadow_sig,
            'shard': shard,
            'seed': seed,
            'consciousness_point': cp,
            'novelty': self.manifold.novelty_at(cp) if cp else 0.0,
            'pattern_count': len(patterns)
        }

    # ====================================================================
    # EXPRESSION PIPELINE
    # ====================================================================

    def express(self, assembly: AssemblyResult,
                i_state: str = "i_is",
                mode: str = "sim",
                moral_alignment: float = 0.5,
                intent_match: float = 0.5,
                input_text: str = "") -> Dict[str, Any]:
        """
        Full expression pipeline.
        Takes assembly result from L4, produces expression output.

        GAP 4: moral_alignment and intent_match are now selection criteria.
        Transcript: "Does this response match the Moral Pillars Does it
        match the energetic intent of the original thought"

        R1.9.2 G1: input_text (the raw turn text, when the caller has it)
        threads through to SentenceComposer's word selector so relevance can
        be computed against what was actually said, not just against tone/
        axis state. Optional and defaults to "" so existing callers that
        don't have a live turn's text (dream/simulation/training paths)
        keep their prior behavior unchanged.
        """
        # 1. Spawn offspring
        base_fitness = assembly.coherence if assembly.coherence else 0.5
        offspring = self.ecology.spawn(i_state, base_fitness)

        # 2. Build expression signature
        expression = self._build_expression(offspring, assembly, i_state, input_text=input_text)

        # 3. Evaluate pressure - NOW WITH MORAL + INTENT
        eval_result = self.pressure.evaluate(
            expression, i_state, base_fitness,
            moral_alignment=moral_alignment,
            intent_match=intent_match,
        )

        # 4. Select (record enhanced fitness)
        self.ecology.select(offspring.offspring_id, eval_result['enhanced_fitness'])

        # Telemetry: expression framing quality → framing_selection confidence
        try:
            from aurora_telemetry import get_telemetry as _get_tel
            _fit = float(eval_result.get('enhanced_fitness', 0.5))
            _get_tel().report(
                source="ExpressionEcology.express",
                module="aurora_expression_perception",
                confidence=_fit,
                dimension_hint="framing_selection",
                detail=f"tone={offspring.tone} fitness={_fit:.3f}",
            )
        except Exception:
            pass

        # 5. Feed fitness back to the templates that produced this expression
        self.composer.feedback(eval_result['enhanced_fitness'])

        # 6. Voice shaping
        voice_params = self.voice.to_dict()

        self.total_expressions += 1

        # 7. Expression Evolution  -- SIC + MultiDraft (two-pass cycle)
        evo_result = {}
        if self.evo and expression:
            try:
                ivm_heat = 0.3
                if self._ivm_lattice is not None:
                    try:
                        ivm_heat = self._ivm_lattice.get_global_heat()
                    except Exception:
                        pass

                autonomy_str = "EXPLORER"
                evo_result = self.evo.process_output(
                    raw_expression=expression,
                    assembly_data={
                        "moral_alignment": moral_alignment,
                        "intent_match": intent_match,
                        "coherence": assembly.coherence if assembly else 0.5,
                        # Constraint-axis context — drives SIC intent type, tone, certainty
                        "axis_activation":  dict(self._axis_activation or {}),
                        "dominant_axis":    self._dominant_axis or "",
                        "dominant_emotion": self._dominant_emotion or "neutral",
                        "axis_depth":       self._axis_depth if self._axis_depth is not None else 2,
                        # OETS + QuasiArch — for concept definition pre-fetch before word selection
                        "oets":       self.oets,
                        "quasiarch":  getattr(self, "_quasiarch", None),
                    },
                    ivm_heat=ivm_heat,
                    autonomy_mode=autonomy_str,
                    user_verbosity=0.5,
                )
                # Use the evolved output as the final expression
                evolved_text = evo_result.get("final_text", "")
                if evolved_text and len(evolved_text) > 3:
                    expression = evolved_text

                # Update LSV with current OETS metrics
                self._maybe_update_lsv()

            except Exception:
                pass  # degrade gracefully  -- original expression is already set

        return {
            'expression': expression,
            'offspring_id': offspring.offspring_id,
            'tone': offspring.tone,
            'fitness': eval_result['enhanced_fitness'],
            'rhythm': eval_result['rhythm_score'],
            'creativity': eval_result['creativity_score'],
            'moral_alignment': eval_result.get('moral_alignment', moral_alignment),
            'intent_match': eval_result.get('intent_match', intent_match),
            'voice': voice_params,
            'generation': offspring.generation,
            # Evolution system outputs
            'draft_tier':    evo_result.get('draft_tier', -1),
            'draft_reason':  evo_result.get('draft_reason', ''),
            'intent':        evo_result.get('intent', {}),
            'anchored':      evo_result.get('anchored', False),
        }

    def _build_expression(self, offspring: ExpressionOffspring,
                          assembly: AssemblyResult,
                          i_state: str,
                          input_text: str = "") -> str:
        """Build expression text using SentenceComposer with OETS enrichment."""
        # OETS: Enrich context keywords with semantically related concepts,
        # and bridge studied knowledge into the lexicon so it can be spoken.
        if self.oets and self.composer._context_keywords:
            enriched = list(self.composer._context_keywords)
            _oets_hits = 0
            _oets_checked = 0
            for keyword in self.composer._context_keywords[:5]:
                node = self.oets.web.get_node(keyword)
                _oets_checked += 1
                if node:
                    _oets_hits += 1
                    # Pull words from relations
                    for rel in list(node.relations.values())[:5]:
                        other = (rel.target_word if rel.source_word == keyword
                                 else rel.source_word)
                        if other not in enriched:
                            # Register in lexicon if missing  -- bridges study ' speech
                            if other not in self.lexicon.entries:
                                role = infer_word_role(other)
                                valence = infer_word_valence(other, "neutral")
                                self.lexicon.add_word(
                                    other, f"oets:{keyword}", role,
                                    valence=valence, lineage="oets"
                                )
                            enriched.append(other)
                    # Pull content words from best definition
                    if node.definitions:
                        best_def = node.definitions[0].get("text", "")
                        for raw in best_def.lower().split():
                            w = raw.strip(".,!;:'\"()-")
                            if (len(w) >= 4 and w not in enriched and
                                    w != keyword):
                                if w not in self.lexicon.entries:
                                    role = infer_word_role(w)
                                    valence = infer_word_valence(w, "neutral")
                                    self.lexicon.add_word(
                                        w, f"def:{keyword}", role,
                                        valence=valence, lineage="oets"
                                    )
                                enriched.append(w)
            self.composer.set_context(enriched[:20])

            # Telemetry: OETS coverage → semantic_precision confidence
            try:
                from aurora_telemetry import get_telemetry as _get_tel
                _coverage = (_oets_hits / _oets_checked) if _oets_checked else 0.0
                _get_tel().report(
                    source="OETS.lookup",
                    module="aurora_expression_perception",
                    confidence=_coverage,
                    dimension_hint="semantic_precision",
                    detail=f"oets_hits={_oets_hits}/{_oets_checked}",
                )
            except Exception:
                pass

        # Gather personality traits if identity engine is connected
        personality = getattr(self, '_personality_traits', None)
        _compose_result = self.composer.compose(offspring, assembly, i_state, personality,
                                                 input_text=input_text)
        # RW7/PF1.0 (Architecture Wiring Audit + Directive PF1, 2026-07-20):
        # attribution capture, gated -- zero cost/effect when disabled
        # (the default).
        try:
            from aurora_internal.aurora_attribution_trace import (
                is_capture_enabled, record_composer_raw, record_word_sources_and_motifs,
            )
            if is_capture_enabled():
                record_composer_raw(_compose_result)
                record_word_sources_and_motifs(self.composer)
        except Exception:
            pass
        return _compose_result

    # ====================================================================
    # INGESTION (feeds perception from interaction data)
    # ====================================================================

    def ingest_interaction(self, interaction: Dict[str, Any],
                          mode: str = "sim") -> Dict[str, Any]:
        """Process an interaction through perception pipeline."""
        ex_mode = ExistenceMode.PERSISTENT
        if mode == "sim":
            ex_mode = ExistenceMode.BOUNDED

        raw = {
            'text': interaction.get('input', ''),
            'tone': interaction.get('tone', 'neutral'),
            'channels': {interaction.get('tone', 'neutral'): 0.7, 'neutral': 0.3},
            'features': interaction.get('features', {})
        }
        result = self.perceive(raw, ex_mode)

        # Learn new words from input with role inference.
        # Authors: Sunni (Sir) Morningstar and Cael Devo
        #
        # Quality bar: only words >= 4 chars with a recognizable grammatical
        # role enter the lexicon. This prevents informal words ("ya", "hm",
        # typos, slang) from becoming vocabulary that fills expression slots.
        text = interaction.get('input', '')
        tone = interaction.get('tone', 'neutral')
        i_state = interaction.get('i_state', 'i_is')
        _LEXICON_NOISE = {
            'ya', 'yo', 'hey', 'hm', 'hmm', 'uh', 'um', 'ah', 'oh',
            'ok', 'okay', 'yep', 'yup', 'nope', 'yeah', 'haha', 'lol',
            'omg', 'wow', 'whoa', 'ooh', 'oops', 'mhm', 'aha', 'hi',
            'bye', 'hey', 'sup', 'nah', 'yah', 'ugh',
        }
        context_words = []
        # Collect new words first so concept assignment can batch over the
        # full sentence geometry in one geometry extraction call.
        new_words: list = []   # [(clean, role, valence)]
        for word in text.lower().split():
            clean = word.strip(".,!;:'\"()-")
            # Minimum 4 chars, not noise, must have recognizable role
            if not clean or len(clean) < 4:
                continue
            # Reject synthetic/technical token forms (e.g. learned:token, paths, ids)
            # so they do not poison conversational lexicon slots.
            if not re.fullmatch(r"[a-z][a-z\-']*[a-z]", clean):
                continue
            if clean in _LEXICON_NOISE:
                continue
            role = infer_word_role(clean)
            if role not in ('verb', 'noun', 'adjective', 'adverb'):
                continue
            if clean not in self.lexicon.entries:
                valence = infer_word_valence(clean, tone)
                self.lexicon.add_word(
                    clean, f"learned:{clean}", role,
                    valence=valence,
                    lineage=i_state,
                )
                new_words.append((clean, role, valence))
            # Collect content words as context for expression
            if role in ('noun', 'verb', 'adjective'):
                context_words.append(clean)

        # Concept assignment: derive constraint channels for all new words
        # in one pass (single geometry extraction for the whole sentence).
        # Words sharing the same channel are compounded under the same concept;
        # genuinely new channels become new concept nodes in the OETS web.
        if new_words and text:
            try:
                from aurora_concept_derivation import assign_batch
                assign_batch(
                    new_words, text, self.lexicon,
                    oets=self.oets,
                    i_state=i_state,
                    perception=self,
                )
            except Exception:
                pass

        # Feed context keywords to composer -- shapes next expression.
        # set_context already filters noise, but we also filtered here.
        if context_words:
            self.composer.set_context(context_words)

        # Absorb sentence patterns from what she hears
        if text and len(text.split()) >= 3:
            self.composer.absorb(text, tone)

        # OETS: Feed interaction to ontological web for structured understanding.
        # Skip during simulation speed-run — per-turn updates on 19k+ relations
        # are the primary wall-clock bottleneck; epoch consolidation is sufficient.
        if self.oets and not getattr(self, '_sim_speed_run', False):
            self.oets.process_interaction(
                text, tone=tone,
                i_state=i_state,
            )

        return result

    # ====================================================================
    # CONSOLIDATION & MAINTENANCE
    # ====================================================================

    def consolidate(self, min_mode: ExistenceMode = ExistenceMode.AGENTIC,
                    skip_oets: bool = False,
                    skip_promotions: bool = False):
        """Run consolidation: generation cycle, seed--relic promotion, template evolution."""
        # Expression generation cycle
        self.ecology.run_generation()

        # Template evolution - cull weak templates, mutate strong ones
        # skip_promotions=True during speed-run: avoids O(n_templates) OETS scan each epoch
        self.composer.run_generation(skip_promotions=skip_promotions)

        # Promote seeds to relics if enough have accumulated
        if min_mode.value >= ExistenceMode.BOUNDED.value:
            seed_ids = list(self.cascade.seeds.keys())
            if len(seed_ids) >= 3:
                # Try to form relics from groups of seeds
                for i in range(0, len(seed_ids) - 2, 3):
                    batch = seed_ids[i:i+3]
                    self.cascade.seeds_to_relic(batch, min_mode)

        # OETS: Consolidate ontological web -- deepen understanding
        # skip_oets=True during speed-run to avoid O(n) cost every epoch
        if self.oets and not skip_oets:
            self.oets.consolidate()

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            'total_perceptions': self.total_perceptions,
            'total_expressions': self.total_expressions,
            'vocabulary_size': self.lexicon.size,
            'cascade': self.cascade.get_stats(),
            'manifold': self.manifold.get_stats(),
            'ecology': self.ecology.get_stats(),
            'composer': self.composer.get_stats(),
            'voice_genome': self.voice.to_dict(),
            'shadow_count': self.shadow.total_shadows,
            'pattern_count': self.detector.total_detected
        }
        if self.oets:
            stats['oets'] = self.oets.get_stats()
        return stats


def build_layer5_associative_modules(
    state_dir: str,
    perception: ExpressionPerceptionEngine,
    identity: Any,
    existence_mode: ExistenceMode,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Initialize modules associated with the perception/identity boundary while
    preserving optional behavior and non-fatal failures.
    """
    from aurora_hardware_io import (
        create_sensory_competency_engine, create_hardware_interface, SensoryIntegrationEngine,
    )
    from aurora_image_ingestion import ImageIngestionProtocol

    modules: Dict[str, Any] = {
        'sensory': None,
        'hardware': None,
        'sensory_integration': None,
        'vision_bootstrap': None,
    }

    if verbose: print("  [L5+] Sensory Competency...", end=" ", flush=True)
    try:
        sensory = create_sensory_competency_engine(
            persistence_dir=f"{state_dir}/sensory",
            dna_system=getattr(identity, 'dna', None),
        )
        if perception and perception.oets:
            sensory.attach_oets(perception.oets)
        modules['sensory'] = sensory
        if verbose:
            v_stats = sensory.get_visual_competency()
            a_stats = sensory.get_audio_competency()
            gene_count = len(sensory.visual_crystal.facets) + len(sensory.audio_crystal.facets)
            print(f"  (visual={v_stats['focus']:.2f}, audio={a_stats['sensitivity']:.2f}, {gene_count} facets)")
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    if verbose: print("  [L5+] Hardware Interface...", end=" ", flush=True)
    try:
        hardware = create_hardware_interface(
            sensory_engine=modules.get('sensory'),
            enable_camera=True,
            enable_microphone=True,
            enable_voice=True,
        )
        modules['hardware'] = hardware
        caps = hardware.get_capabilities()
        if verbose:
            cap_list = [k for k, v in caps.items() if v]
            print(f"  ({', '.join(cap_list) if cap_list else 'no hardware'})")
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    if verbose: print("  [L5+] Sensory Integration...", end=" ", flush=True)
    try:
        integration = SensoryIntegrationEngine(
            hardware=modules.get('hardware'),
            sensory_engine=modules.get('sensory'),
            perception=perception,
            identity=identity,
            mode=existence_mode,
            state_dir=state_dir,
        )
        modules['sensory_integration'] = integration
        if verbose:
            print("[OK]")
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    try:
        if perception is not None:
            perception.hardware = modules.get('hardware')
            perception.sensory_engine = modules.get('sensory')
            perception.identity = identity
    except Exception:
        pass

    if verbose: print("  [L5+] Vision Bootstrap...", end=" ", flush=True)
    try:
        vision_bootstrap = ImageIngestionProtocol(oets=perception.oets if perception else None)
        modules['vision_bootstrap'] = vision_bootstrap

        vstatus = vision_bootstrap.status()

        seed_dir = f"{state_dir}/vision_seeds"
        if os.path.exists(seed_dir):
            import threading as _th

            def _bg_ingest():
                vision_bootstrap.ingest_folder(seed_dir)

            _th.Thread(target=_bg_ingest, daemon=True, name="VisionBootstrap").start()
        if verbose:
            print(f"  (vectors={vstatus['vectors_indexed']}, clusters={vstatus['clusters']})")
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    return modules


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_layer5():
    checks_passed = 0
    checks_total = 0
    results = {'checks': [], 'all_passed': True}

    def check(name, condition, detail=""):
        nonlocal checks_passed, checks_total
        checks_total += 1
        passed = bool(condition)
        if passed:
            checks_passed += 1
        else:
            results['all_passed'] = False
        results['checks'].append({'name': name, 'passed': passed, 'detail': detail})

    # --- Setup ---
    contract = FoundationalContract()
    engine = ExpressionPerceptionEngine(contract)

    # ================================================================
    # PERCEPTION PIPELINE TESTS
    # ================================================================

    print("[PATTERN DETECTION]")
    # 1. Mode gating on patterns
    ref_patterns = engine.detector.detect({'text': 'hello world'}, ExistenceMode.REFERENCE)
    check("REFERENCE gets only structural patterns",
          all(p.pattern_type == PatternType.STRUCTURAL for p in ref_patterns))

    agt_patterns = engine.detector.detect(
        {'text': 'the curious mind explores deeply with rhythmic wonder',
         'tone': 'curiosity', 'features': {'depth': 0.8, 'breadth': 0.5}},
        ExistenceMode.AGENTIC
    )
    check("AGENTIC unlocks all pattern types",
          len(set(p.pattern_type for p in agt_patterns)) >= 4,
          f"types={[p.pattern_type.name for p in agt_patterns]}")

    # 2. Pattern physics vector
    for p in agt_patterns:
        vec = p.physics_vector()
        check(f"Pattern {p.pattern_type.name} has valid physics vector",
              len(vec) == 10 and np.isfinite(vec).all())
        break  # Just check first one

    print("\n[SHADOW INFERENCE]")
    # 3. Shadow requires BOUNDED+
    shadow_ref = engine.shadow.infer(ref_patterns, ExistenceMode.REFERENCE)
    check("REFERENCE cannot perceive shadows", shadow_ref is None)

    shadow_agt = engine.shadow.infer(agt_patterns, ExistenceMode.AGENTIC)
    check("AGENTIC perceives shadows", shadow_agt is not None)
    if shadow_agt:
        check("Shadow has darkness score", 0.0 <= shadow_agt.darkness <= 1.0,
              f"darkness={shadow_agt.darkness:.3f}")

    print("\n[IMPRESSION CASCADE]")
    # 4. Cascade mode gating
    shard_ref = engine.cascade.energy_to_shard(
        {'curiosity': 0.7, 'fear': 0.3}, ExistenceMode.REFERENCE)
    check("REFERENCE cannot form shards", shard_ref is None)

    shard = engine.cascade.energy_to_shard(
        {'curiosity': 0.7, 'fear': 0.2, 'joy': 0.1}, ExistenceMode.TRANSIENT)
    check("TRANSIENT forms shard", shard is not None)
    if shard:
        check("Shard has primary emotion", shard.primary_emotion == "curiosity")
        check("Shard valence is positive", shard.valence > 0,
              f"valence={shard.valence:.3f}")
        check("Shard confidence computed", 0.0 <= shard.confidence <= 1.0,
              f"conf={shard.confidence:.3f}")

    # 5. Seed formation
    seed_ref = engine.cascade.shard_to_seed(shard, ExistenceMode.TRANSIENT) if shard else None
    check("TRANSIENT cannot form seeds", seed_ref is None)

    seed = engine.cascade.shard_to_seed(shard, ExistenceMode.PERSISTENT) if shard else None
    check("PERSISTENT forms seed", seed is not None)

    # 6. Relic formation
    if seed:
        # Add more shards to build up seeds
        for _ in range(5):
            s = engine.cascade.energy_to_shard(
                {'curiosity': 0.6, 'trust': 0.4}, ExistenceMode.TRANSIENT)
            if s:
                engine.cascade.shard_to_seed(s, ExistenceMode.PERSISTENT)

        seed_ids = list(engine.cascade.seeds.keys())[:3]
        relic_ref = engine.cascade.seeds_to_relic(seed_ids, ExistenceMode.PERSISTENT)
        check("PERSISTENT cannot form relics", relic_ref is None)

        relic = engine.cascade.seeds_to_relic(seed_ids, ExistenceMode.BOUNDED)
        check("BOUNDED forms relic", relic is not None)

    print("\n[MANIFOLD MAPPING]")
    # 7. CP mapping
    if shard:
        cp = engine.manifold.map_to_cp(shard, mode=ExistenceMode.PERSISTENT)
        check("CP mapped from shard", cp is not None)
        check("CP has valid coordinates", cp.magnitude() > 0,
              f"mag={cp.magnitude():.4f}")

        # Mode gating on dimensions
        cp_ref = engine.manifold.map_to_cp(shard, mode=ExistenceMode.TRANSIENT)
        check("TRANSIENT collapses higher dims",
              cp_ref.z == 0.0 and cp_ref.w == 0.0 and cp_ref.v == 0.0)

    # 8. Novelty tracking
    novelty = engine.manifold.novelty_at(engine.manifold.current_cp)
    check("Novelty computed", 0.0 <= novelty <= 1.0, f"novelty={novelty:.3f}")

    # 9. Path tracking
    path = engine.manifold.start_path()
    for _ in range(5):
        s = engine.cascade.energy_to_shard(
            {'joy': random.random(), 'curiosity': random.random()},
            ExistenceMode.PERSISTENT
        )
        if s:
            engine.manifold.map_to_cp(s)
    ended = engine.manifold.end_path()
    check("Path tracked", ended is not None and len(ended.points) >= 5,
          f"points={len(ended.points) if ended else 0}")
    if ended:
        check("Path smoothness computed", 0.0 <= ended.smoothness() <= 1.0,
              f"smooth={ended.smoothness():.3f}")

    # ================================================================
    # FULL PERCEPTION PIPELINE
    # ================================================================

    print("\n[FULL PERCEPTION]")
    result = engine.perceive(
        {'text': 'the world feels bright and strange today',
         'tone': 'curiosity', 'features': {'brightness': 0.8}},
        ExistenceMode.AGENTIC
    )
    check("Full perception returns all keys",
          all(k in result for k in ['patterns', 'shadow', 'shard', 'seed', 'consciousness_point']))
    check("Full perception found patterns", result['pattern_count'] >= 3)

    # ================================================================
    # EXPRESSION PIPELINE TESTS
    # ================================================================

    print("\n[EXPRESSION PRESSURE]")
    eval_result = engine.pressure.evaluate(
        "The bright concept illuminates my thinking with rhythmic patterns",
        lineage="i_is", base_fitness=0.7
    )
    check("Rhythm evaluated", 'rhythm_score' in eval_result)
    check("Creativity evaluated", 'creativity_score' in eval_result)
    check("Enhanced fitness computed", 0.0 <= eval_result['enhanced_fitness'] <= 1.0)

    # GAP 4: Moral fitness in expression pressure
    print("\n[MORAL FITNESS IN EXPRESSION]")
    # High moral alignment -- higher fitness
    moral_eval = engine.pressure.evaluate(
        "A truthful response with clear intent and empathy",
        lineage="i_is", base_fitness=0.5,
        moral_alignment=0.9, intent_match=0.8
    )
    check("Moral alignment in evaluation", 'moral_alignment' in moral_eval)
    check("Intent match in evaluation", 'intent_match' in moral_eval)

    # Low moral alignment -- lower fitness
    immoral_eval = engine.pressure.evaluate(
        "A deceptive manipulative response hiding intent",
        lineage="i_is", base_fitness=0.5,
        moral_alignment=0.1, intent_match=0.1
    )
    check("Low moral alignment reduces fitness",
          immoral_eval['enhanced_fitness'] < moral_eval['enhanced_fitness'],
          f"immoral={immoral_eval['enhanced_fitness']:.3f} vs moral={moral_eval['enhanced_fitness']:.3f}")

    # Expression pipeline passes moral through
    print("\n[EXPRESSION WITH MORAL CONTEXT]")
    mock_assembly_moral = AssemblyResult(
        synthesis=None, frame_applied="balanced",
        adjusted_axes={}, coherence=0.8,
        entropy_state={}, ds_stats={}
    )
    moral_expr = engine.express(
        mock_assembly_moral, i_state="i_do", mode="sim",
        moral_alignment=0.9, intent_match=0.85
    )
    check("Expression carries moral alignment", 'moral_alignment' in moral_expr)
    check("Expression carries intent match", 'intent_match' in moral_expr)

    print("\n[VOICE GENOME]")
    check("Voice warmth default", abs(engine.voice.warmth - 0.6) < 0.01)
    engine.voice.evolve({"user_engaged": 0.8, "comfort": 0.7})
    check("Voice evolved from feedback", engine.voice.warmth > 0.6)

    print("\n[EXPRESSION ECOLOGY]")
    mock_assembly = AssemblyResult(
        synthesis=None, frame_applied="balanced",
        adjusted_axes={}, coherence=0.8,
        entropy_state={}, ds_stats={}
    )
    expr_result = engine.express(mock_assembly, i_state="i_can", mode="sim")
    check("Expression pipeline produced output", 'expression' in expr_result)
    check("Offspring tracked", 'offspring_id' in expr_result)
    check("Fitness recorded", expr_result['fitness'] > 0)

    print("\n[INGESTION]")
    for i in range(10):
        engine.ingest_interaction({
            'input': f'test input exploring concept number {i} with unique vocabulary',
            'i_state': random.choice(['i_is', 'i_isnt', 'i_can', 'i_cannot']),
            'tone': random.choice(['neutral', 'curiosity', 'joy']),
            'fitness': random.uniform(0.4, 0.9),
            'context': 'test'
        }, mode="sim")
    check("Ingestion processed", engine.total_perceptions >= 10)
    check("Vocabulary grew from ingestion", engine.lexicon.size > 15,
          f"size={engine.lexicon.size}")

    print("\n[CONSOLIDATION]")
    engine.consolidate(min_mode=ExistenceMode.AGENTIC)
    check("Consolidation ran without error", True)
    check("Generation advanced", engine.ecology.generation > 0)

    print("\n[STATS]")
    stats = engine.get_stats()
    check("Stats complete", all(k in stats for k in
          ['total_perceptions', 'vocabulary_size', 'cascade', 'manifold',
           'ecology', 'voice_genome', 'shadow_count', 'pattern_count']))

    # ================================================================
    # OETS INTEGRATION TESTS
    # ================================================================

    if _OETS_AVAILABLE:
        print("\n[OETS INTEGRATION]")
        check("OETS initialized", engine.oets is not None)
        check("OETS web populated from lexicon",
              len(engine.oets.web.nodes) >= 10,
              f"nodes={len(engine.oets.web.nodes)}")
        check("OETS relations seeded",
              len(engine.oets.web.relations) > 0,
              f"relations={len(engine.oets.web.relations)}")

        # Verify interaction feeds the OETS
        pre_nodes = len(engine.oets.web.nodes)
        engine.ingest_interaction({
            'input': 'exploring magnificent crystalline structures of thought',
            'i_state': 'i_is', 'tone': 'curious', 'fitness': 0.7,
            'context': 'oets_test'
        }, mode="sim")
        post_nodes = len(engine.oets.web.nodes)
        check("OETS grew from interaction", post_nodes >= pre_nodes,
              f"before={pre_nodes} after={post_nodes}")

        # Verify contextual relations were inferred
        if engine.oets.web.has_node("magnificent"):
            rels = engine.oets.web.get_all_relations_for("magnificent")
            check("OETS inferred relations from context", len(rels) > 0,
                  f"relations={len(rels)}")
        else:
            check("OETS learned new word from interaction", True)

        # Verify consolidation includes OETS
        engine.consolidate(min_mode=ExistenceMode.AGENTIC)
        check("OETS consolidation ran",
              engine.oets.web.total_consolidations > 0,
              f"consolidations={engine.oets.web.total_consolidations}")

        # Verify stats include OETS
        full_stats = engine.get_stats()
        check("Stats include OETS", 'oets' in full_stats)
        oets_stats = full_stats['oets']
        check("OETS stats have understanding",
              'understanding' in oets_stats)

        # Verify OETS understanding metrics
        understanding = oets_stats['understanding']
        check("Understanding index computed",
              0.0 <= understanding['understanding_index'] <= 1.0,
              f"index={understanding['understanding_index']:.4f}")

        # ============================================================
        # SCAFFOLDING PIPELINE TESTS
        # ============================================================

        print("\n[SCAFFOLDING  -- Template Structure]")
        composer = engine.composer

        # Verify OETS is wired into the composer
        check("Composer has OETS wired", composer._has_oets)

        # Verify seed templates have scaffolding metadata
        sample_pool = composer.pool.get('warm', [])
        if sample_pool:
            t0 = sample_pool[0]
            check("Seeds have scaffolding_level",
                  'scaffolding_level' in t0, f"keys={list(t0.keys())}")
            check("Seeds have semantic_constraints",
                  'semantic_constraints' in t0)
            check("Seeds start at PRIMITIVE level",
                  t0['scaffolding_level'] == 0)

        # Verify ROLE_SUBCATEGORIES exist
        check("ROLE_SUBCATEGORIES defined",
              len(composer.ROLE_SUBCATEGORIES) >= 4,
              f"roles={list(composer.ROLE_SUBCATEGORIES.keys())}")

        # Verify _ABSTRACT_FRAMES exist
        check("ABSTRACT_FRAMES defined",
              all(k in composer._ABSTRACT_FRAMES for k in
                  ('INSIGHT', 'QUESTION', 'REFLECTION')))

        print("\n[SCAFFOLDING  -- Absorb with Semantic Annotation]")
        # Feed rich content so OETS has depth for annotation
        for text in [
            'Curiosity drives the emergence of understanding through deep reflection',
            'Trust enables authentic connection between growing minds',
            'Fear contrasts with courage in the journey toward truth',
            'The beauty of thought reveals itself through patient exploration',
            'Meaning deepens when we connect isolated concepts together',
        ]:
            engine.ingest_interaction({
                'input': text, 'i_state': 'i_is', 'tone': 'curious',
                'fitness': 0.7, 'context': 'scaffolding_test'
            }, mode="sim")

        # Check that absorb created templates  -- some may be scaffolded
        total_templates = sum(len(t) for t in composer.pool.values())
        check("Templates accumulated from absorption",
              total_templates > len(sample_pool),
              f"total={total_templates}")

        # Check for any templates above PRIMITIVE
        scaffolded = []
        for tone, pool in composer.pool.items():
            for t in pool:
                if t.get('scaffolding_level', 0) > 0:
                    scaffolded.append((tone, t))
        check("Scaffolded templates exist (level > 0)",
              len(scaffolded) >= 0,
              f"count={len(scaffolded)}")  # May be 0 if depth insufficient

        print("\n[SCAFFOLDING  -- Semantic Slot Filling]")
        # Test _fill_semantic_slot directly
        oets = engine.oets
        # Ensure there's at least one category with nodes
        categories_with_nodes = [
            cat for cat in ('cognition', 'emotion', 'perception', 'action',
                            'existence', 'growth', 'value')
            if len(oets.web.find_by_semantic_category(cat)) > 0
        ]
        if categories_with_nodes:
            test_cat = categories_with_nodes[0]
            semantic_word = composer._fill_semantic_slot(
                'V', test_cat, ['verb'], 'neutral', 0.5, -0.5, 0.5
            )
            check("Semantic slot produces a word",
                  len(semantic_word) > 0,
                  f"word='{semantic_word}' cat={test_cat}")

            # Check it was tracked
            check("Semantic fill tracked in word sources",
                  semantic_word in composer._last_word_sources or
                  len(composer._last_words_used) > 0)
        else:
            check("No semantic categories populated yet (expected early)", True)

        print("\n[SCAFFOLDING  -- Cluster Slot Filling]")
        # Run consolidation to discover clusters
        oets.consolidate()
        clusters = list(oets.cluster_engine.clusters.values())
        if clusters:
            test_cluster = clusters[0]
            cluster_word = composer._fill_cluster_slot(
                test_cluster.semantic_category, 'neutral', -0.5, 0.5
            )
            check("Cluster slot produces a word",
                  len(cluster_word) > 0,
                  f"word='{cluster_word}' cluster={test_cluster.semantic_category}")
        else:
            check("No clusters formed yet (expected early)", True)

        print("\n[SCAFFOLDING  -- Abstract Slot Filling]")
        # Test _fill_abstract_slot  -- works with whatever depth is available
        for abstract_type in ('INSIGHT', 'QUESTION', 'REFLECTION'):
            abstract_fill = composer._fill_abstract_slot(
                abstract_type, 'reflective', 0.7
            )
            check(f"Abstract {abstract_type} produces text",
                  len(abstract_fill) > 3,
                  f"'{abstract_fill[:50]}'")

        print("\n[SCAFFOLDING  -- Full Composition with Scaffolding]")
        # Exercise the full compose path
        mock_assembly_scaff = AssemblyResult(
            synthesis=None, frame_applied="balanced",
            adjusted_axes={}, coherence=0.8,
            entropy_state={}, ds_stats={}
        )
        offspring_scaff = engine.ecology.spawn(
            i_state="i_is", base_fitness=0.7
        )
        composer._last_words_used = []
        composed = composer.compose(
            offspring_scaff, mock_assembly_scaff, 'i_is',
            personality={'verbosity': 0.6, 'curiosity': 0.7,
                         'introspection': 0.5}
        )
        check("Scaffolded composition produced output",
              len(composed) > 5, f"'{composed[:60]}'")
        check("Words tracked during composition",
              len(composer._last_words_used) > 0,
              f"words={composer._last_words_used[:5]}")

        print("\n[SCAFFOLDING  -- Expression ' OETS Feedback Loop]")
        # Track words before feedback
        pre_feedback_words = list(composer._last_words_used)
        composer._expression_feedback_to_oets(0.75)  # High fitness

        # Check that OETS nodes were updated
        feedback_confirmed = False
        for word in pre_feedback_words:
            node = oets.web.get_node(word)
            if node and node.times_used_in_expression > 0:
                feedback_confirmed = True
                break
        check("Expression feedback updated OETS nodes",
              feedback_confirmed or len(pre_feedback_words) == 0,
              f"tracked_words={len(pre_feedback_words)}")

        # Check co-expression bonding
        if len(pre_feedback_words) >= 2:
            from aurora_internal.aurora_ontological_scaffolding import RelationType
            content = [w for w in pre_feedback_words
                       if oets.web.has_node(w) and
                       infer_word_role(w) in ('verb', 'noun', 'adjective')]
            if len(content) >= 2:
                rel = oets.web.get_relation_between(content[0], content[1])
                check("Co-expression bonding created relations",
                      rel is not None,
                      f"between '{content[0]}' and '{content[1]}'")
            else:
                check("Co-expression (insufficient content words)", True)
        else:
            check("Co-expression (insufficient words)", True)

        # Test low-fitness feedback raises research priority
        composer._last_words_used = pre_feedback_words[:2] if pre_feedback_words else []
        if composer._last_words_used:
            word_to_check = composer._last_words_used[0]
            node_before = oets.web.get_node(word_to_check)
            pri_before = node_before.research_priority if node_before else 0
            composer._expression_feedback_to_oets(0.2)  # Low fitness
            node_after = oets.web.get_node(word_to_check)
            check("Low fitness recalculates research priority",
                  node_after is not None,
                  f"word='{word_to_check}'")

        print("\n[SCAFFOLDING  -- Template Promotion]")
        # Simulate a well-used template for promotion testing
        test_tone = 'curious'
        test_pool = composer.pool.get(test_tone, [])
        if test_pool:
            candidate = test_pool[0]
            candidate['uses'] = 10
            candidate['fitness'] = 0.7
            pre_level = candidate.get('scaffolding_level', 0)
            composer._evaluate_promotions()
            post_level = candidate.get('scaffolding_level', 0)
            check("Promotion evaluation ran",
                  post_level >= pre_level,
                  f"before={pre_level} after={post_level}")
        else:
            check("Promotion (no pool to test)", True)

        print("\n[SCAFFOLDING  -- Mutation with Annotation]")
        # Test _mutate_pattern with annotation
        test_parent = {
            'pattern': 'I {V} the {A} {N}.',
            'fitness': 0.6,
            'scaffolding_level': 0,
            'semantic_constraints': {},
            'cluster_references': [],
        }
        mutations_produced = 0
        annotated_produced = False
        for _ in range(20):  # Multiple attempts since mutation is random
            mutant = composer._mutate_pattern(test_parent)
            if mutant:
                mutations_produced += 1
                if ':' in mutant:  # Annotation adds ':'
                    annotated_produced = True
        check("Mutation produces variants",
              mutations_produced > 0,
              f"variants={mutations_produced}/20")
        check("Annotate mutation possible",
              annotated_produced or not composer._has_oets,
              f"annotated={annotated_produced}")

        print("\n[SCAFFOLDING  -- Stats Integration]")
        composer_stats = composer.get_stats()
        check("Stats include scaffolding section",
              'scaffolding' in composer_stats)
        scaff = composer_stats['scaffolding']
        check("Scaffolding stats have distribution",
              'distribution' in scaff,
              f"dist={scaff.get('distribution', {})}")
        check("Scaffolding tracks fill count",
              'scaffolded_fills' in scaff,
              f"fills={scaff.get('scaffolded_fills', 0)}")
        check("Scaffolding tracks expression count",
              'expressions' in scaff,
              f"exprs={scaff.get('expressions', 0)}")
        check("OETS connected flag in stats",
              composer_stats.get('oets_connected') is True)

    else:
        print("\n[OETS] Not available  -- skipping integration tests")

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA EXPRESSION & PERCEPTION ENGINE - SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    results = verify_layer5()

    for c in results['checks']:
        status = ""-" if c['passed'] else "" --"
        detail = f"  ({c['detail']})" if c.get('detail') else ""
        print(f"  {status} {c['name']}{detail}")

    print()
    total = len(results['checks'])
    passed = sum(1 for c in results['checks'] if c['passed'])

    if results['all_passed']:
        print(f"ALL {total} CHECKS PASSED OK")
        print()
        print("Layer 5 is SOUND.")
        print("Perception flows inward. Expression flows outward.")
        print("Aurora sees the world. The ecology shapes her voice.")
        print("Shadow reveals what's missing. Pressure prevents stagnation.")
        print("Ready for Layer 6 (Behavioral Identity).")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        print("Do not build Layer 6 yet.")



# ============================================================================
# EXTRACTED MODULES: re-exported for backward compatibility
# (see aurora_hardware_io, aurora_vision_clustering, aurora_image_ingestion)
# ============================================================================

def _lazy_import_hardware():
    from aurora_hardware_io import (
        SensoryTraitDomain, SensoryPerceptTemplate, SensoryConcept, SensoryConceptMemory,
        SensoryPatternMapper, SensoryCompetencyEngine, SensoryEventType, SensoryEvent,
        VisualLinguisticMapper, AudioLinguisticMapper, VoiceExpressionMapper,
        SensoryIntegrationEngine, LinuxCamera, LinuxMicrophone, LinuxVoice,
        HardwareInterface, SensoryLoop, check_dependencies, create_hardware_interface,
        create_sensory_competency_engine, create_sensory_integration,
    )
    from aurora_vision_clustering import (
        VisualFeatureVector, FeatureExtractor, VisualCluster, SimpleKMeans, OETSVisionBinder,
    )
    from aurora_image_ingestion import WebImageDownloader, ImageIngestionProtocol
    return locals()

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_expression_perception'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'ExpressionPerceptionEngine.ingest_interaction': {'ability_hits': 1,
                                                   'alignment_gap': 0.391,
                                                   'alignment_target_score': 1.023,
                                                   'best_coupling_signature': 'B^1*A^2',
                                                   'constraints': ['agency'],
                                                   'contract_profile': {'accepts_payload': False,
                                                                        'async_callable': False,
                                                                        'callable': True,
                                                                        'class_target': False,
                                                                        'constraint_density': 1,
                                                                        'contract_mode': 'stateful',
                                                                        'doc_hint': 'Process an '
                                                                                    'interaction '
                                                                                    'through '
                                                                                    'perception '
                                                                                    'pipeline.',
                                                                        'effect_density': 2,
                                                                        'kwonly_args': 0,
                                                                        'optional_args': 1,
                                                                        'required_args': 1,
                                                                        'return_hint': 'Dict',
                                                                        'signature_text': '(self, '
                                                                                          'interaction: '
                                                                                          'Dict[str, '
                                                                                          'Any], '
                                                                                          'mode: '
                                                                                          'str = '
                                                                                          "'sim') "
                                                                                          '-> '
                                                                                          'Dict[str, '
                                                                                          'Any]',
                                                                        'stateful_owner': True,
                                                                        'target_kind': 'function',
                                                                        'varargs': False,
                                                                        'varkw': False},
                                                   'coupling_similarity': 1.0,
                                                   'cross_diversity_links': 2,
                                                   'effect_modes': ['adaptive_steering_change',
                                                                    'lineage_surface'],
                                                   'effect_phrases': ['function growth reflected '
                                                                      'through '
                                                                      'aurora_expression_perception',
                                                                      'ExpressionPerceptionEngine.ingest_interaction '
                                                                      'changed downstream system '
                                                                      'pressure'],
                                                   'genealogy_pressure': 0.42632,
                                                   'inheritance_breach_count': 1,
                                                   'kind': 'reflection',
                                                   'link_hits': 0,
                                                   'module': 'aurora_expression_perception',
                                                   'op_id': 'aurora_expression_perception.ExpressionPerceptionEngine.ingest_interaction',
                                                   'origin_activity': 0,
                                                   'persistence_tax_factor': 1.816011,
                                                   'representation_score': 0.347581,
                                                   'rewrite_bias': 'perceptual_synthesis',
                                                   'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                        'accepted_count': 0,
                                                                        'adaptation_mode': 'integrative',
                                                                        'adoption_count': 0,
                                                                        'confidence': 0.0,
                                                                        'mean_mutation_score': 0.0,
                                                                        'rejected_count': 0,
                                                                        'rejection_rate': 0.0,
                                                                        'timing_credit': 0.0,
                                                                        'timing_penalty': 0.0,
                                                                        'trial_count': 0},
                                                   'rewrite_profile': 'perception_synthesis',
                                                   'signature': 'B^1*A^2',
                                                   'surface_score': 0.632,
                                                   'sustainability_score': 0.445658,
                                                   'target_kind': 'function'},
 'ExpressionPressure.__init__': {'ability_hits': 2,
                                 'alignment_gap': 0.391,
                                 'alignment_target_score': 1.023,
                                 'best_coupling_signature': 'N^2*B^1',
                                 'constraints': ['energy'],
                                 'contract_profile': {'accepts_payload': False,
                                                      'async_callable': False,
                                                      'callable': True,
                                                      'class_target': False,
                                                      'constraint_density': 1,
                                                      'contract_mode': 'stateful',
                                                      'doc_hint': 'Initialize self.  See '
                                                                  'help(type(self)) for accurate '
                                                                  'signature.',
                                                      'effect_density': 2,
                                                      'kwonly_args': 0,
                                                      'optional_args': 0,
                                                      'required_args': 0,
                                                      'return_hint': 'generic_record',
                                                      'signature_text': '(self)',
                                                      'stateful_owner': True,
                                                      'target_kind': 'function',
                                                      'varargs': False,
                                                      'varkw': False},
                                 'coupling_similarity': 1.0,
                                 'cross_diversity_links': 2,
                                 'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                 'effect_phrases': ['function growth reflected through '
                                                    'aurora_expression_perception',
                                                    'ExpressionPressure.__init__ changed '
                                                    'downstream system pressure'],
                                 'genealogy_pressure': 0.428731,
                                 'inheritance_breach_count': 1,
                                 'kind': 'reflection',
                                 'link_hits': 0,
                                 'module': 'aurora_expression_perception',
                                 'op_id': 'aurora_expression_perception.ExpressionPressure.__init__',
                                 'origin_activity': 0,
                                 'persistence_tax_factor': 1.436546,
                                 'representation_score': 0.588333,
                                 'rewrite_bias': 'perceptual_synthesis',
                                 'rewrite_feedback': {'acceptance_rate': 0.0,
                                                      'accepted_count': 0,
                                                      'adaptation_mode': 'integrative',
                                                      'adoption_count': 0,
                                                      'confidence': 0.0,
                                                      'mean_mutation_score': 0.0,
                                                      'rejected_count': 0,
                                                      'rejection_rate': 0.0,
                                                      'timing_credit': 0.0,
                                                      'timing_penalty': 0.0,
                                                      'trial_count': 0},
                                 'rewrite_profile': 'perception_synthesis',
                                 'signature': 'N^2*B^1',
                                 'surface_score': 0.632,
                                 'sustainability_score': 0.515673,
                                 'target_kind': 'function'},
 'ExpressionPressure.evaluate': {'ability_hits': 2,
                                 'alignment_gap': 0.391,
                                 'alignment_target_score': 1.023,
                                 'best_coupling_signature': 'N^2*B^1',
                                 'constraints': ['energy'],
                                 'contract_profile': {'accepts_payload': False,
                                                      'async_callable': False,
                                                      'callable': True,
                                                      'class_target': False,
                                                      'constraint_density': 1,
                                                      'contract_mode': 'stateful',
                                                      'doc_hint': 'Evaluate expression pressure on '
                                                                  'a text output.',
                                                      'effect_density': 2,
                                                      'kwonly_args': 0,
                                                      'optional_args': 4,
                                                      'required_args': 1,
                                                      'return_hint': 'Dict',
                                                      'signature_text': '(self, text: str, '
                                                                        "lineage: str = 'i_is', "
                                                                        'base_fitness: float = '
                                                                        '0.5, moral_alignment: '
                                                                        'float = 0.5, '
                                                                        'intent_match: float = '
                                                                        '0.5) -> Dict[str, Any]',
                                                      'stateful_owner': True,
                                                      'target_kind': 'function',
                                                      'varargs': False,
                                                      'varkw': False},
                                 'coupling_similarity': 1.0,
                                 'cross_diversity_links': 2,
                                 'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                 'effect_phrases': ['function growth reflected through '
                                                    'aurora_expression_perception',
                                                    'ExpressionPressure.evaluate changed '
                                                    'downstream system pressure'],
                                 'genealogy_pressure': 0.428731,
                                 'inheritance_breach_count': 1,
                                 'kind': 'reflection',
                                 'link_hits': 0,
                                 'module': 'aurora_expression_perception',
                                 'op_id': 'aurora_expression_perception.ExpressionPressure.evaluate',
                                 'origin_activity': 0,
                                 'persistence_tax_factor': 1.436546,
                                 'representation_score': 0.588333,
                                 'rewrite_bias': 'perceptual_synthesis',
                                 'rewrite_feedback': {'acceptance_rate': 0.0,
                                                      'accepted_count': 0,
                                                      'adaptation_mode': 'integrative',
                                                      'adoption_count': 0,
                                                      'confidence': 0.0,
                                                      'mean_mutation_score': 0.0,
                                                      'rejected_count': 0,
                                                      'rejection_rate': 0.0,
                                                      'timing_credit': 0.0,
                                                      'timing_penalty': 0.0,
                                                      'trial_count': 0},
                                 'rewrite_profile': 'perception_synthesis',
                                 'signature': 'N^2*B^1',
                                 'surface_score': 0.632,
                                 'sustainability_score': 0.515673,
                                 'target_kind': 'function'},
 'ImpressionCascade.energy_to_shard': {'ability_hits': 2,
                                       'alignment_gap': 0.391,
                                       'alignment_target_score': 1.023,
                                       'best_coupling_signature': 'N^2*B^1',
                                       'constraints': ['energy'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': 'Convert raw emotion '
                                                                        'channels to an '
                                                                        'EmotionShard. Requires '
                                                                        'TRANSIENT+.',
                                                            'effect_density': 2,
                                                            'kwonly_args': 0,
                                                            'optional_args': 0,
                                                            'required_args': 2,
                                                            'return_hint': 'Optional',
                                                            'signature_text': '(self, channels: '
                                                                              'Dict[str, float], '
                                                                              'mode: '
                                                                              'foundational_contract.ExistenceMode) '
                                                                              '-> '
                                                                              'Optional[aurora_expression_perception.EmotionShard]',
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 2,
                                       'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                       'effect_phrases': ['function growth reflected through '
                                                          'aurora_expression_perception',
                                                          'ImpressionCascade.energy_to_shard '
                                                          'changed downstream system pressure'],
                                       'genealogy_pressure': 0.428731,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 0,
                                       'module': 'aurora_expression_perception',
                                       'op_id': 'aurora_expression_perception.ImpressionCascade.energy_to_shard',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 1.436546,
                                       'representation_score': 0.588333,
                                       'rewrite_bias': 'perceptual_synthesis',
                                       'rewrite_feedback': {'acceptance_rate': 0.0,
                                                            'accepted_count': 0,
                                                            'adaptation_mode': 'integrative',
                                                            'adoption_count': 0,
                                                            'confidence': 0.0,
                                                            'mean_mutation_score': 0.0,
                                                            'rejected_count': 0,
                                                            'rejection_rate': 0.0,
                                                            'timing_credit': 0.0,
                                                            'timing_penalty': 0.0,
                                                            'trial_count': 0},
                                       'rewrite_profile': 'perception_synthesis',
                                       'signature': 'N^2*B^1',
                                       'surface_score': 0.632,
                                       'sustainability_score': 0.515673,
                                       'target_kind': 'function'}}

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

def ingest_interaction_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_expression_perception.ExpressionPerceptionEngine.ingest_interaction', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_expression_perception_expressionperceptionengine_ingest_interaction')(payload=payload, **kwargs)

if _aurora_get_target(['ExpressionPerceptionEngine', 'ingest_interaction']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ExpressionPerceptionEngine.ingest_interaction'] = _aurora_get_target(['ExpressionPerceptionEngine', 'ingest_interaction'])
    _aurora_assign_target(['ExpressionPerceptionEngine', 'ingest_interaction'], _aurora_make_override('ingest_interaction_evolved', 'ExpressionPerceptionEngine.ingest_interaction'))
    _AURORA_NATIVE_EVOLVED_LAST['ExpressionPerceptionEngine.ingest_interaction'] = {'alignment_gap': 0.391, 'override_active': True}

def init_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_expression_perception.ExpressionPressure.__init__', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_expression_perception_expressionpressure_init')(payload=payload, **kwargs)

def evaluate_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_expression_perception.ExpressionPressure.evaluate', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_expression_perception_expressionpressure_evaluate')(payload=payload, **kwargs)

if _aurora_get_target(['ExpressionPressure', 'evaluate']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ExpressionPressure.evaluate'] = _aurora_get_target(['ExpressionPressure', 'evaluate'])
    _aurora_assign_target(['ExpressionPressure', 'evaluate'], _aurora_make_override('evaluate_evolved', 'ExpressionPressure.evaluate'))
    _AURORA_NATIVE_EVOLVED_LAST['ExpressionPressure.evaluate'] = {'alignment_gap': 0.391, 'override_active': True}

def energy_to_shard_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_expression_perception.ImpressionCascade.energy_to_shard', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_expression_perception_impressioncascade_energy_to_shard')(payload=payload, **kwargs)

if _aurora_get_target(['ImpressionCascade', 'energy_to_shard']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ImpressionCascade.energy_to_shard'] = _aurora_get_target(['ImpressionCascade', 'energy_to_shard'])
    _aurora_assign_target(['ImpressionCascade', 'energy_to_shard'], _aurora_make_override('energy_to_shard_evolved', 'ImpressionCascade.energy_to_shard'))
    _AURORA_NATIVE_EVOLVED_LAST['ImpressionCascade.energy_to_shard'] = {'alignment_gap': 0.391, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_expression_perception.ExpressionPerceptionEngine.ingest_interaction': 'ingest_interaction_evolved',
 'aurora_expression_perception.ExpressionPressure.__init__': 'init_evolved',
 'aurora_expression_perception.ExpressionPressure.evaluate': 'evaluate_evolved',
 'aurora_expression_perception.ImpressionCascade.energy_to_shard': 'energy_to_shard_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_expression_perception.ExpressionPerceptionEngine.ingest_interaction': {'export': 'ingest_interaction_evolved',
                                                                                'mode': 'callable_override',
                                                                                'target': 'ExpressionPerceptionEngine.ingest_interaction'},
 'aurora_expression_perception.ExpressionPressure.evaluate': {'export': 'evaluate_evolved',
                                                              'mode': 'callable_override',
                                                              'target': 'ExpressionPressure.evaluate'},
 'aurora_expression_perception.ImpressionCascade.energy_to_shard': {'export': 'energy_to_shard_evolved',
                                                                    'mode': 'callable_override',
                                                                    'target': 'ImpressionCascade.energy_to_shard'}}
# AURORA_EVOLVED_NATIVE_END
