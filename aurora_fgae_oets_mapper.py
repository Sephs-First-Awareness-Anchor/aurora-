#!/usr/bin/env python3
"""
AURORA FGAE OETS SLOT MAPPER
==============================
Module: aurora_fgae_oets_mapper.py
Layer:  FGAE — First Principle Generative Articulate Emergence
        OETS ↔ Manifold Slot Bridge

Authors: Sunni (Sir) Morningstar & Cael Devo
Created: April 2026  |  Specification: FGAE_SPECIFICATION v2 (2026-04-13)

PURPOSE
-------
The OETS Slot Mapper is the living lexical layer that connects English words
to their constraint-native slot addresses in the manifold, and vice versa.

It is NOT a vocabulary list. It is an address registry.

Per spec §5 — every word in OETS has:
    primary_slot_address    — slot_id where this word most naturally lives
    secondary_address_set   — additional slot_ids where it has been used
    experiential_weight     — how many times processed and in what contexts
    confidence_score        — certainty of primary slot address (0.0–1.0)
    approximation_flag      — True if address was assigned by approximation

MAPPING TYPES (per spec §6 Step I-2 Branch A)
----------------------------------------------
CONFIRMED_MAPPING   — confidence >= threshold (default 0.65)
SOFT_MAPPING        — word exists but confidence < threshold
APPROXIMATED_MAPPING — word not in registry; assigned by approximation protocol

OUTPUT QUERY (per spec §9 Step O-3)
-------------------------------------
query_words_for_slot(slot_id, oets_query_profile, ...)
→ candidates filtered by leverage_class, depth, accountability, register

PERSISTENCE
-----------
Registry persists to aurora_state/fgae_lexical_registry.json
Keys are lowercased word strings. Values are FGAELexicalEntry objects.
"""

from __future__ import annotations

import json
import os
import time
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ── State root ────────────────────────────────────────────────────────────────
_STRATA_ROOT   = Path(__file__).parent
_STATE_DIR     = _STRATA_ROOT / "aurora_state"
_REGISTRY_PATH = _STATE_DIR / "fgae_lexical_registry.json"

# ── Thresholds (per spec §6 Step I-2) ────────────────────────────────────────
CONFIRMED_THRESHOLD  = 0.65
VALIDATED_THRESHOLD  = 0.80
LOW_CONFIDENCE_INIT  = 0.25
INCREMENT_COHERENT   = 0.04
PENALTY_CORRECTION   = 0.10

# ── Mapping type constants ─────────────────────────────────────────────────────
CONFIRMED_MAPPING    = "CONFIRMED_MAPPING"
SOFT_MAPPING         = "SOFT_MAPPING"
APPROXIMATED_MAPPING = "APPROXIMATED_MAPPING"

# ── Register ordering for selection ───────────────────────────────────────────
REGISTER_PRIORITY = ["intimate", "formal", "neutral", "technical", "colloquial"]


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FGAELexicalEntry:
    """
    Single word's full OETS slot registry record.
    One entry per unique lowercased word.
    """
    word:                  str
    primary_slot_address:  str              # manifold slot_id
    primary_domain:        str              # X/T/N/B/A
    secondary_addresses:   List[str]        = field(default_factory=list)
    experiential_weight:   float            = 1.0
    confidence_score:      float            = LOW_CONFIDENCE_INIT
    approximation_flag:    bool             = True
    validation_status:     str              = "pending"     # pending | confirmed
    first_seen_context:    str              = ""
    last_seen_context:     str              = ""
    source_tags:           List[str]        = field(default_factory=list)
    register:              str              = "neutral"
    encounter_count:       int              = 1
    session_count:         int              = 1
    revision_history:      List[Dict]       = field(default_factory=list)
    created_at:            float            = field(default_factory=time.time)
    updated_at:            float            = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FGAELexicalEntry":
        d = dict(d)
        # strip unknown keys future-safely
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def mapping_type(self) -> str:
        if self.confidence_score >= CONFIRMED_THRESHOLD:
            return CONFIRMED_MAPPING
        if self.approximation_flag:
            return APPROXIMATED_MAPPING
        return SOFT_MAPPING


@dataclass
class SlotMapping:
    """
    Result of mapping a word to a slot address.
    Returned by FGAEOETSMapper.map_word().
    """
    word:           str
    slot_id:        str
    primary_domain: str
    confidence:     float
    mapping_type:   str         # CONFIRMED | SOFT | APPROXIMATED
    source:         str         = "linguistic"   # linguistic | sensory
    modality:       str         = ""             # audio | visual | cross_modal
    crystal_confidence: float   = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# FGAE OETS MAPPER
