#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_concept_derivation.py — Live concept assignment and derivation engine.

WHAT THIS IS
============
The bridge that was missing between Aurora's three vocabulary layers:

    Lexicon   (words + functional role)
    OETS web  (concept nodes + ontological depth)
    Noncomp   (constraint-axis crystal channels)

When a new word arrives during ingestion the lexicon entry gets:
    noncomp_id = None        ← no concept assignment
    meaning    = "learned:X" ← placeholder, not real

This module fixes that. It runs during every live ingest and does:

  1. GEOMETRY EXTRACTION — extracts the constraint axis profile of the
     sentence the word arrived in (same extractor the corpus runner uses).

  2. CHANNEL DERIVATION — maps (geometry, role, valence, word) → a
     concept channel string like "A:OPERATOR" or "B:DIFFERENCE".
     Multiple words that arrive in geometrically similar contexts and
     share the same functional role collapse to the same channel.
     This is the compounding the architecture always intended.

  3. CONCEPT CREATION — if the derived channel is genuinely new (not
     present in the lexicon's noncomp index AND not present in the OETS
     web), a minimal OETS concept node is created for it so the concept
     has ontological depth, not just a string label.

  4. ASSOCIATION — calls lexicon.associate(word, channel) so the word
     joins its concept group and the noncomp_index stays current.

  5. WARP FALLBACK — for words in low-signal / geometry-flat contexts
     (all axis activations ≤ 0.05), a role-lineage fallback channel is
     derived from the word's functional class and the I-state it arrived
     in, so no word is left concept-less.

IMPORT SAFETY
=============
This module imports from neither aurora_expression_perception nor
corpus_runner at module level (both would be circular). All geometry /
channel logic uses lazy function-level imports that are safe once
both modules are fully loaded.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

# ── Axis / I-state constants (mirrored from warp_protocol — no dep) ───────────

_AXES = ("X", "T", "N", "B", "A")

_ISTATE_FOR_AXIS: Dict[str, str] = {
    "X": "I_IS", "T": "I_CAN", "N": "I_DO", "B": "I_SAW", "A": "I_DID",
}

# Role → default axis affinity when geometry is flat
_ROLE_AXIS_FALLBACK: Dict[str, str] = {
    "verb":      "A",   # agency — verbs encode action
    "noun":      "X",   # existence — nouns name things that are
    "adjective": "B",   # boundary — adjectives define limits/qualities
    "adverb":    "N",   # energy — adverbs modulate force/intensity
}

# I-state → axis mapping for lineage-based fallback channels
_ISTATE_AXIS: Dict[str, str] = {
    "i_is":    "X", "i_isnt":   "X",
    "i_can":   "T", "i_cannot": "T",
    "i_do":    "N", "i_donot":  "N",
    "i_saw":   "B", "i_sought": "B",
    "i_did":   "A", "i_didnt":  "A",
}


# ══════════════════════════════════════════════════════════════════════════════
# CORE API
# ══════════════════════════════════════════════════════════════════════════════

def assign_word_concept(
    word: str,
    role: str,
    valence: float,
    text_context: str,
    lexicon: Any,
    oets: Any = None,
    i_state: str = "i_is",
    *,
    perception: Any = None,
) -> str:
    """
    Derive the concept channel for `word` and associate it in the lexicon.

    Returns the channel string (e.g. "A:OPERATOR") or "" if nothing could
    be derived. Always safe to call — all failures are caught silently.

    Parameters
    ----------
    word         : the token being ingested
    role         : its functional role (verb / noun / adjective / adverb)
    valence      : emotional valence [-1, +1]
    text_context : the full sentence/utterance the word arrived in
    lexicon      : live Lexicon instance (from ExpressionPerceptionEngine)
    oets         : optional OntologicalScaffoldingEngine — used to create a
                   concept node when the channel is new
    i_state      : the I-state context of the ingest turn (e.g. "i_is")
    perception   : optional ExpressionPerceptionEngine for character_affinity
    """
    if not word or not role:
        return ""

    channel = ""

    # ── Step 1: geometry-driven derivation ────────────────────────────────────
    geom = _extract_geometry(text_context)
    if geom is not None:
        channel = _derive_channel(geom, role, valence, word, perception)

    # ── Step 2: WARP fallback when geometry is flat ───────────────────────────
    if not channel:
        channel = _fallback_channel(word, role, i_state)

    if not channel:
        return ""

    # ── Step 3: associate word → channel in lexicon ───────────────────────────
    _associate_in_lexicon(word, channel, lexicon)

    # ── Step 4: ensure an OETS concept node exists for this channel ───────────
    if oets is not None:
        _ensure_oets_concept(channel, word, role, geom, oets)

    return channel


