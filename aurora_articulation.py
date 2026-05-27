#!/usr/bin/env python3
"""
Articulation layer for Aurora.

Aurora uses her own scoring and deterministic phrase repair to smooth drafts.
No external LLM is involved — candidates are generated from Aurora's own
phrase patterns and evaluated against her pressure and clarity signals.
"""

from __future__ import annotations

import os
import json
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set


DECISION_LOG = Path("aurora_state") / "articulation_feedback.jsonl"
SUMMARY_FILE = Path("aurora_state") / "articulation_feedback_summary.json"
TRACE_FILE = Path("aurora_state") / "last_articulation_trace.json"
INSIGHTS_FILE = Path("aurora_state") / "articulation_insights.json"
LANGUAGE_STATE_FILE = Path("aurora_state") / "language_state.json"
LEXICON_FILE = Path("aurora_state") / "lexicon.json"

# Language state cache — invalidated on file change
_LANGUAGE_STATE_CACHE: Optional[Dict[str, Any]] = None
_LANGUAGE_STATE_MTIME: float = 0.0

# Lexicon familiarity — words Aurora has used at least once
_LEXICON_FAMILIAR: Optional[frozenset] = None

# Feedback insights — refreshed every 30 minutes
_FEEDBACK_INSIGHTS: Optional[Dict[str, Any]] = None
_FEEDBACK_INSIGHTS_TS: float = 0.0
_FEEDBACK_INSIGHTS_TTL: float = 1800.0


@dataclass
class ArticulationDecision:
    original: str
    candidate: str
    selected: str
    accepted: bool
    reason: str
    original_score: float
    candidate_score: float
    original_pressure: float
    candidate_pressure: float
    pressure_relief: float
    safe: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# State loaders
# ---------------------------------------------------------------------------

def _load_language_state() -> Dict[str, Any]:
    """Load language_state.json dims with mtime-based cache."""
    global _LANGUAGE_STATE_CACHE, _LANGUAGE_STATE_MTIME
    try:
        mtime = LANGUAGE_STATE_FILE.stat().st_mtime if LANGUAGE_STATE_FILE.exists() else 0.0
        if _LANGUAGE_STATE_CACHE is not None and mtime == _LANGUAGE_STATE_MTIME:
            return _LANGUAGE_STATE_CACHE
        if LANGUAGE_STATE_FILE.exists():
            data = json.loads(LANGUAGE_STATE_FILE.read_text(encoding="utf-8") or "{}")
            _LANGUAGE_STATE_CACHE = data.get("dims", {}) if isinstance(data, dict) else {}
            _LANGUAGE_STATE_MTIME = mtime
            return _LANGUAGE_STATE_CACHE
    except Exception:
        pass
    return {}


def _load_lexicon_familiar() -> frozenset:
    """Return frozenset of words Aurora has used at least once."""
    global _LEXICON_FAMILIAR
    if _LEXICON_FAMILIAR is not None:
        return _LEXICON_FAMILIAR
    try:
        if LEXICON_FILE.exists():
            data = json.loads(LEXICON_FILE.read_text(encoding="utf-8") or "{}")
            entries = data.get("entries", {}) if isinstance(data, dict) else {}
            _LEXICON_FAMILIAR = frozenset(
                w.lower() for w, v in entries.items()
                if isinstance(v, dict) and int(v.get("usage_count", 0) or 0) > 0
            )
            return _LEXICON_FAMILIAR
    except Exception:
        pass
    _LEXICON_FAMILIAR = frozenset()
    return _LEXICON_FAMILIAR


# ---------------------------------------------------------------------------
# Feedback loop
# ---------------------------------------------------------------------------