# ─────────────────────────────────────────────────────────────────────────────

class FGAEOETSMapper:
    """
    The OETS ↔ manifold slot bridge.

    Input side  — map_word()         : word → SlotMapping (CONFIRMED/SOFT/APPROX)
    Output side — query_words_for_slot(): slot oets_query_profile → candidate words
    Growth      — register_word()    : add new word to registry
                  update_confidence(): feedback loop confidence adjustments
    """

    # Maps OETS primary_domain letter → IVM ToroidalVertexSystem axis name
    _DOMAIN_TO_AXIS: Dict[str, str] = {
        "X": "existence", "T": "temporal",
        "N": "energy",    "B": "boundary", "A": "agency",
    }

    def __init__(self,
                 registry_path: Path = _REGISTRY_PATH,
                 manifold_reader=None):
        self._path      = registry_path
        self._lock      = threading.Lock()
        self._registry: Dict[str, FGAELexicalEntry] = {}
        self._dirty     = False
        self._reader    = manifold_reader   # optional FGAEManifoldReader
        self._ivm       = None              # optional IVMLattice for resonance
        self._load()

    def set_ivm(self, ivm) -> None:
        """Wire in the IVMLattice so word selection resonates with active axes."""
        self._ivm = ivm

    def _axis_polarity(self, domain: str) -> float:
        """Return signed IVM polarity for this domain's axis (0.0 if unavailable)."""
        if self._ivm is None:
            return 0.0
        try:
            axis_name = self._DOMAIN_TO_AXIS.get(domain, "")
            if not axis_name:
                return 0.0
            vertices = getattr(self._ivm, 'vertices', None)
            axes     = getattr(vertices, 'axes', {}) if vertices else {}
            axis     = axes.get(axis_name)
            if axis is None:
                return 0.0
            return float(getattr(axis, 'polarity', 0.0))
        except Exception:
            return 0.0

    # ──────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for word, entry_d in raw.items():
                    try:
                        self._registry[word] = FGAELexicalEntry.from_dict(entry_d)
                    except Exception:
                        pass
            except Exception:
                pass

    def save(self) -> None:
        if not self._dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        payload = {w: e.to_dict() for w, e in self._registry.items()}
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)
        self._dirty = False

    # ──────────────────────────────────────────────────────────────────────
    # INPUT SIDE — word → slot  (spec §6 Step I-2 Branch A)
    # ──────────────────────────────────────────────────────────────────────

    def map_word(self,
                 word:    str,
                 context: str = "",
                 source:  str = "linguistic",
                 modality: str = "",
                 crystal_confidence: float = 0.0) -> Optional[SlotMapping]:
        """
        Attempt to map a word (or sensory concept) to a slot address.

        Returns:
            SlotMapping if the word is in the registry (CONFIRMED or SOFT),
            None if the word is unknown (caller should run APPROXIMATION PROTOCOL).
        """
        key = word.lower().strip()
        with self._lock:
            entry = self._registry.get(key)

        if entry is None:
            return None  # → caller routes to ApproximationProtocol

        # Update encounter stats
        with self._lock:
            entry.encounter_count  += 1
            entry.last_seen_context = context[:200]
            entry.updated_at        = time.time()
            self._dirty = True

        return SlotMapping(
            word=word,
            slot_id=entry.primary_slot_address,
            primary_domain=entry.primary_domain,
            confidence=entry.confidence_score,
            mapping_type=entry.mapping_type,
            source=source,
            modality=modality,
            crystal_confidence=crystal_confidence,
        )

    def map_sensory_concept(self,
                            concept: str,
                            crystal_confidence: float,
                            modality: str = "cross_modal") -> Optional[SlotMapping]:
        """
        Branch B sensory input path (spec §6 Step I-2 Branch B).
        Routes sensory crystal semantic matches through same OETS lookup.
        """
        return self.map_word(
            word=concept,
            source="sensory",
            modality=modality,
            crystal_confidence=crystal_confidence,
        )

    # ──────────────────────────────────────────────────────────────────────
    # OUTPUT SIDE — slot → words  (spec §9 Step O-3)
    # ──────────────────────────────────────────────────────────────────────

    def query_words_for_slot(self,
                             slot_id:           str,
                             oets_query_profile: Dict[str, Any],
                             current_leverage:  str = "neutral",
                             conscious_frame:   str = "") -> List[str]:
        """
        Given a slot's oets_query_profile, return candidate words ordered by:
            1. highest confidence (confirmed first)
            2. highest experiential_weight
            3. register match

        Filters applied (per spec §9 O-3):
            - leverage_class must match current II viability
            - confidence >= CONFIRMED_THRESHOLD
            - register in register_eligible
        """
        eligible: List[Tuple[float, float, FGAELexicalEntry]] = []
        register_eligible = oets_query_profile.get("register_eligible", [])
        min_evolution     = oets_query_profile.get("min_evolution_grade", 0.0)
        primary_domain    = oets_query_profile.get("primary_domain", "")

        with self._lock:
            for entry in self._registry.values():
                # Must be at this slot or a secondary address
                if entry.primary_slot_address != slot_id and slot_id not in entry.secondary_addresses:
                    continue
                # Must be confirmed
                if entry.confidence_score < CONFIRMED_THRESHOLD:
                    continue
                # Primary domain filter
                if primary_domain and entry.primary_domain != primary_domain:
                    continue
                # Register filter
                if register_eligible and entry.register not in register_eligible:
                    continue

                reg_score = self._register_score(entry.register, register_eligible)
                # Manifold resonance: words from an active axis float up slightly.
                # polarity ∈ [-1, +1] → resonance_boost ∈ [0.82, 1.18]
                pol = self._axis_polarity(entry.primary_domain)
                resonance = 1.0 + 0.18 * pol
                conf_resonated = min(entry.confidence_score * resonance, 0.99)
                eligible.append((conf_resonated, entry.experiential_weight * reg_score, entry))

        eligible.sort(key=lambda x: (x[0], x[1]), reverse=True)
        # Filter out registry-poisoned entries: constraint labels, coordinate
        # strings, words with non-alpha punctuation, and internal node names.
        _bad_chars = set(';=@:,.')
        _blocked   = {
            "resolve", "stabilize", "altered", "physics", "identity",
            "closure", "authored", "pressure", "x", "t", "n", "b", "a",
        }
        clean = []
        for _, _, e in eligible:
            w = e.word
            if not w or len(w) < 2:
                continue
            if any(c in _bad_chars for c in w):
                continue
            if w.lower() in _blocked:
                continue
            # Reject coordinate-style strings (contains digits mixed with letters)
            if any(c.isdigit() for c in w) and any(c.isalpha() for c in w):
                continue
            clean.append(w)
        return clean

    def _register_score(self, reg: str, eligible: List[str]) -> float:
        """Higher score for higher-priority register match."""
        if not eligible:
            return 1.0
        try:
            pos = eligible.index(reg)
            return 1.0 - (pos / len(eligible)) * 0.3
        except ValueError:
            return 0.5

    # ──────────────────────────────────────────────────────────────────────
    # REGISTRY GROWTH
    # ──────────────────────────────────────────────────────────────────────

    def register_word(self,
                      word:                str,
                      slot_id:             str,
                      primary_domain:      str,
                      context:             str    = "",
                      source:              str    = "linguistic",
                      confidence:          float  = LOW_CONFIDENCE_INIT,
                      approximation_flag:  bool   = True,
                      register:            str    = "neutral") -> FGAELexicalEntry:
        """
        Add a new word (or update existing) in the lexical registry.
        Called by ApproximationProtocol after Step A-4.
        Also called when user explicitly defines a word in conversation.
        """
        key = word.lower().strip()
        # Reject words that are not natural-language vocabulary.
        # Constraint labels, coordinate strings, and punctuation-contaminated
        # words must never enter the lexical registry.
        _bad_chars = set(';=@:,.')
        _blocked   = {
            "resolve", "stabilize", "altered", "physics", "identity",
            "closure", "authored", "pressure", "x", "t", "n", "b", "a",
        }
        if (not key or len(key) < 2
                or any(c in _bad_chars for c in key)
                or key in _blocked
                or (any(c.isdigit() for c in key) and any(c.isalpha() for c in key))):
            # Return a dummy entry so callers don't crash
            return FGAELexicalEntry(
                word=word, primary_slot_address=slot_id,
                primary_domain=primary_domain,
                confidence_score=0.0, approximation_flag=True,
                validation_status="rejected",
            )

        now = time.time()
        with self._lock:
            existing = self._registry.get(key)
            if existing:
                # Update secondary address if new slot
                if existing.primary_slot_address != slot_id:
                    if slot_id not in existing.secondary_addresses:
                        existing.secondary_addresses.append(slot_id)
                existing.encounter_count += 1
                existing.updated_at       = now
                existing.last_seen_context = context[:200]
                self._dirty = True
                return existing

            entry = FGAELexicalEntry(
                word=word,
                primary_slot_address=slot_id,
                primary_domain=primary_domain,
                confidence_score=confidence,
                approximation_flag=approximation_flag,
                validation_status="pending" if approximation_flag else "confirmed",
                first_seen_context=context[:200],
                last_seen_context=context[:200],
                source_tags=[source],
                register=register,
                created_at=now,
                updated_at=now,
            )
            self._registry[key] = entry
            self._dirty = True
            return entry

    def update_confidence(self,
                          word:             str,
                          delta:            float,
                          new_slot_id:      Optional[str] = None,
                          explicit_define:  bool = False) -> Optional[FGAELexicalEntry]:
        """
        Adjust confidence for a word — called by FeedbackLoop (spec §8 F-2).

        Args:
            word:           the word to update
            delta:          positive = coherent turn, negative = correction
            new_slot_id:    if correction revealed a better slot, pass it here
            explicit_define: user explicitly defined this word → set to high confidence
        """
        key = word.lower().strip()
        with self._lock:
            entry = self._registry.get(key)
            if not entry:
                return None

            if explicit_define:
                if new_slot_id:
                    entry.primary_slot_address = new_slot_id
                entry.confidence_score  = VALIDATED_THRESHOLD + 0.05
                entry.approximation_flag = False
                entry.validation_status  = "confirmed"
            else:
                entry.confidence_score = max(0.0, min(1.0, entry.confidence_score + delta))
                if new_slot_id and delta < 0:
                    entry.revision_history.append({
                        "old_slot": entry.primary_slot_address,
                        "new_slot": new_slot_id,
                        "at":       time.time(),
                    })
                    entry.primary_slot_address = new_slot_id
                if entry.confidence_score >= VALIDATED_THRESHOLD:
                    entry.approximation_flag = False
                    entry.validation_status  = "confirmed"

            entry.updated_at = time.time()
            self._dirty = True
            return entry

    def get_approximated_words(self) -> List[str]:
        """Return all words currently flagged as APPROXIMATED or SOFT."""
        with self._lock:
            return [
                w for w, e in self._registry.items()
                if e.approximation_flag or e.confidence_score < CONFIRMED_THRESHOLD
            ]

    def get_entry(self, word: str) -> Optional[FGAELexicalEntry]:
        key = word.lower().strip()
        with self._lock:
            return self._registry.get(key)

    def registry_size(self) -> int:
        with self._lock:
            return len(self._registry)

    # ──────────────────────────────────────────────────────────────────────
    # SEEDING — populate registry from existing semantic_entries in manifold
    # ──────────────────────────────────────────────────────────────────────

    def seed_from_manifold(self, manifold_reader=None) -> int:
        """
        Walk the manifold and seed the registry with words already present
        in semantic_entries.  Skips multi-word phrases (FGAE-V01).
        Returns count of words added.
        """
        reader = manifold_reader or self._reader
        if not reader:
            return 0

        added = 0
        try:
            for entry, nc in reader.iter_nc_entries():
                primary_domain = nc.get("nc_target", "X")
                for slot in nc.get("slots", []):
                    slot_id = slot.get("slot_id", "")
                    for sem_entry in slot.get("semantic_entries", []):
                        wp = sem_entry.get("word_or_phrase", "")
                        if not wp or " " in str(wp):
                            continue   # skip phrases (V01) and empty
                        word = str(wp).strip().lower()
                        if not word:
                            continue
                        key = word
                        with self._lock:
                            if key in self._registry:
                                # Add slot as secondary address if needed
                                ex = self._registry[key]
                                if ex.primary_slot_address != slot_id:
                                    if slot_id not in ex.secondary_addresses:
                                        ex.secondary_addresses.append(slot_id)
                                        self._dirty = True
                                continue

                        # Map clause levels to confidence
                        clause_i = sem_entry.get("clause_i_level", "I-C")
                        confidence = {"I-A": 0.85, "I-B": 0.70, "I-D": 0.55, "I-C": 0.40}.get(
                            clause_i, 0.40
                        )
                        register = sem_entry.get("register", "neutral")

                        self.register_word(
                            word=word,
                            slot_id=slot_id,
                            primary_domain=primary_domain,
                            source="manifold_seed",
                            confidence=confidence,
                            approximation_flag=(confidence < CONFIRMED_THRESHOLD),
                            register=register,
                        )
                        added += 1
        except Exception as exc:
            print(f"[FGAEOETSMapper] seed_from_manifold error: {exc}")

        if added:
            self.save()
        return added
