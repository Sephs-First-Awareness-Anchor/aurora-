#!/usr/bin/env python3
"""
AURORA GRAMMAR ENGINE
=====================
Grammar as evolved behavior, not formatting rules.

Sentence structure emerges from the same evolutionary pressure system that
governs Aurora's cognition.  Structural motifs are promoted through the
constraint genealogy when they survive clarity + constraint pressure -- the
exact same mechanism that promotes OUTLET_PUSH and every other behavior.

Doctrine:
  Grammar is the compressed map of surviving structural patterns.
  Clear structure is the lowest-energy path to A-axis relief.
  So grammatical order does not need to be taught -- it needs to be the
  path of least resistance through the constraint system.

Pipeline:
  token -> role_tag -> pattern_extract -> motif_select -> slot_fill ->
  genealogy_relief_log -> promote/penalize

Bootstrap (run once via /grammarboot):
  MotifMiner.mine(corpus) -> seed MotifLineage with top patterns

Reference stability:
  Motifs track which role positions carry entity references across clauses
  so that pronouns ("it", "this") resolve correctly to prior agents.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import re
import json
import time
import hashlib
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict, deque
from enum import Enum


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _genealogy_from_role_sequence(role_sequence: Tuple["TokenRole", ...]) -> str:
    """
    Derive ACMS constraint genealogy from a motif's structural role composition.

    Per ACMS §VII.7, language axes map directly to constraint axes:
      AGENT     → X  (existence / speaker presence)
      ACTION    → A  (agency / enactment)
      OBJECT    → N  (energy / semantic force of content)
      CONTEXT   → T  (time / epistemic framing)
      CONNECTOR → T  (temporal sequencing, also contributes T)
      DESCRIPTOR→ B  (boundary / qualification / distinction)

    Repeated roles reinforce the corresponding axis (Tier 5 weighting).
    Capped at 2× per axis so genealogy stays parseable.
    """
    counts: Dict[str, int] = {a: 0 for a in ("X", "T", "N", "B", "A")}
    _ROLE_TO_AXIS: Dict[Any, str] = {}
    try:
        _ROLE_TO_AXIS = {
            TokenRole.AGENT:      "X",
            TokenRole.ACTION:     "A",
            TokenRole.OBJECT:     "N",
            TokenRole.CONTEXT:    "T",
            TokenRole.CONNECTOR:  "T",
            TokenRole.DESCRIPTOR: "B",
        }
    except Exception:
        return "XTNBA"
    for role in role_sequence:
        axis = _ROLE_TO_AXIS.get(role)
        if axis:
            counts[axis] += 1
    parts = []
    for axis in ("X", "T", "N", "B", "A"):
        repeat = min(counts[axis], 2)
        if repeat > 0:
            parts.append(axis * repeat)
    return "".join(parts) or "X"


# ---------------------------------------------------------------------------
# Token Roles
# ---------------------------------------------------------------------------

class TokenRole(Enum):
    AGENT      = "agent"        # subject / actor
    ACTION     = "action"       # verb
    OBJECT     = "object"       # direct object / target
    DESCRIPTOR = "descriptor"   # adjective / adverb
    CONNECTOR  = "connector"    # conjunction / discourse connector
    CONTEXT    = "context"      # epistemic / temporal framing ("I think", "maybe")
    UNKNOWN    = "unknown"      # skip in pattern extraction


# ---------------------------------------------------------------------------
# Rule-based Role Tagger  (no external NLP deps)
# ---------------------------------------------------------------------------

class RoleTagger:
    """
    Lightweight rule-based tagger.  No external dependencies.
    Good enough for pattern mining; not a full POS tagger.

    Optional NLTK acceleration (used only during corpus bootstrap):
        from aurora_grammar_engine import RoleTagger
        tagger = RoleTagger(use_nltk=True)
    """

    _CONTEXT_UNIGRAMS: frozenset = frozenset([
        "maybe", "perhaps", "probably", "possibly", "likely", "unlikely",
        "apparently", "seemingly", "somehow", "reportedly", "supposedly",
        "clearly", "honestly", "frankly", "truthfully",
    ])

    _CONTEXT_BIGRAMS: frozenset = frozenset([
        "i think", "i believe", "i suspect", "i notice", "i feel", "i sense",
        "i suppose", "it seems", "it appears", "i wonder", "i imagine",
        "i'm not", "not sure", "i guess",
    ])

    _CONNECTORS: frozenset = frozenset([
        "and", "but", "because", "although", "though", "however", "therefore",
        "so", "yet", "if", "then", "since", "when", "as", "that", "which",
        "who", "while", "unless", "until", "whereas", "despite", "even",
        "furthermore", "moreover", "consequently", "thus", "hence", "meanwhile",
        "nonetheless", "otherwise", "besides", "indeed", "also",
    ])

    _AGENT_PRONOUNS: frozenset = frozenset([
        "i", "you", "she", "he", "it", "we", "they", "aurora",
        "this", "that", "these", "those",
    ])

    # Pronouns that signal a reference anchor (pointing back to prior agent)
    _REFERENCE_PRONOUNS: frozenset = frozenset([
        "it", "this", "that", "they", "these", "those", "which",
    ])

    _VERB_FORMS: frozenset = frozenset([
        "is", "are", "was", "were", "be", "been", "being",
        "has", "have", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might",
        "can", "shall", "must", "need", "dare",
        "seems", "feels", "looks", "appears", "becomes", "remains",
        "means", "works", "runs", "grows", "moves", "shifts",
    ])

    # Possessives are NOT skipped -- "my systems" = the systems are the agent
    _SKIP_TOKENS: frozenset = frozenset([
        "the", "a", "an",
        "of", "in", "on", "at", "to", "for", "by", "with", "from",
        "very", "quite", "just", "really", "so",
    ])

    # Possessives: following noun becomes the agent
    _POSSESSIVES: frozenset = frozenset([
        "my", "your", "its", "their", "our", "his", "her",
    ])

    # Auxiliary verbs -- next -ing word is ACTION (progressive), not DESCRIPTOR
    _AUXILIARIES: frozenset = frozenset([
        "am", "is", "are", "was", "were", "be", "been", "being",
        "has", "have", "had", "will", "would", "could", "should",
        "may", "might", "can", "shall", "must",
    ])

    _DESCRIPTOR_ENDINGS: tuple = (
        "ly", "ful", "ous", "ive", "al", "less", "ible", "able", "ent", "ant",
    )
    _ACTION_ENDINGS: tuple = (
        "ize", "ise", "ate", "ify", "en", "ing", "ed",
    )

    def __init__(self, use_nltk: bool = False):
        self._use_nltk = use_nltk
        self._nltk_tagger = None
        if use_nltk:
            try:
                import nltk
                self._nltk_tagger = nltk.pos_tag
            except Exception:
                self._use_nltk = False

    def tag(self, text: str) -> List[Tuple[str, TokenRole]]:
        """Return list of (token, TokenRole) for the sentence."""
        if self._use_nltk and self._nltk_tagger:
            return self._tag_with_nltk(text)
        return self._tag_rule_based(text)

    def extract_pattern(self, text: str) -> Tuple[TokenRole, ...]:
        """
        Return the collapsed role sequence (no UNKNOWN, no consecutive dupes).
        e.g. "I think the system works well" -> (CONTEXT, AGENT, ACTION, DESCRIPTOR)
        """
        tagged = self.tag(text)
        roles = [r for _, r in tagged if r is not TokenRole.UNKNOWN]
        if not roles:
            return ()
        # Collapse consecutive identical roles
        deduped = [roles[0]]
        for r in roles[1:]:
            if r != deduped[-1]:
                deduped.append(r)
        return tuple(deduped)

    def extract_reference_positions(self, tagged: List[Tuple[str, TokenRole]]) -> List[int]:
        """Return indices where the token is a reference pronoun (-> prior agent)."""
        return [
            i for i, (tok, _) in enumerate(tagged)
            if tok.lower().strip(".,!?;:") in self._REFERENCE_PRONOUNS
        ]

    # -- internal -----------------------------------------------------------

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.findall(r"\b\w[\w']*\w?\b|[^\w\s]", text)
                if re.match(r"\w", t)]

    def _tag_rule_based(self, text: str) -> List[Tuple[str, TokenRole]]:
        tokens = self._tokenize(text)
        if not tokens:
            return []

        result: List[Optional[Tuple[str, TokenRole]]] = [None] * len(tokens)
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            tl = tok.lower().strip(".,!?;:'\"")

            # 2-gram context check
            if i + 1 < len(tokens):
                bigram = tl + " " + tokens[i + 1].lower().strip(".,!?;:'\"")
                if bigram in self._CONTEXT_BIGRAMS:
                    result[i]     = (tok,         TokenRole.CONTEXT)
                    result[i + 1] = (tokens[i+1], TokenRole.CONTEXT)
                    i += 2
                    continue

            if tl in self._CONTEXT_UNIGRAMS:
                result[i] = (tok, TokenRole.CONTEXT)
            elif tl in self._CONNECTORS:
                result[i] = (tok, TokenRole.CONNECTOR)
            elif tl in self._SKIP_TOKENS:
                result[i] = (tok, TokenRole.UNKNOWN)
            elif tl in self._POSSESSIVES:
                # Possessive: mark as UNKNOWN, make next word AGENT
                result[i] = (tok, TokenRole.UNKNOWN)
                if i + 1 < len(tokens) and result[i + 1] is None:
                    result[i + 1] = (tokens[i + 1], TokenRole.AGENT)
                i += 1
                continue
            elif tl in self._AGENT_PRONOUNS:
                result[i] = (tok, TokenRole.AGENT)
            elif tl in self._VERB_FORMS:
                result[i] = (tok, TokenRole.ACTION)
            # suffix-based
            elif any(tl.endswith(e) for e in self._DESCRIPTOR_ENDINGS) and len(tl) > 4:
                result[i] = (tok, TokenRole.DESCRIPTOR)
            elif tl.endswith("ing") and len(tl) > 4:
                # Progressive -ing after auxiliary = ACTION; after noun/object = DESCRIPTOR
                prev_tok = tokens[i - 1].lower().strip(".,!?;:'\"") if i > 0 else ""
                prev_role_val = result[i - 1][1] if i > 0 and result[i - 1] else None
                if prev_tok in self._AUXILIARIES or prev_role_val is TokenRole.AGENT:
                    result[i] = (tok, TokenRole.ACTION)
                else:
                    result[i] = (tok, TokenRole.DESCRIPTOR)
            elif any(tl.endswith(e) for e in self._ACTION_ENDINGS) and len(tl) > 4:
                result[i] = (tok, TokenRole.ACTION)
            i += 1

        # Second pass: fill None by position
        prev_role: Optional[TokenRole] = None
        for i, item in enumerate(result):
            if item is not None:
                prev_role = item[1]
                continue
            tok = tokens[i]
            if i == 0:
                result[i] = (tok, TokenRole.AGENT)
            elif prev_role is TokenRole.AGENT:
                result[i] = (tok, TokenRole.ACTION)
            elif prev_role is TokenRole.ACTION:
                result[i] = (tok, TokenRole.OBJECT)
            elif prev_role is TokenRole.OBJECT:
                result[i] = (tok, TokenRole.DESCRIPTOR)
            else:
                result[i] = (tok, TokenRole.UNKNOWN)
            prev_role = result[i][1]  # type: ignore[index]

        return [item for item in result if item is not None]  # type: ignore[misc]

    def _tag_with_nltk(self, text: str) -> List[Tuple[str, TokenRole]]:
        """NLTK POS -> simplified TokenRole mapping."""
        _POS_MAP = {
            "NN": TokenRole.OBJECT, "NNS": TokenRole.OBJECT,
            "NNP": TokenRole.AGENT, "NNPS": TokenRole.AGENT,
            "PRP": TokenRole.AGENT, "PRP$": TokenRole.AGENT,
            "VB":  TokenRole.ACTION, "VBD": TokenRole.ACTION,
            "VBG": TokenRole.ACTION, "VBN": TokenRole.ACTION,
            "VBP": TokenRole.ACTION, "VBZ": TokenRole.ACTION,
            "MD":  TokenRole.ACTION,
            "JJ":  TokenRole.DESCRIPTOR, "JJR": TokenRole.DESCRIPTOR,
            "JJS": TokenRole.DESCRIPTOR, "RB": TokenRole.DESCRIPTOR,
            "RBR": TokenRole.DESCRIPTOR, "RBS": TokenRole.DESCRIPTOR,
            "CC":  TokenRole.CONNECTOR, "IN": TokenRole.CONNECTOR,
            "WDT": TokenRole.CONNECTOR, "WP": TokenRole.CONNECTOR,
            "WRB": TokenRole.CONNECTOR,
            "UH":  TokenRole.CONTEXT,
        }
        tokens = self._tokenize(text)
        try:
            pos_tagged = self._nltk_tagger(tokens)
            return [(tok, _POS_MAP.get(pos, TokenRole.UNKNOWN))
                    for tok, pos in pos_tagged]
        except Exception:
            return self._tag_rule_based(text)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StructuralMotif:
    """
    A promoted sentence structure pattern -- the basic unit of evolved grammar.

    Fields:
      role_sequence     -- the role order pattern (tuple of TokenRole)
      reference_anchors -- list of (role_pos_A, role_pos_B) pairs meaning those
                           two positions refer to the same entity.  Enables
                           pronoun resolution across clauses.
      constraint_scores -- per-axis fit score [0,1].  Updated from genealogy
                           orientation at time of successful use.
      compression_score -- reward for economy (fewer tokens, same clarity).
    """
    pattern_id:        str
    role_sequence:     Tuple[TokenRole, ...]
    success_count:     int             = 0
    fail_count:        int             = 0
    contexts_seen:     Set[str]        = field(default_factory=set)
    constraint_scores: Dict[str, float] = field(
        default_factory=lambda: {a: 0.5 for a in ("X", "T", "N", "B", "A")}
    )
    child_patterns:     List[str]      = field(default_factory=list)
    parent_pattern_id:  Optional[str]  = None
    reference_anchors:  List[Tuple[int, int]] = field(default_factory=list)
    promoted:           bool           = False
    generation:         int            = 0
    compression_score:  float          = 0.0
    total_tokens_avg:   float          = 0.0
    # CBU profile — registered with CBURegistry when motif is promoted (CBU directive Step 9)
    cbu_profile:        Any            = field(default=None, repr=False, compare=False)

    # ---- scoring ----------------------------------------------------------

    def composability_score(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        freq      = self.success_count / total
        diversity = _clamp(len(self.contexts_seen) / 15.0)
        return freq * diversity

    def should_promote(self) -> bool:
        return (self.success_count >= 5
                and len(self.contexts_seen) >= 3
                and self.composability_score() > 0.30)

    def should_demote(self) -> bool:
        total = self.success_count + self.fail_count
        return total >= 8 and (self.fail_count / total) > 0.65

    # ---- serialization ----------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "pattern_id":       self.pattern_id,
            "role_sequence":    [r.value for r in self.role_sequence],
            "success_count":    self.success_count,
            "fail_count":       self.fail_count,
            "contexts_seen":    list(self.contexts_seen),
            "constraint_scores": self.constraint_scores,
            "child_patterns":   self.child_patterns,
            "parent_pattern_id": self.parent_pattern_id,
            "reference_anchors": self.reference_anchors,
            "promoted":         self.promoted,
            "generation":       self.generation,
            "compression_score": self.compression_score,
            "total_tokens_avg": self.total_tokens_avg,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "StructuralMotif":
        _valid = {r.value for r in TokenRole}
        seq = tuple(TokenRole(r) for r in d.get("role_sequence", []) if r in _valid)
        return cls(
            pattern_id        = d["pattern_id"],
            role_sequence     = seq,
            success_count     = d.get("success_count", 0),
            fail_count        = d.get("fail_count", 0),
            contexts_seen     = set(d.get("contexts_seen", [])),
            constraint_scores = d.get("constraint_scores",
                                      {a: 0.5 for a in ("X", "T", "N", "B", "A")}),
            child_patterns    = d.get("child_patterns", []),
            parent_pattern_id = d.get("parent_pattern_id"),
            reference_anchors = [tuple(x) for x in d.get("reference_anchors", [])],
            promoted          = d.get("promoted", False),
            generation        = d.get("generation", 0),
            compression_score = d.get("compression_score", 0.0),
            total_tokens_avg  = d.get("total_tokens_avg", 0.0),
        )


@dataclass
class DiscourseMotif:
    """Turn-level discourse transition pattern."""
    pattern_id:    str
    turn_sequence: Tuple[str, ...]
    success_count: int  = 0
    fail_count:    int  = 0
    promoted:      bool = False

    def to_dict(self) -> Dict:
        return {
            "pattern_id":    self.pattern_id,
            "turn_sequence": list(self.turn_sequence),
            "success_count": self.success_count,
            "fail_count":    self.fail_count,
            "promoted":      self.promoted,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "DiscourseMotif":
        return cls(
            pattern_id    = d["pattern_id"],
            turn_sequence = tuple(d.get("turn_sequence", [])),
            success_count = d.get("success_count", 0),
            fail_count    = d.get("fail_count", 0),
            promoted      = d.get("promoted", False),
        )


# ---------------------------------------------------------------------------
# Motif Lineage -- the promoted pattern pool
# ---------------------------------------------------------------------------

class MotifLineage:
    """
    Manages the full motif pool: storage, promotion, penalization.
    This is the grammar's evolved skeleton -- lineage nodes that survived.
    """

    _SAVE_INTERVAL = 50

    def __init__(self, state_path: str):
        self._state_path  = state_path
        self._motifs:     Dict[str, StructuralMotif] = {}
        self._discourse:  Dict[str, DiscourseMotif]  = {}
        self._update_n    = 0
        self._lock        = threading.Lock()
        self._load()

    # ---- pattern key ------------------------------------------------------

    @staticmethod
    def pattern_key(role_sequence: Tuple[TokenRole, ...]) -> str:
        return "_".join(r.value for r in role_sequence)

    # ---- read / write -----------------------------------------------------

    def get_or_create(self, role_sequence: Tuple[TokenRole, ...]) -> StructuralMotif:
        key = self.pattern_key(role_sequence)
        if key not in self._motifs:
            self._motifs[key] = StructuralMotif(
                pattern_id    = key,
                role_sequence = role_sequence,
            )
        return self._motifs[key]

    def record_success(
        self,
        role_sequence:         Tuple[TokenRole, ...],
        context_hash:          str,
        token_count:           int,
        constraint_orientation: Optional[Dict[str, float]] = None,
        reference_anchors:     Optional[List[Tuple[int, int]]] = None,
    ):
        with self._lock:
            m = self.get_or_create(role_sequence)
            m.success_count += 1
            m.contexts_seen.add(context_hash)
            n = m.success_count
            m.total_tokens_avg = (m.total_tokens_avg * (n - 1) + token_count) / n
            # Compression: fewer tokens than average -> positive compression score
            if m.total_tokens_avg > 0:
                m.compression_score = _clamp(
                    1.0 - token_count / (m.total_tokens_avg * 1.4)
                )
            # Absorb constraint orientation into per-axis scores (slow EMA)
            if constraint_orientation:
                for ax, val in constraint_orientation.items():
                    prev = m.constraint_scores.get(ax, 0.5)
                    m.constraint_scores[ax] = _clamp(prev * 0.88 + val * 0.12)
            # Update reference anchors if provided
            if reference_anchors:
                for anchor in reference_anchors:
                    if anchor not in m.reference_anchors:
                        m.reference_anchors.append(anchor)
                        m.reference_anchors = m.reference_anchors[-10:]
            if not m.promoted and m.should_promote():
                m.promoted = True
            self._maybe_save()

    def record_fail(self, role_sequence: Tuple[TokenRole, ...]):
        with self._lock:
            m = self.get_or_create(role_sequence)
            m.fail_count += 1
            if m.promoted and m.should_demote():
                m.promoted = False
                m.cbu_profile = None
            self._maybe_save()

    def get_promoted(self, min_composability: float = 0.0) -> List[StructuralMotif]:
        return [m for m in self._motifs.values()
                if m.promoted and m.composability_score() >= min_composability]

    def best_for_pressure(
        self,
        orientation:     Dict[str, float],
        outlet_fraction: float,
    ) -> Optional[StructuralMotif]:
        """
        Select best promoted motif given the current constraint pressure state.

        Axis orientation (correction > 1.0 = consolidating/reliable) weights
        motifs whose constraint scores match the consolidating axes.
        Outlet fraction boosts AGENT-first patterns (committed voice).
        Compression score rewards economy (N-axis fitness).
        """
        candidates = self.get_promoted(min_composability=0.20)
        if not candidates:
            return None

        def _score(m: StructuralMotif) -> float:
            axis_fit = sum(
                m.constraint_scores.get(ax, 0.5) * _clamp(corr, 0.5, 2.0)
                for ax, corr in orientation.items()
            ) / max(1, len(orientation))
            # Agent-first bonus scales with outlet fraction
            agent_bonus = (
                outlet_fraction * 0.25
                if m.role_sequence and m.role_sequence[0] is TokenRole.AGENT
                else 0.0
            )
            economy = m.compression_score * 0.15
            return m.composability_score() * 0.45 + axis_fit * 0.30 + agent_bonus + economy

        return max(candidates, key=_score)

    def top_for_pressure(
        self,
        orientation:     Dict[str, float],
        outlet_fraction: float,
        n: int = 8,
    ) -> List[StructuralMotif]:
        """Return top-N promoted motifs ranked by pressure score (descending)."""
        candidates = self.get_promoted(min_composability=0.20)
        if not candidates:
            return []

        def _score(m: StructuralMotif) -> float:
            axis_fit = sum(
                m.constraint_scores.get(ax, 0.5) * _clamp(corr, 0.5, 2.0)
                for ax, corr in orientation.items()
            ) / max(1, len(orientation))
            agent_bonus = (
                outlet_fraction * 0.25
                if m.role_sequence and m.role_sequence[0] is TokenRole.AGENT
                else 0.0
            )
            economy = m.compression_score * 0.15
            # S12c CBU-aware: factor in profile_magnitude for promoted motifs with CBU profiles
            # Per §B3: reads pressure_vector magnitude, not phase label
            cbu_bonus = 0.0
            if m.cbu_profile is not None and m.cbu_profile.can_operate():
                cbu_bonus = min(0.10, m.cbu_profile.profile_magnitude() * 0.10)
            return m.composability_score() * 0.45 + axis_fit * 0.30 + agent_bonus + economy + cbu_bonus

        return sorted(candidates, key=_score, reverse=True)[:n]

    def seed_motifs(
        self,
        patterns: List[Tuple[Tuple[TokenRole, ...], int, List[str]]],
    ):
        """Bulk-seed from corpus mining: [(role_seq, freq, context_list)]"""
        with self._lock:
            for role_seq, freq, contexts in patterns:
                if len(role_seq) < 2:
                    continue
                m = self.get_or_create(role_seq)
                m.success_count = max(m.success_count, freq)
                for ctx in contexts[:12]:
                    m.contexts_seen.add(ctx)
                if freq >= 20 and len(contexts) >= 5:
                    m.promoted = True
            self._save()

    def tick_motif_transitions(self, genealogy_logger: Optional[Any] = None) -> int:
        """
        Check promoted motifs for pressure-triggered weight reconfiguration.

        Per ACMS §V: transition fires only when pressure exceeds tolerance —
        never stochastically.  Transformation kind maps to TNB (structured
        transformation) or Tier 5 weight_reconfiguration.

        Returns count of motifs that transitioned this tick.
        """
        transformed = 0
        with self._lock:
            for m in list(self._motifs.values()):
                if not m.promoted or m.cbu_profile is None:
                    continue
                try:
                    pred = m.cbu_profile.predict_transition()
                    if pred.transition_kind not in (
                        "weight_reconfiguration", "regime_shift", "pressure_rise"
                    ):
                        continue
                    old_phase = m.cbu_profile.phase_state
                    m.cbu_profile.phase_state = pred.target_phase
                    # Reinforce dominant axis weight; decay others slightly
                    dominant = pred.dominant_axis
                    for _ax in ("X", "T", "N", "B", "A"):
                        _cur = float(getattr(m.cbu_profile, f"{_ax}_weight", 0.0))
                        if _ax == dominant:
                            setattr(m.cbu_profile, f"{_ax}_weight", min(1.0, _cur + 0.08))
                        else:
                            setattr(m.cbu_profile, f"{_ax}_weight", max(0.0, _cur - 0.02))
                    # Mirror the shift into constraint_scores so motif selection feels it
                    m.constraint_scores[dominant] = min(
                        1.0, m.constraint_scores.get(dominant, 0.5) + 0.04
                    )
                    transformed += 1
                    if genealogy_logger is not None:
                        try:
                            genealogy_logger.record_phase_change(
                                unit_id=m.cbu_profile.unit_id,
                                unit_kind="grammar_motif",
                                old_phase=old_phase,
                                new_phase=pred.target_phase,
                                breached_axis=dominant,
                                profile_snapshot={
                                    "genealogy": m.cbu_profile.genealogy,
                                    "dominant": dominant,
                                    "tier": pred.target_tier.value,
                                    "kind": pred.transition_kind,
                                },
                            )
                        except Exception:
                            pass
                except Exception:
                    pass
        return transformed

    def stats(self) -> Dict:
        total    = len(self._motifs)
        promoted = sum(1 for m in self._motifs.values() if m.promoted)
        return {
            "total":    total,
            "promoted": promoted,
            "promoted_count": promoted,
            "discourse_motifs": len(self._discourse),
        }

    # ---- persistence ------------------------------------------------------

    def _maybe_save(self):
        self._update_n += 1
        if self._update_n % self._SAVE_INTERVAL == 0:
            self._save()

    def save(self):
        self._save()

    def _save(self):
        try:
            data = {
                "motifs":    {k: v.to_dict() for k, v in self._motifs.items()},
                "discourse": {k: v.to_dict() for k, v in self._discourse.items()},
                "saved_at":  time.time(),
            }
            tmp = self._state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self._state_path)
        except Exception:
            pass

    def _load(self):
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path, encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.get("motifs", {}).items():
                    self._motifs[k] = StructuralMotif.from_dict(v)
                for k, v in data.get("discourse", {}).items():
                    self._discourse[k] = DiscourseMotif.from_dict(v)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Slot Filler  -- fill motif role-slots with tokens from context
# ---------------------------------------------------------------------------

class SlotFiller:
    """
    Given a structural motif and a pool of tokens keyed by role, assemble
    a sentence.  Respects reference_anchors so pronouns resolve correctly.
    """

    _REFERENCE_WORDS: Dict[TokenRole, str] = {
        TokenRole.AGENT:  "it",
        TokenRole.OBJECT: "that",
    }

    def fill(
        self,
        motif:      StructuralMotif,
        token_pool: Dict[TokenRole, List[str]],
        raw_text:   str = "",
    ) -> str:
        if not token_pool and raw_text:
            token_pool = self.pool_from_text(raw_text)
        if not token_pool:
            return raw_text

        # Build anchor map: {position -> canonical_token}
        anchor_map: Dict[int, str] = {}
        for pos_a, pos_b in motif.reference_anchors:
            # The first of the pair sets the canonical token
            role_a = motif.role_sequence[pos_a] if pos_a < len(motif.role_sequence) else None
            if role_a and role_a in token_pool and token_pool[role_a]:
                anchor_map[pos_b] = self._REFERENCE_WORDS.get(role_a, "it")

        parts: List[str] = []
        use_idx: Dict[TokenRole, int] = defaultdict(int)

        for idx, role in enumerate(motif.role_sequence):
            if idx in anchor_map:
                parts.append(anchor_map[idx])
                continue
            pool = token_pool.get(role, [])
            if pool:
                parts.append(pool[use_idx[role] % len(pool)])
                use_idx[role] += 1

        sentence = " ".join(parts).strip()
        if not sentence or len(sentence.split()) < 2:
            return raw_text
        return sentence[0].upper() + sentence[1:]

    def pool_from_text(
        self,
        text:   str,
        tagger: Optional[RoleTagger] = None,
    ) -> Dict[TokenRole, List[str]]:
        if tagger is None:
            tagger = RoleTagger()
        tagged = tagger.tag(text)
        pool: Dict[TokenRole, List[str]] = defaultdict(list)
        skip = RoleTagger._SKIP_TOKENS | {"the", "a", "an"}
        for tok, role in tagged:
            if role is not TokenRole.UNKNOWN and tok.lower() not in skip:
                pool[role].append(tok)
        return dict(pool)


# ---------------------------------------------------------------------------
# Corpus Motif Miner  -- offline bootstrap
# ---------------------------------------------------------------------------

class MotifMiner:
    """
    Run once on the chat corpus to extract structural motifs and seed the
    lineage.  After seeding, real-time evolution takes over.
    """

    def __init__(self, use_nltk: bool = False):
        self._tagger = RoleTagger(use_nltk=use_nltk)

    def mine_corpus(
        self,
        corpus_path:  str,
        max_messages: int = 12000,
        top_n:        int = 400,
    ) -> List[Tuple[Tuple[TokenRole, ...], int, List[str]]]:
        """
        Extract top structural motifs.
        Returns: [(role_sequence, frequency, context_hashes)]
        """
        pattern_counts:   Counter              = Counter()
        pattern_contexts: Dict[str, Set[str]]  = defaultdict(set)
        processed = 0

        try:
            with open(corpus_path, encoding="utf-8", errors="replace") as f:
                corpus = json.load(f)
        except Exception:
            return []

        convs = corpus if isinstance(corpus, list) else corpus.get("conversations", [])

        for conv in convs:
            if processed >= max_messages:
                break
            conv_hash = hashlib.md5(
                str(conv)[:60].encode("utf-8", errors="replace")
            ).hexdigest()[:8]

            # Collect message texts -- handles both flat list and ChatGPT mapping format
            texts: List[str] = []
            if isinstance(conv, list):
                # Plain list of message strings or dicts
                texts = [
                    (m.get("content", "") if isinstance(m, dict) else str(m))
                    for m in conv
                ]
            elif isinstance(conv, dict):
                mapping = conv.get("mapping")
                if mapping and isinstance(mapping, dict):
                    # ChatGPT export format: mapping[node_id].message.content.parts
                    for node in mapping.values():
                        msg = node.get("message") if isinstance(node, dict) else None
                        if not msg:
                            continue
                        content = msg.get("content", {})
                        if isinstance(content, dict):
                            parts = content.get("parts", [])
                            for part in parts:
                                if isinstance(part, str) and part.strip():
                                    texts.append(part)
                        elif isinstance(content, str) and content.strip():
                            texts.append(content)
                else:
                    # Flat messages list
                    for m in conv.get("messages", []):
                        t = m.get("content", "") if isinstance(m, dict) else str(m)
                        if t:
                            texts.append(t)

            for text in texts:
                if processed >= max_messages:
                    break
                if not text or len(text) < 6:
                    continue
                for sent in re.split(r"[.!?]+", text):
                    sent = sent.strip()
                    if len(sent.split()) < 3:
                        continue
                    pattern = self._tagger.extract_pattern(sent)
                    if len(pattern) >= 2:
                        key = "_".join(r.value for r in pattern)
                        pattern_counts[key] += 1
                        pattern_contexts[key].add(conv_hash)
                processed += 1

        results = []
        _valid = {r.value for r in TokenRole}
        for key, count in pattern_counts.most_common(top_n):
            parts = key.split("_")
            roles = tuple(TokenRole(p) for p in parts if p in _valid)
            if roles:
                results.append((roles, count, list(pattern_contexts[key])[:20]))
        return results

    def mine_discourse(
        self,
        corpus_path: str,
        max_convs:   int = 2000,
    ) -> List[Tuple[Tuple[str, str], int]]:
        """Extract turn-type bigrams for discourse motifs."""
        try:
            with open(corpus_path, encoding="utf-8", errors="replace") as f:
                corpus = json.load(f)
        except Exception:
            return []

        transitions: Counter = Counter()
        convs = corpus if isinstance(corpus, list) else corpus.get("conversations", [])

        for conv in convs[:max_convs]:
            texts: List[str] = []
            if isinstance(conv, list):
                texts = [(m.get("content", "") if isinstance(m, dict) else str(m))
                         for m in conv]
            elif isinstance(conv, dict):
                mapping = conv.get("mapping")
                if mapping and isinstance(mapping, dict):
                    for node in mapping.values():
                        msg = node.get("message") if isinstance(node, dict) else None
                        if not msg:
                            continue
                        content = msg.get("content", {})
                        if isinstance(content, dict):
                            for part in content.get("parts", []):
                                if isinstance(part, str) and part.strip():
                                    texts.append(part)
                        elif isinstance(content, str) and content.strip():
                            texts.append(content)
                else:
                    texts = [(m.get("content", "") if isinstance(m, dict) else str(m))
                             for m in conv.get("messages", [])]
            prev = None
            for text in texts:
                cur = _classify_turn_type(text)
                if prev and cur:
                    transitions[(prev, cur)] += 1
                prev = cur

        return list(transitions.most_common(60))


# ---------------------------------------------------------------------------
# Discourse Tracker
# ---------------------------------------------------------------------------

class DiscourseTracker:
    """Track turn-level discourse patterns and suggest coherent continuations."""

    def __init__(self, lineage: MotifLineage):
        self._lineage  = lineage
        self._history: deque = deque(maxlen=20)

    def record_turn(self, turn_type: str):
        if self._history:
            prev = self._history[-1]
            key  = f"{prev}_{turn_type}"
            if key not in self._lineage._discourse:
                self._lineage._discourse[key] = DiscourseMotif(
                    pattern_id    = key,
                    turn_sequence = (prev, turn_type),
                )
            dm = self._lineage._discourse[key]
            dm.success_count += 1
            if not dm.promoted and dm.success_count >= 8:
                dm.promoted = True
        self._history.append(turn_type)

    def suggest_next_turn_type(self) -> Optional[str]:
        if not self._history:
            return None
        prev  = self._history[-1]
        best  = None
        score = 0.0
        for dm in self._lineage._discourse.values():
            if dm.promoted and len(dm.turn_sequence) >= 2 and dm.turn_sequence[0] == prev:
                total = dm.success_count + dm.fail_count
                s     = dm.success_count / max(1, total)
                if s > score:
                    best, score = dm.turn_sequence[1], s
        return best


# ---------------------------------------------------------------------------
# Shared turn-type classifier
# ---------------------------------------------------------------------------

def _classify_turn_type(text: str) -> Optional[str]:
    if not text:
        return None
    sl = text.strip().lower()
    if sl.endswith("?") or re.match(r"^(what|why|how|when|where|who|which|can you|do you|is it|are you|will you)\b", sl):
        return "question"
    if any(w in sl for w in ("because", "since", "therefore", "that's why", "the reason")):
        return "explanation"
    if any(w in sl for w in ("for example", "for instance", "such as", "like when")):
        return "evidence"
    if re.match(r"^(yes|no|correct|right|exactly|indeed|sure|absolutely|not quite)\b", sl):
        return "answer"
    if any(w in sl for w in ("i claim", "i argue", "i assert", "i hold that", "i maintain")):
        return "claim"
    return "statement"


# ---------------------------------------------------------------------------
# Grammar Engine  -- top-level coordinator
# ---------------------------------------------------------------------------

class GrammarEngine:
    """
    Top-level grammar evolution engine.

    Key design: grammatical clarity is the path of least resistance to
    A-axis (OUTLET_PUSH) relief.  Every successful exchange is logged to
    the constraint genealogy, making grammar a direct driver of constraint
    relief rather than a separate learning problem.

    Usage:
        engine = GrammarEngine(state_dir="/path/to/aurora_strata/aurora_state")
        engine.set_genealogy(genealogy_logger)   # wire after boot
        suggestion = engine.suggest_structure(raw_expression, context)
        engine.observe_exchange(user_text, aurora_text, success=True)
    """

    def __init__(self, state_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")):
        os.makedirs(state_dir, exist_ok=True)
        state_path        = os.path.join(state_dir, "grammar_motifs.json")
        self._tagger      = RoleTagger()
        self._lineage     = MotifLineage(state_path)
        self._filler      = SlotFiller()
        self._discourse   = DiscourseTracker(self._lineage)
        self._genealogy: Optional[Any] = None
        self._ivm:       Optional[Any] = None
        self._lock        = threading.Lock()
        self._last_motif_id: Optional[str] = None

    def set_genealogy(self, genealogy: Any):
        """Wire in the ConstraintGenealogyLogger for pressure-state reads."""
        self._genealogy = genealogy

    def set_ivm(self, ivm: Any):
        """Wire in the IVM lattice so heat level can modulate clause depth."""
        self._ivm = ivm

    # ---- pressure state ---------------------------------------------------

    def _axis_bias_from_links(self) -> Dict[str, float]:
        """
        Compute a frequency-based axis prior from the promoted link registry.
        Links that include each axis as a parent represent patterns the
        evolutionary chain has already validated.  Returns a normalized vector.
        """
        if not self._genealogy:
            return {}
        try:
            counts: Dict[str, int] = {a: 0 for a in ("X", "T", "N", "B", "A")}
            links = getattr(self._genealogy, "links", {}) or {}
            total = 0
            for lnk in links.values():
                for p in getattr(lnk, "parents", []):
                    sp = str(p)
                    if ":" in sp:
                        prefix, rest = sp.split(":", 1)
                        if prefix in counts:
                            # "A:OUTLET_PUSH" style — direct axis ability
                            counts[prefix] += 1
                            total += 1
                        elif prefix == "NC" and ">" in rest:
                            # "NC:B>T" style — OETS relation carrying two axes
                            for part in rest.split(">"):
                                ax = part.strip().upper()
                                if ax in counts:
                                    counts[ax] += 1
                                    total += 1
            if total == 0:
                return {}
            # Normalize to [0.8, 1.4] range — a gentle prior, not a hard override
            max_count = max(counts.values()) or 1
            return {
                ax: 0.8 + 0.6 * (cnt / max_count)
                for ax, cnt in counts.items()
            }
        except Exception:
            return {}

    def _pressure_state(self) -> Tuple[Dict[str, float], float]:
        """
        Return (orientation, outlet_fraction) from genealogy.
        Blends three signals:
          1. correction factors from PressureComplexityCurve (live oscillation state)
          2. gradient EMA (actual accumulated per-axis relief this session)
          3. axis frequency prior from promoted links (evolutionary history)
        """
        if self._genealogy is None:
            return {a: 1.0 for a in ("X", "T", "N", "B", "A")}, 0.05
        try:
            orientation     = self._genealogy.pressure_orientation()
            outlet_fraction = self._genealogy._outlet_fraction()

            # Blend active evolution momentum into orientation.
            # axis_relief_state() returns the normalized _gradient_axis_ema (0–1)
            # via the public API instead of reaching into private internals.
            # Axes actively building promoted links get boosted grammar orientation —
            # their motifs become the natural rhythm of expression.
            if hasattr(self._genealogy, "axis_relief_state"):
                relief = self._genealogy.axis_relief_state()
                for ax in orientation:
                    orientation[ax] = _clamp(
                        orientation[ax] * (1.0 + 0.15 * relief.get(ax, 0.0)),
                        0.5, 2.0
                    )

            # Blend evolutionary link-frequency prior (stable historical signal)
            link_bias = self._axis_bias_from_links()
            if link_bias:
                for ax in orientation:
                    if ax in link_bias:
                        # 70% live signal, 30% historical prior
                        orientation[ax] = 0.70 * orientation[ax] + 0.30 * link_bias[ax]

            return orientation, float(outlet_fraction)
        except Exception:
            return {a: 1.0 for a in ("X", "T", "N", "B", "A")}, 0.05

    def _log_relief_to_genealogy(
        self,
        text_changed: bool,
        clarity: float,
        motif: Optional["StructuralMotif"] = None,
    ):
        """
        Log relief events to the genealogy when a grammatically clear sentence
        is produced.

        Logs three axes that grammar directly satisfies:
          A (OUTLET_PUSH)       -- expression completed = agency exercised
          B (INTERFACE_WEAKEN)  -- clear clause boundaries reduce containment pressure
          T (ADVANCE_TICK)      -- coherent tense/sequence advances temporal state

        This populates _gradient_axis_ema for all three axes, making them
        visible to the motif selection feedback loop.
        """
        if not self._genealogy or not text_changed:
            return
        try:
            r = clarity * 0.03   # base relief magnitude (small but real)

            # B-axis relief scales with clause structure quality (from motif)
            b_score = (motif.constraint_scores.get("B", 0.5) if motif else 0.5)
            b_relief = r * (0.5 + b_score)

            # T-axis relief scales with temporal stability of motif
            t_score = (motif.constraint_scores.get("T", 0.5) if motif else 0.5)
            t_relief = r * (0.5 + t_score)

            pv_before = {
                "A": r * 2.0,       # A under most pressure (expression pending)
                "B": b_relief * 1.5, # B pressure from unresolved containment
                "T": t_relief * 1.5, # T pressure from unresolved sequence
                "N": r,
                "X": 0.0,
            }
            pv_after = {
                "A": 0.0, "B": 0.0, "T": 0.0, "N": 0.0, "X": 0.0,
            }
            self._genealogy.observe(
                pressure_before=pv_before,
                trace=[
                    {"ability": "A:OUTLET_PUSH",        "cost": 0.001, "source": "grammar"},
                    {"ability": "B:INTERFACE_WEAKEN",    "cost": 0.001, "source": "grammar"},
                    {"ability": "T:ADVANCE_TICK",        "cost": 0.001, "source": "grammar"},
                ],
                pressure_after=pv_after,
                state_sig_before=hashlib.md5(b"gram_before").hexdigest()[:8],
                state_sig_after=hashlib.md5(b"gram_after").hexdigest()[:8],
                notes={
                    "tag":     "grammar_clarity",
                    "clarity": round(clarity, 3),
                    "b_score": round(b_score, 3),
                    "t_score": round(t_score, 3),
                },
                difference_snapshot={},
            )
        except Exception:
            pass

    @staticmethod
    def _context_hash(text: str) -> str:
        return hashlib.md5(text[:80].encode("utf-8", errors="replace")).hexdigest()[:8]

    # ---- main API ---------------------------------------------------------

    def suggest_structure(
        self,
        raw_expression: str,
        context_text:   str = "",
        tone:           str = "neutral",
        passion:        str = "observant",
        drive:          str = "steady",
        turn_profile:   Optional[Any] = None,
    ) -> Optional[Dict]:
        """
        Given a raw expression, find the best promoted structural motif for
        the current constraint pressure state and apply it.

        Returns None if no promoted motif exists yet or the suggestion
        doesn't improve the expression.

        Returns dict:
            motif_id       -- pattern_id of the applied motif
            role_sequence  -- list of role names
            applied_text   -- the restructured sentence
            constraint_fit -- axis alignment score [0,1]
        """
        orientation, outlet = self._pressure_state()

        # If the caller supplies the live turn's ConstraintProfile, blend its
        # pressure_vector into orientation.  This anchors motif selection to the
        # actual XTNBA state of the turn (ACMS §VII.7: language is a projection
        # of state), not just the accumulated genealogy signal.
        if turn_profile is not None:
            try:
                _pv = turn_profile.pressure_vector()
                for _ax in orientation:
                    _pv_ax = abs(float(_pv.get(_ax, 0.0)))
                    if _pv_ax > 0.0:
                        orientation[_ax] = _clamp(
                            orientation[_ax] * (1.0 + _pv_ax * 0.5), 0.5, 2.0
                        )
            except Exception:
                pass

        # Clause III coloring: tone, passion, and drive bias motif selection
        # (e.g., "focused" tone biases toward B-axis (Boundary) structure)
        if tone == "focused":
            orientation["B"] = orientation.get("B", 1.0) * 1.3
        if passion == "intense":
            orientation["A"] = orientation.get("A", 1.0) * 1.4
        if drive == "exploratory":
            orientation["X"] = orientation.get("X", 1.0) * 1.2

        # IVM heat modulates clause complexity preference.
        # High contradiction heat → prefer simpler (lower clause_depth) motifs.
        try:
            if self._ivm is not None:
                heat_fn = getattr(self._ivm, "get_global_heat", None)
                if heat_fn:
                    heat = float(heat_fn())   # 0..1
                    if heat > 0.6:
                        # Suppress B-axis orientation so complex clause motifs
                        # are deprioritized under high cognitive load
                        orientation["B"] = orientation.get("B", 1.0) * (1.0 - 0.4 * heat)
        except Exception:
            pass

        # Get top-N candidates ranked by pressure score, not just the single best.
        # The single best is often too complex for the input — try several.
        candidates = self._lineage.top_for_pressure(orientation, outlet, n=8)

        if not candidates:
            # No promoted motif yet -- observe the current pattern so the
            # lineage can start learning from it.
            pattern   = self._tagger.extract_pattern(raw_expression)
            ctx_hash  = self._context_hash(context_text or raw_expression)
            self._lineage.record_success(
                pattern, ctx_hash,
                len(raw_expression.split()), orientation,
            )
            return None

        token_pool = self._filler.pool_from_text(raw_expression, self._tagger)
        _input_len = len(raw_expression.split())

        _orig_words   = set(re.findall(r'[a-z]+', raw_expression.lower()))
        _stopwords    = {'the', 'a', 'an', 'is', 'are', 'was', 'it', 'to',
                         'of', 'in', 'and', 'but', 'i', 'my', 'this', 'that'}
        _orig_content = _orig_words - _stopwords

        # Sort candidates: prefer motifs whose role count is close to input length.
        # This prevents the most-complex motif from always winning even when it
        # can't be filled from a short expression.
        def _complexity_penalty(m: StructuralMotif) -> float:
            diff = abs(len(m.role_sequence) - _input_len)
            return diff * 0.05  # small penalty per excess role

        candidates = sorted(candidates,
                            key=lambda m: _complexity_penalty(m))

        for best in candidates:
            # S13a: skip motifs whose CBU profile is in COLLAPSED phase
            # S13b: sign-flip axis_fit contributions for INVERTING CBUs
            if best.cbu_profile is not None and not best.cbu_profile.can_operate():
                continue

            applied = self._filler.fill(best, token_pool, raw_expression)

            # Skip if filler returned the input unchanged or produced a stub
            if len(applied.split()) < 2 or applied.strip() == raw_expression.strip():
                continue

            # Quality gate: require content-word overlap ≥ 50%
            _appl_words   = set(re.findall(r'[a-z]+', applied.lower()))
            _appl_content = _appl_words - _stopwords
            if _orig_content:
                overlap = len(_orig_content & _appl_content) / len(_orig_content)
                if overlap < 0.5:
                    continue

            # Reject dangling participles
            if re.search(r'\b(i|he|she|it|we|they)\s+\w+ing\b', applied.lower()):
                continue

            # This candidate passed — use it
            axis_fit = sum(
                best.constraint_scores.get(ax, 0.5) * _clamp(corr, 0.5, 1.5)
                for ax, corr in orientation.items()
            ) / max(1, len(orientation))

            self._last_motif_id = best.pattern_id

            return {
                "motif_id":       best.pattern_id,
                "role_sequence":  [r.value for r in best.role_sequence],
                "applied_text":   applied,
                "constraint_fit": round(axis_fit, 3),
            }

        # All candidates failed quality gate — record pattern for future learning
        pattern  = self._tagger.extract_pattern(raw_expression)
        ctx_hash = self._context_hash(context_text or raw_expression)
        self._lineage.record_success(pattern, ctx_hash,
                                     len(raw_expression.split()), orientation)
        return None

    def assemble(self, word_list: List[Tuple[str, str]]) -> str:
        """
        O-4 assembly: compose a sentence from (word, grammatical_position) pairs
        produced by the FGAE output pipeline.

        Maps each word's FGAE grammatical position to a TokenRole, builds a
        token pool, then fills the best promoted structural motif.  When no
        motif has been promoted yet the lineage records the default pattern so
        it can start learning, and a minimal first-person clause is returned.

        Position → Role mapping (mirrors FGAE FGAEOutputSlot.grammatical_position):
            modal / pre-verbal / stance_marker  → ACTION / CONTEXT
            pre-nominal / intensifier           → DESCRIPTOR
            semantic / post-verbal              → OBJECT
            boundary / delimiter                → CONNECTOR
        """
        if not word_list:
            return ""

        _POS_TO_ROLE: Dict[str, TokenRole] = {
            "modal":         TokenRole.ACTION,
            "pre-verbal":    TokenRole.CONTEXT,
            "stance_marker": TokenRole.CONTEXT,
            "pre-nominal":   TokenRole.DESCRIPTOR,
            "intensifier":   TokenRole.DESCRIPTOR,
            "semantic":      TokenRole.OBJECT,
            "post-verbal":   TokenRole.OBJECT,
            "boundary":      TokenRole.CONNECTOR,
            "delimiter":     TokenRole.CONNECTOR,
        }

        pool: Dict[TokenRole, List[str]] = defaultdict(list)
        pool[TokenRole.AGENT].append("I")

        for word, pos in word_list:
            if not word:
                continue
            pool[_POS_TO_ROLE.get(pos, TokenRole.OBJECT)].append(word)

        token_pool = dict(pool)

        orientation, outlet = self._pressure_state()
        best = self._lineage.best_for_pressure(orientation, outlet)

        if best is not None:
            filled = self._filler.fill(best, token_pool)
            if filled and len(filled.split()) >= 2:
                s = filled.strip()
                if not s.endswith((".", "?", "!")):
                    s += "."
                return s[0].upper() + s[1:]

        # No promoted motif yet — record the default pattern so lineage learns,
        # then return a minimal first-person clause from whatever roles exist.
        _actions  = token_pool.get(TokenRole.ACTION,  [])
        _objects  = token_pool.get(TokenRole.OBJECT,  [])
        _contexts = token_pool.get(TokenRole.CONTEXT, [])

        parts: List[str] = []
        if _actions:
            parts += ["I'm", _actions[0]]
        if _objects:
            parts.append(_objects[0])
        if _contexts and len(parts) < 4:
            parts.append(_contexts[0])
        if not parts:
            parts = ["I'm", "present"]

        default_pattern = self._tagger.extract_pattern(" ".join(parts))
        if default_pattern:
            ctx_hash = self._context_hash(" ".join(parts))
            self._lineage.record_success(
                default_pattern, ctx_hash, len(parts), orientation,
            )

        s = " ".join(parts)
        if not s.endswith((".", "?", "!")):
            s += "."
        return s[0].upper() + s[1:]

    def extract_pattern(self, text: str) -> Tuple[TokenRole, ...]:
        """Public helper for external callers."""
        return self._tagger.extract_pattern(text)

    def suggest_discourse(self) -> Optional[str]:
        """Suggest what type of turn would cohere with the current discourse."""
        return self._discourse.suggest_next_turn_type()

    # ---- exchange feedback ------------------------------------------------

    def observe_exchange(
        self,
        user_text:    str,
        aurora_text:  str,
        success:      bool,
        clarity:      float = 0.65,
        turn_profile: Optional[Any] = None,
    ) -> None:
        """
        Record a completed exchange and update motif fitness with constraint-native
        outcome signals (ACMS §IV, §V).

        Scoring axes:
          N-axis relief  — shorter, denser response reduces expression load
          A-axis relief  — intent enacted / question answered
          T+B stability  — coherent context and structure maintained

        These are written back to the applied motif's ConstraintProfile via
        update_from_ivm() so the CBU registry tick can detect genuine pressure
        changes rather than operating on stale profiles.
        """
        orientation, outlet = self._pressure_state()
        pattern   = self._tagger.extract_pattern(aurora_text)
        ctx_hash  = self._context_hash(user_text)
        n_tokens  = len(aurora_text.split())

        tagged      = self._tagger.tag(aurora_text)
        ref_pos     = self._tagger.extract_reference_positions(tagged)
        tagged_roles = [r for _, r in tagged]
        agent_pos   = next((i for i, r in enumerate(tagged_roles)
                            if r is TokenRole.AGENT), None)
        anchors: List[Tuple[int, int]] = []
        if agent_pos is not None:
            for rp in ref_pos:
                if rp > agent_pos:
                    anchors.append((agent_pos, rp))

        if success:
            self._lineage.record_success(pattern, ctx_hash, n_tokens,
                                         orientation, anchors)
            last_m = (self._lineage._motifs.get(self._last_motif_id)
                      if self._last_motif_id else None)
            self._log_relief_to_genealogy(True, clarity, motif=last_m)

            # Write constraint-native outcome signals to the motif's CBU profile.
            # Polarities are signed: negative = pressure relieving (moving toward
            # stability), positive = pressure building.
            if last_m is not None and last_m.cbu_profile is not None:
                _n_relief   = _clamp(1.0 - n_tokens / 30.0)
                _aurora_type = _classify_turn_type(aurora_text) or "statement"
                _a_relief   = 1.0 if _aurora_type != "question" else 0.5
                _tb_relief  = _clamp(clarity)
                _ivm = {
                    "N": -_n_relief * 0.30,
                    "A": -_a_relief * 0.40,
                    "T": -_tb_relief * 0.15,
                    "B": -_tb_relief * 0.10,
                    "X": 0.0,
                }
                try:
                    last_m.cbu_profile.update_from_ivm(_ivm)
                except Exception:
                    pass
        else:
            self._lineage.record_fail(pattern)
            if self._last_motif_id:
                _last_m = self._lineage._motifs.get(self._last_motif_id)
                if _last_m is not None and _last_m.cbu_profile is not None:
                    try:
                        _last_m.cbu_profile.update_from_ivm(
                            {"N": 0.20, "A": 0.25, "T": 0.0, "B": 0.0, "X": 0.0}
                        )
                    except Exception:
                        pass

        user_type   = _classify_turn_type(user_text)   or "statement"
        aurora_type = _classify_turn_type(aurora_text) or "statement"
        self._discourse.record_turn(user_type)
        self._discourse.record_turn(aurora_type)

    def tick(self, genealogy_logger: Optional[Any] = None) -> Dict:
        """
        Drive one motif-transition cycle.  Call from the surface daemon tick
        so the grammar manifold stays in sync with CBU pressure state.
        Returns diagnostic dict.
        """
        return {
            "motif_transitions": self._lineage.tick_motif_transitions(genealogy_logger),
        }

    # ---- bootstrap --------------------------------------------------------

    def bootstrap_from_corpus(
        self,
        corpus_path:  str,
        max_messages: int = 12000,
        use_nltk:     bool = False,
    ) -> Dict:
        """
        Mine corpus once to seed the motif lineage with real structural patterns.
        Run via /grammarboot command.
        """
        miner    = MotifMiner(use_nltk=use_nltk)
        patterns = miner.mine_corpus(corpus_path, max_messages=max_messages)
        self._lineage.seed_motifs(patterns)

        disc_patterns = miner.mine_discourse(corpus_path)
        for (prev_type, next_type), count in disc_patterns:
            key = f"{prev_type}_{next_type}"
            dm  = DiscourseMotif(
                pattern_id    = key,
                turn_sequence = (prev_type, next_type),
                success_count = count,
                promoted      = count >= 15,
            )
            self._lineage._discourse[key] = dm

        self._lineage.save()
        return {
            "patterns_seeded":     len(patterns),
            "discourse_patterns":  len(disc_patterns),
            "promoted_after_seed": len(self._lineage.get_promoted()),
        }

    # ---- status -----------------------------------------------------------

    def status(self) -> Dict:
        orientation, outlet = self._pressure_state()
        best = self._lineage.best_for_pressure(orientation, outlet)
        return {
            "motif_lineage":    self._lineage.stats(),
            "genealogy_wired":  self._genealogy is not None,
            "outlet_fraction":  round(outlet, 3),
            "top_motif":        best.pattern_id if best else None,
            "last_applied":     self._last_motif_id,
        }