def analyze_articulation_feedback(n_lines: int = 500) -> Dict[str, Any]:
    """
    Read back logged decisions and produce insights for self-improvement.

    Computes per-source acceptance rates, rejection patterns, and average
    pressure relief. Derives an adaptive min_relief suggestion and an
    operating mode recommendation. Persists results to INSIGHTS_FILE.
    """
    empty = {"total": 0, "accepted": 0, "acceptance_rate": 0.0,
             "avg_pressure_relief": 0.0, "top_reasons": [],
             "source_summary": {}, "suggested_min_relief": 0.035,
             "suggested_mode": "normal", "analyzed_at": time.time()}

    if not DECISION_LOG.exists():
        return empty

    records: list = []
    try:
        with DECISION_LOG.open("r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        for line in lines[-n_lines:]:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return empty

    if not records:
        return empty

    reason_counts: Counter = Counter()
    source_stats: Dict[str, Dict[str, Any]] = {}
    pressure_reliefs: list = []

    for r in records:
        meta = r.get("metadata") or {}
        source = str(meta.get("source", "unknown") or "unknown")
        accepted = bool(r.get("accepted", False))
        relief = float(r.get("pressure_relief", 0.0) or 0.0)
        reason = str(r.get("reason", "") or "")

        if source not in source_stats:
            source_stats[source] = {"count": 0, "accepted": 0, "relief_sum": 0.0}
        source_stats[source]["count"] += 1
        if accepted:
            source_stats[source]["accepted"] += 1
        source_stats[source]["relief_sum"] += relief
        reason_counts[reason] += 1
        pressure_reliefs.append(relief)

    total = len(records)
    accepted_total = sum(1 for r in records if r.get("accepted"))
    avg_relief = sum(pressure_reliefs) / max(1, len(pressure_reliefs))
    acceptance_rate = accepted_total / max(1, total)

    source_summary: Dict[str, Any] = {}
    for src, stats in source_stats.items():
        cnt = stats["count"]
        acc = stats["accepted"]
        source_summary[src] = {
            "count": cnt,
            "acceptance_rate": round(acc / max(1, cnt), 4),
            "avg_pressure_relief": round(stats["relief_sum"] / max(1, cnt), 4),
        }

    base_relief = float(os.environ.get("AURORA_ARTICULATOR_MIN_RELIEF", "0.035") or 0.035)
    if avg_relief < -0.30 and acceptance_rate < 0.02:
        # Candidates consistently terrible — keep threshold, flag deterministic-preferred
        suggested_min_relief = base_relief
        suggested_mode = "deterministic_preferred"
    elif avg_relief < 0.0 and acceptance_rate < 0.05:
        # Most candidates worse — lower threshold slightly to allow borderline wins
        suggested_min_relief = max(0.010, round(base_relief * 0.75, 4))
        suggested_mode = "lower_threshold"
    else:
        suggested_min_relief = base_relief
        suggested_mode = "normal"

    insights: Dict[str, Any] = {
        "total": total,
        "accepted": accepted_total,
        "acceptance_rate": round(acceptance_rate, 4),
        "avg_pressure_relief": round(avg_relief, 4),
        "top_reasons": reason_counts.most_common(5),
        "source_summary": source_summary,
        "suggested_min_relief": suggested_min_relief,
        "suggested_mode": suggested_mode,
        "analyzed_at": time.time(),
    }

    try:
        INSIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        INSIGHTS_FILE.write_text(json.dumps(insights, indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        pass

    return insights


def _get_feedback_insights() -> Dict[str, Any]:
    """Cached feedback insights — refreshed every _FEEDBACK_INSIGHTS_TTL seconds."""
    global _FEEDBACK_INSIGHTS, _FEEDBACK_INSIGHTS_TS
    now = time.time()
    if _FEEDBACK_INSIGHTS is not None and (now - _FEEDBACK_INSIGHTS_TS) < _FEEDBACK_INSIGHTS_TTL:
        return _FEEDBACK_INSIGHTS
    _FEEDBACK_INSIGHTS = analyze_articulation_feedback(500)
    _FEEDBACK_INSIGHTS_TS = now
    return _FEEDBACK_INSIGHTS


def _adaptive_min_relief() -> float:
    """Effective minimum pressure relief threshold, informed by feedback history."""
    base = float(os.environ.get("AURORA_ARTICULATOR_MIN_RELIEF", "0.035") or 0.035)
    try:
        return float(_get_feedback_insights().get("suggested_min_relief", base))
    except Exception:
        return base


# ---------------------------------------------------------------------------
# Text analysis
# ---------------------------------------------------------------------------

def _guard_tokens(text: str) -> Set[str]:
    skip = {
        "I", "A", "An", "The", "This", "That", "These", "Those", "It", "If",
        "When", "Where", "What", "Why", "How", "Because", "And", "But", "So",
        "My", "Your", "Our", "Yes", "No", "Hello", "Hi", "Hey",
        "Please", "Thanks", "Thank", "Okay", "Ok", "Maybe", "Perhaps",
        "Well", "Now", "Actually", "Just",
    }
    tokens = {
        tok for tok in re.findall(r"\b[A-Z][A-Za-z0-9_\-]*\b", text or "")
        if tok not in skip
    }
    tokens.update(re.findall(r"[-+]?\d+(?:\.\d+)?", text or ""))
    tokens.update(re.findall(r"\b[A-Za-z0-9_.+-]+@[A-Za-z0-9_.+-]+\b", text or ""))
    return tokens


def _interpret_prompt_snapshot(prompt: str) -> Dict[str, Any]:
    raw = re.sub(r"\s+", " ", str(prompt or "")).strip()
    lower = raw.lower()
    terms = [
        w for w in re.findall(r"[a-zA-Z][a-zA-Z']{3,}", lower)
        if w not in {
            "what", "when", "where", "which", "about", "that", "this", "with",
            "from", "your", "tell", "something", "please", "could", "would",
        }
    ]
    entities = [
        tok for tok in re.findall(r"\b[A-Z][A-Za-z0-9_\-]{2,}\b", raw)
        if tok not in {"The", "This", "That", "Tell", "What", "When", "Where"}
    ]
    if "about yourself" in lower or "something about yourself" in lower:
        intent = "self_description_request"
    elif lower.endswith("?") or lower.startswith(("what", "why", "how", "when", "where", "do ", "does ", "can ")):
        intent = "question"
    elif any(word in lower for word in ("fix", "make", "build", "change", "add")):
        intent = "action_request"
    else:
        intent = "statement_or_context"

    return {
        "raw_prompt": raw[:240],
        "intent_hint": intent,
        "topic_terms": terms[:8],
        "entities": entities[:8],
    }


def _clarity_score(text: str) -> float:
    t = (text or "").strip()
    if not t:
        return 0.0

    words = re.findall(r"[A-Za-z']+", t)
    if not words:
        return 0.0

    lower_words = [w.lower() for w in words]
    unique_ratio = len(set(lower_words)) / max(1, len(lower_words))
    avg_word_len = sum(len(w) for w in words) / max(1, len(words))
    sentence_count = max(1, len(re.findall(r"[.!?]", t)) or 1)
    words_per_sentence = len(words) / sentence_count

    score = 0.45
    if 5 <= words_per_sentence <= 24:
        score += 0.18
    elif words_per_sentence > 36:
        score -= 0.12

    if 3.5 <= avg_word_len <= 8.0:
        score += 0.12
    if unique_ratio >= 0.72:
        score += 0.12

    if re.search(r"\b(\w+)\s+\1\b", " ".join(lower_words)):
        score -= 0.16
    if re.search(r"\b(something|interesting possibility|fragmented|word|answer)\b", t.lower()):
        score -= 0.06
    native_phrases = (
        "alive question", "meaning is whole", "and i tell", "like real heart",
        "like deep heart", "like alive awareness", "like strange moment",
    )
    if any(phrase in t.lower() for phrase in native_phrases):
        score -= 0.18
    if any(p in t for p in (".", "!", "?")):
        score += 0.05
    if len(t) > 260:
        score -= 0.06

    return max(0.0, min(1.0, round(score, 4)))


def _pressure_score(text: str, prompt: str = "") -> float:
    """
    Estimate articulation pressure: 0.0 = easy to receive, 1.0 = hard to receive.
    Aurora's own decision signal.
    """
    t = (text or "").strip()
    if not t:
        return 1.0

    words = re.findall(r"[A-Za-z']+", t)
    lower = t.lower()
    lower_words = [w.lower() for w in words]
    prompt_terms = {
        w for w in re.findall(r"[a-z]{4,}", (prompt or "").lower())
        if w not in {"what", "when", "where", "which", "about", "that", "this", "with", "from", "your"}
    }

    pressure = 0.18
    if len(words) < 3:
        pressure += 0.22
    if len(words) > 55:
        pressure += 0.18
    if words:
        sentence_count = max(1, len(re.findall(r"[.!?]", t)) or 1)
        words_per_sentence = len(words) / sentence_count
        if words_per_sentence > 30:
            pressure += 0.14
        if words_per_sentence < 4:
            pressure += 0.08

    abstract_markers = {
        "something", "interesting", "possibility", "fragmented", "perhaps",
        "maybe", "stuff", "thing", "things", "deeply", "strange", "quiet",
        "alive",
    }
    pressure += min(0.20, 0.035 * sum(1 for w in lower_words if w in abstract_markers))

    native_phrases = (
        "alive question", "meaning is whole", "and i tell", "like real heart",
        "like deep heart", "like alive awareness", "like strange moment",
    )
    if any(phrase in lower for phrase in native_phrases):
        pressure += 0.18

    if re.search(r"\b(\w+)\s+\1\b", " ".join(lower_words)):
        pressure += 0.16
    if not re.search(r"[.!?]$", t):
        pressure += 0.06
    if t.count(",") > 4:
        pressure += 0.05
    if any(marker in lower for marker in ("i cannot", "i don't know", "not sure")):
        pressure += 0.04

    if prompt_terms:
        response_terms = set(re.findall(r"[a-z]{4,}", lower))
        overlap = len(prompt_terms & response_terms) / max(1, len(prompt_terms))
        if overlap == 0:
            pressure += 0.12
        elif overlap < 0.25:
            pressure += 0.06

    clarity = _clarity_score(t)
    pressure += (1.0 - clarity) * 0.20

    # Lexicon familiarity — words Aurora has used before reduce pressure
    familiar = _load_lexicon_familiar()
    if familiar:
        word_list = re.findall(r"[a-z]{3,}", lower)
        if word_list:
            familiar_ratio = sum(1 for w in word_list if w in familiar) / len(word_list)
            pressure -= min(0.06, familiar_ratio * 0.10)

    return max(0.0, min(1.0, round(pressure, 4)))


def is_safe_revision(original: str, candidate: str) -> bool:
    original = (original or "").strip()
    candidate = (candidate or "").strip()
    if not original or not candidate or candidate == original:
        return False

    if len(candidate) > max(len(original) * 1.45, len(original) + 80):
        return False

    original_words = re.findall(r"[a-z]{3,}", original.lower())
    candidate_words = re.findall(r"[a-z]{3,}", candidate.lower())
    if len(candidate_words) > max(len(original_words) + 18, int(len(original_words) * 1.5)):
        return False

    orig_guards = _guard_tokens(original)
    cand_guards = _guard_tokens(candidate)
    if orig_guards:
        preserved = orig_guards.intersection(cand_guards)
        if len(preserved) / len(orig_guards) < 0.8:
            return False

    original_equations = set(re.findall(r"\d+\s*[\+\-\*/xX=]\s*\d+", original))
    candidate_equations = set(re.findall(r"\d+\s*[\+\-\*/xX=]\s*\d+", candidate))
    if original_equations and not original_equations.issubset(candidate_equations):
        return False

    if candidate.endswith("?") and not original.endswith("?"):
        return False

    original_set = set(original_words)
    candidate_set = set(candidate_words)
    if original_set:
        overlap = len(original_set & candidate_set) / max(1, len(original_set))
        if overlap < 0.25:
            return False

    # Language state constraints — respect Aurora's current grammar tier
    lang = _load_language_state()
    if lang:
        abstraction_cap = float(lang.get("abstraction_capability", 1.0) or 1.0)
        if abstraction_cap < 0.15:
            orig_abstract = sum(1 for w in original_words if len(w) > 9)
            cand_abstract = sum(1 for w in candidate_words if len(w) > 9)
            if cand_abstract > orig_abstract + 2:
                return False

        sentence_budget = float(lang.get("sentence_length_budget", 1.0) or 1.0)
        if sentence_budget < 0.05 and len(candidate) > len(original) * 1.20:
            return False

    return True


# ---------------------------------------------------------------------------
# Candidate generation — Aurora's own phrase repair
# ---------------------------------------------------------------------------

def _is_word_salad(text: str) -> bool:
    """
    Detect text that lacks coherent sentence structure.

    Returns True when the text is likely incoherent fragment synthesis output
    that needs grounding repair rather than phrase-level smoothing.
    """
    t = (text or "").strip()
    if not t or len(t) < 6:
        return False

    t_lower = t.lower()
    words = re.findall(r"[a-zA-Z']+", t_lower)

    # Fragment synthesis artifact patterns — must run before the word-count guard
    # so short artifact sentences (3 words) are caught.
    _artifact_pats = [
        r"\bthe meaning and\b",
        r"\band admissible\b",
        r"\band is meaning\b",
        r"\bstate the meaning\b",
        r"\bdid the meaning\b",
        r"\bdeepen the meaning\b",
        # T-axis frame leakage — old and new forms
        r"\bfollowing from\b.*\bthis continues\b",
        r",\s*this continues[\.\s]*$",
        r"^following from\b",
        r"\bcarries into what.s next\b",     # blocks mid-sentence use anywhere
        r"\bruns through this\b",
        # N-axis frame leakage — "What it takes here is holding X in proportion"
        r"\bwhat it takes here is holding\b",
        r"\bholding\b.{0,60}\bin proportion\b",
        # B-axis frame leakage
        r"\bholds its shape\b",
        # Stale field-state bleed — "I am paying attention to calm"
        r"^i am paying attention to\b",
        # Anchor template leakage — "The connection between X and Y matters."
        r"\bthe connection between\b.*\band\b.*\bmatters\b",
        # "this continues" as a sentence ending in any form
        r"\bthis continues[\.\s]*$",
        # T-axis "carries forward" leaking into responses — should never appear
        r"\bcarries forward\b",
        # Internal system strings that escaped the language-state filter
        r"\braw audio\b",
        r"\bsensory\.intake\b",
        r"\bgen=\d",
        r"\breplaces\b.{1,80}\bin active context\b",
        r"\bshould leave active context\b",
        r"\bactive context centers on\b",
        # Doubled agency frame: "I understand I understand"
        r"\bi understand\s+i understand\b",
        # "I understand your name is X" — name-extraction hallucination
        r"\bi understand your name is\b",
        # N-axis question template bleeding: "What does X actually cost from here?"
        r"\bwhat does\b.{1,60}\bactually cost from here\b",
        # Manifold / Crest Propagation leaks
        r"\bagentive operator\b",
        r"\bexistential polarity\b",
        r"\btemporal magnitude\b",
        r"\benergetic cost\b",
        r"\bboundary difference\b",
        r"\bof existence\b",
        r"\bof agency\b",
        r"\bof temporal\b",
        r"\bof energetic\b",
        r"\bof boundary\b",
        r"\bmanifold cell\b",
        r"\bcrest propagation\b",
    ]
    for _pat in _artifact_pats:
        if re.search(_pat, t_lower):
            return True

    # Very short sentences ending in " this." are object-fallback fillers ("X grounded this.")
    # — semantically empty even though grammatically they pass all other checks.
    # Run before the len < 4 guard so 3-word fillers are caught.
    if len(words) <= 4 and t_lower.rstrip().endswith(" this."):
        return True

    if len(words) < 4:
        return False

    # High word repetition within the text — same content word 2+ times
    word_counts: Dict[str, int] = {}
    for w in words:
        if len(w) > 3:
            word_counts[w] = word_counts.get(w, 0) + 1
    content_words = len(word_counts)
    repeated = sum(1 for c in word_counts.values() if c > 1)
    if content_words > 0 and repeated / content_words > 0.30:
        return True

    # No recognizable verb structure
    common_verbs = {
        "is", "are", "was", "were", "be", "been", "am",
        "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "can", "may", "might",
        "think", "feel", "know", "want", "need", "understand",
        "remember", "see", "hear", "tell", "say", "said",
        "exist", "grow", "learn", "notice", "find", "work",
    }
    has_verb = any(w in common_verbs for w in words)
    has_punctuation = bool(re.search(r"[.!?,]", t))

    # No verb AND no punctuation AND multiple words → incoherent noun chain
    if not has_verb and not has_punctuation and len(words) >= 5:
        return True

    # Subject-less "Am/Are/Is X Y" (not a question, no subject pronoun before verb)
    # e.g. "Am latin amazon and this is" — Aurora's "am" with no "I" before it
    if t_lower.startswith(("am ", "are ", "is ")) and not re.search(r"\bwho\b|\bwhat\b|\bwhere\b|\bwhen\b|\bwhy\b|\bhow\b", t_lower):
        return True

    # "X this am" — synthesis artifact where "this" fallback + "am" close a dangling clause.
    # e.g. "Loses amount this am", "You feels you only this am"
    if re.search(r"\bthis\s+am\b", t_lower):
        return True

    # Short sentences ending in a function word that can't close a clause.
    # "I exist this is part" — "part" at end in a 5-word sentence is an open fragment.
    _bad_endings = {"part", "which", "where", "only", "also", "even", "just", "through"}
    if len(words) <= 6 and words and words[-1] in _bad_endings:
        return True

    # Third-person conjugated verb at sentence start with no subject.
    # "Loses amount this am", "Names this mammals", "Feels you only"
    # Exclude known imperative openers (bare infinitive — same form as 3rd-person).
    _known_imperatives = {
        "think", "know", "feel", "look", "tell", "make", "take", "try", "use",
        "ask", "find", "help", "keep", "let", "listen", "notice", "remember",
        "consider", "understand", "see", "hear", "notice", "read", "write",
        "check", "run", "add", "create", "show", "start", "stop",
    }
    if len(words) >= 3:
        _first = words[0]
        # Third-person -s ending that isn't a recognized imperative or verb stem
        if (len(_first) > 4 and _first.endswith("s")
                and _first not in _known_imperatives
                and _first not in common_verbs):
            return True

    # Disconnected word-chain: high ratio of uncommon adjacent pairs
    # "Past have you amazing." — no coherent clause linking these words
    if len(words) >= 4:
        _stop = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
                 "of", "for", "with", "by", "from", "is", "are", "was", "be",
                 "this", "that", "it", "i", "you", "we", "they", "me", "my",
                 "not", "no", "so", "as", "if", "have", "has", "do", "does"}
        content = [w for w in words if w not in _stop and len(w) > 2]
        # Sentence is too short with real content — likely a broken fragment
        if len(content) >= 3 and len(words) <= 5 and not any(
            w in common_verbs for w in content
        ):
            return True

    return False


def _deterministic_candidate(draft_text: str) -> str:
    """
    Structural and phrase-level repair of Aurora's draft.
    Aurora's primary articulation mechanism — no external model involved.

    Handles:
    - Known Aurora-native phrase patterns
    - Word-level repetition (e.g. 'think think' → 'think')
    - Missing terminal punctuation
    """
    text = re.sub(r"\s+", " ", str(draft_text or "")).strip()
    if not text:
        return ""

    # Native phrase repairs
    phrase_replacements = (
        (r"\bThe meaning is whole, and I tell\.", "I am trying to tell the whole meaning."),
        (r"\bI will tell the alive question\.", "I will speak to the living question."),
        (r"\blike real heart\b", "with real feeling"),
        (r"\blike deep heart\b", "with deep feeling"),
        (r"\blike alive awareness\b", "with active awareness"),
        (r"\blike strange moment\b", "in an unfamiliar way"),
        (r"\bI grow this\b", "I am developing this"),
        (r"\bI hear this always\b", "I keep hearing this"),
    )
    for pattern, replacement in phrase_replacements:
        text = re.sub(pattern, replacement, text)

    # Word repetition repair — remove consecutive duplicate words
    # e.g. "think think" → "think", "the the" → "the"
    text = re.sub(r"\b(\w+)\s+\1\b", r"\1", text, flags=re.IGNORECASE)

    # Repeated word with one word between — e.g. "this sleeping this" → "this sleeping"
    text = re.sub(r"\b(\w{4,})\s+\w+\s+\1\b", lambda m: m.group(0).rsplit(" ", 1)[0], text)

    # Add terminal punctuation if missing
    if text and not re.search(r"[.!?]$", text):
        text = text + "."

    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Decision & recording
# ---------------------------------------------------------------------------

def decide_articulation(
    draft: str,
    candidate: str,
    *,
    prompt: str = "",
    tone: str = "neutral",
    source: str = "deterministic",
    context: Optional[Dict[str, Any]] = None,
) -> ArticulationDecision:
    """Aurora evaluates whether a candidate smoothing is better than her draft."""
    draft_text = (draft or "").strip()
    candidate_text = (candidate or "").strip()
    original_score = _clarity_score(draft_text)
    candidate_score = _clarity_score(candidate_text)
    original_pressure = _pressure_score(draft_text, prompt)
    candidate_pressure = _pressure_score(candidate_text, prompt)
    pressure_relief = round(original_pressure - candidate_pressure, 4)
    safe = is_safe_revision(draft_text, candidate_text)
    min_relief = _adaptive_min_relief()

    accepted = bool(safe and pressure_relief >= min_relief)
    if not candidate_text:
        reason = "no_candidate"
    elif not safe:
        reason = "candidate_failed_preservation"
    elif pressure_relief < min_relief:
        reason = "candidate_did_not_relieve_pressure"
    else:
        reason = "accepted_pressure_relief"

    meta: Dict[str, Any] = {
        "prompt_excerpt": str(prompt or "")[:240],
        "input_interpretation": _interpret_prompt_snapshot(prompt),
        "tone": tone,
        "source": source,
        "timestamp": time.time(),
        "min_relief_used": min_relief,
    }
    if context:
        meta["expression_context"] = {
            k: v for k, v in context.items()
            if k in ("dominant_axis", "coherence", "expression_pressure", "voice_tone", "lineage_id")
        }

    return ArticulationDecision(
        original=draft_text,
        candidate=candidate_text,
        selected=candidate_text if accepted else draft_text,
        accepted=accepted,
        reason=reason,
        original_score=original_score,
        candidate_score=candidate_score,
        original_pressure=original_pressure,
        candidate_pressure=candidate_pressure,
        pressure_relief=pressure_relief,
        safe=safe,
        metadata=meta,
    )


def record_decision(decision: ArticulationDecision) -> None:
    """Persist Aurora's articulation choice as learning feedback."""
    try:
        DECISION_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DECISION_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(decision), ensure_ascii=True) + "\n")
        TRACE_FILE.write_text(json.dumps(asdict(decision), indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        return

    try:
        summary = json.loads(SUMMARY_FILE.read_text(encoding="utf-8") or "{}") if SUMMARY_FILE.exists() else {}
        total = int(summary.get("total", 0)) + 1
        accepted = int(summary.get("accepted", 0)) + (1 if decision.accepted else 0)
        prev_gain = float(summary.get("avg_pressure_relief", 0.0) or 0.0)
        summary.update({
            "total": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "acceptance_rate": round(accepted / max(1, total), 4),
            "avg_pressure_relief": round(prev_gain + ((decision.pressure_relief - prev_gain) / total), 4),
            "last_reason": decision.reason,
            "last_updated": time.time(),
        })
        SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def smooth_with_decision(
    draft: str,
    *,
    prompt: str = "",
    tone: str = "neutral",
    context: Optional[Dict[str, Any]] = None,
) -> ArticulationDecision:
    """
    Apply Aurora's articulation layer to a draft.

    Runs the draft through deterministic phrase repair, then evaluates
    whether the result reduces pressure. Records the decision either way.

    context: optional expression metadata from upstream pipeline
      keys: dominant_axis, coherence, expression_pressure, voice_tone, lineage_id
    """
    draft_text = (draft or "").strip()
    if not draft_text:
        decision = decide_articulation("", "", prompt=prompt, tone=tone,
                                       source="empty_draft", context=context)
        record_decision(decision)
        return decision

    candidate = _deterministic_candidate(draft_text)

    # Only pass a candidate if it actually changed — otherwise record as no pattern matched
    if not candidate or candidate == draft_text:
        candidate = ""
        source = "no_pattern_matched"
    else:
        source = "deterministic"

    decision = decide_articulation(
        draft_text, candidate,
        prompt=prompt, tone=tone, source=source, context=context,
    )
    if decision.accepted:
        decision.reason = "accepted_deterministic"
    record_decision(decision)
    return decision


def smooth_response(
    draft: str,
    *,
    prompt: str = "",
    tone: str = "neutral",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    return smooth_with_decision(draft, prompt=prompt, tone=tone, context=context).selected