def assign_batch(
    word_role_valence: list,
    text_context: str,
    lexicon: Any,
    oets: Any = None,
    i_state: str = "i_is",
    *,
    perception: Any = None,
) -> Dict[str, str]:
    """
    Assign concept channels to a batch of (word, role, valence) tuples
    from the same sentence. Extracts geometry once and reuses it.

    Returns {word: channel} for every word that got a channel.
    """
    geom = _extract_geometry(text_context)
    results: Dict[str, str] = {}

    for word, role, valence in word_role_valence:
        if not word or not role:
            continue
        channel = ""
        if geom is not None:
            channel = _derive_channel(geom, role, valence, word, perception)
        if not channel:
            channel = _fallback_channel(word, role, i_state)
        if not channel:
            continue
        _associate_in_lexicon(word, channel, lexicon)
        if oets is not None:
            _ensure_oets_concept(channel, word, role, geom, oets)
        results[word] = channel

    return results


# ══════════════════════════════════════════════════════════════════════════════
# INTERNALS
# ══════════════════════════════════════════════════════════════════════════════

_geom_extractor = None  # module-level singleton, lazy-loaded


def _extract_geometry(text: str) -> Optional[Any]:
    """Extract ComparisonGeometry from text. Returns None on any failure."""
    global _geom_extractor
    if not text or not text.strip():
        return None
    try:
        if _geom_extractor is None:
            from corpus_runner import GeometryExtractor
            _geom_extractor = GeometryExtractor()
        return _geom_extractor.extract(text)
    except Exception:
        return None


def _derive_channel(geom: Any, role: str, valence: float, word: str,
                    perception: Any = None) -> str:
    """Derive noncomp concept channel from geometry + word properties."""
    try:
        from corpus_runner import derive_noncomp_channel
        return derive_noncomp_channel(geom, role, valence, word) or ""
    except Exception:
        return ""


def _fallback_channel(word: str, role: str, i_state: str) -> str:
    """
    Role + I-state derived fallback for words arriving in geometry-flat contexts.
    Ensures no word is left concept-less just because its utterance had low
    constraint signal (e.g. very short phrases, function words).
    """
    axis = (
        _ISTATE_AXIS.get(i_state.lower(), None)
        or _ROLE_AXIS_FALLBACK.get(role, None)
    )
    if not axis:
        return ""
    char_map = {
        "verb":      "OPERATOR",
        "noun":      "MAGNITUDE",
        "adjective": "POLARITY",
        "adverb":    "COST",
    }
    char = char_map.get(role, "MAGNITUDE")
    return f"{axis}:{char}"


def _associate_in_lexicon(word: str, channel: str, lexicon: Any) -> None:
    """Call lexicon.associate() safely — adds word to its concept group."""
    try:
        if lexicon is not None and hasattr(lexicon, "associate"):
            lexicon.associate(word, channel, strength=0.8)
    except Exception:
        pass


def _ensure_oets_concept(
    channel: str,
    word: str,
    role: str,
    geom: Any,
    oets: Any,
) -> None:
    """
    Create a minimal OETS concept node for `channel` if one does not exist.

    The node is keyed by the channel string (e.g. "A:OPERATOR") so it
    represents the CONCEPT, not just this one word. The word that triggered
    creation is recorded as the seed, but other words will join later as
    concept_words() accumulates them.

    Axis/I-state provenance is derived from the channel's axis prefix and
    stored in the node's `lineage` field so WARP can use it.
    """
    if oets is None:
        return
    try:
        # OETS engine stores nodes in oets.web.nodes (OntologicalWeb.nodes).
        web = getattr(oets, "web", oets)
        nodes = getattr(web, "nodes", None)
        if nodes is None:
            return
        if channel in nodes:
            return  # already exists

        # Derive I-state for this channel's axis
        axis = channel.split(":")[0]
        i_state = _ISTATE_FOR_AXIS.get(axis, "I_IS")

        # Build axis profile from geometry or uniform fallback
        axis_profile: Dict[str, float] = {}
        if geom is not None:
            for ax in _AXES:
                v = float(getattr(geom, f"{ax.lower()}_activation", 0.0) or 0.0)
                axis_profile[ax] = round(v, 3)
        else:
            axis_profile = {ax: (0.6 if ax == axis else 0.1) for ax in _AXES}

        # Use the web's own add_node() to create a proper SemanticNode so the
        # serialiser never encounters a raw dict. Derived concept nodes are
        # keyed by the channel string (e.g. "A:OPERATOR") rather than a word.
        node = web.add_node(
            channel, role,
            valence=0.0,
            meaning=f"derived:{word}",
            lineage=i_state,
        )
        # Attach axis profile and seed info as non-standard fields so WARP /
        # RelationalComparisonEngine can consume them without OETS changes.
        node.axis_profile = axis_profile
        node.seed_word = word
        node.concept_channel = channel
    except Exception:
        pass
