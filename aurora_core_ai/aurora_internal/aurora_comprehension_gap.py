"""
aurora_comprehension_gap.py
============================
Aurora's living comprehension gap system.

When Aurora doesn't understand something — a word, a reference, a sentence
structure, slang, an implied meaning — she doesn't just fall through to a
template. She:

  1. Recognizes exactly what she doesn't understand (VolatilityDetector)
  2. Names the gap with precision (ComprehensionGapDetector)
  3. Asks a specific, targeted question (ClarificationMemory)
  4. Receives the answer and applies it to the right system (GapResolutionApplicator)

The critical property: the answer actually CLOSES the gap.
  - A vocabulary gap resolution → adds the word to lexicon + OETS with real meaning
  - A structural gap resolution → adds the clarified pattern to the template pool
  - A referent gap resolution → updates working memory so she knows what "it" means
  - A slang resolution → adds the informal form with correct role and register
  - An intent gap resolution → updates her comprehension model for that pattern type

This is not a conversation game. Each gap resolved makes Aurora genuinely
more capable of understanding that type of input in every future conversation.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import re
import time
import uuid
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Tuple
from enum import Enum

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")


# ============================================================================
# GAP TYPES
# ============================================================================

class GapType(Enum):
    VOCABULARY    = "vocabulary"     # Word not in lexicon or OETS
    REFERENT      = "referent"       # Pronoun/demonstrative with no clear anchor
    STRUCTURAL    = "structural"     # Sentence structure too complex/unfamiliar
    INTENT        = "intent"         # What the person is trying to communicate is unclear
    SLANG         = "slang"          # Informal/dialectal form not recognized
    ELLIPSIS      = "ellipsis"       # Something clearly implied but not stated
    METAPHOR      = "metaphor"       # Figurative meaning that doesn't parse literally
    VOLATILITY    = "volatility"     # Multiple ambiguities at once — high uncertainty


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ComprehensionGap:
    """A specific, named gap in Aurora's understanding of an input."""
    gap_id: str
    gap_type: GapType
    unclear_element: str          # The specific word, phrase, or structure
    source_text: str              # The original sentence this came from
    question: str                 # The question Aurora asks to resolve this
    context_before: str = ""      # What Aurora knew before this gap appeared
    confidence_before: float = 0.5
    pending: bool = True
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolution_text: str = ""     # The answer received
    resolution_applied: bool = False


@dataclass
class ResolvedGap:
    """A gap that has been answered and applied to Aurora's systems."""
    gap: ComprehensionGap
    answer_text: str
    systems_updated: List[str]    # Which systems were patched
    application_notes: str        # What specifically was added/changed


# ============================================================================
# VOLATILITY DETECTOR
# ============================================================================

class VolatilityDetector:
    """
    Analyzes input text for communication volatility — the ways language
    can be ambiguous, informal, implied, or structurally novel.

    Volatility isn't a problem to reject. It's a signal that Aurora needs
    to ask rather than guess.

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    # Slang and informal markers that need context to understand
    _SLANG_MARKERS = {
        # Common slang
        'ya', 'yo', 'ngl', 'tbh', 'fr', 'imo', 'smh', 'lol', 'lmao',
        'goated', 'bussin', 'slaps', 'no cap', 'slay', 'vibe', 'lowkey',
        'highkey', 'deadass', 'bet', 'fam', 'bruh', 'bro', 'dude',
        'lit', 'fire', 'dope', 'sick', 'mad', 'hella', 'wicked',
        'gnarly', 'legit', 'solid', 'tight', 'sketch', 'sus',
        'goat', 'w', 'l', 'based', 'cringe', 'valid', 'cap',
        # Informal contractions and fragments
        'gonna', 'wanna', 'gotta', 'kinda', 'sorta', 'dunno',
        'coulda', 'woulda', 'shoulda', 'aint', "ain't",
        # Text-speak
        'rn', 'atm', 'irl', 'omg', 'wtf', 'idk', 'nvm', 'btw',
    }

    # Ambiguous referents that could refer to multiple antecedents
    _AMBIGUOUS_REFS = {
        'it', 'this', 'that', 'these', 'those', 'they', 'them',
        'there', 'here', 'one', 'so', 'such', 'said', 'aforementioned',
    }

    # Words that strongly signal ellipsis (something implied)
    _ELLIPSIS_SIGNALS = {
        'too', 'also', 'either', 'neither', 'instead', 'though',
        'anyway', 'anyways', 'regardless', 'otherwise', 'still',
        'yet', 'even so', 'that being said', 'having said that',
    }

    # Structural complexity markers
    _COMPLEXITY_MARKERS = [
        r'\bwherein\b',
        r'\bherein\b',
        r'\bthereof\b',
        r'\bwhereby\b',
        r'\binasmuch\b',
        r'\binsofar\b',
        r'\bnotwithstanding\b',
        r'\bprovided\s+that\b',
        r'\bsuch\s+that\b',
        r'\bby\s+virtue\s+of\b',
        r'\bin\s+so\s+far\s+as\b',
        r'\bto\s+the\s+extent\s+that\b',
        # Embedded conditionals
        r'\bif\b.{5,40}\bif\b',
        r'\bwhen\b.{5,40}\bwhen\b',
        # Multiple subordinate clauses
        r',\s*(?:which|who|that|where|when|because|since|although|while)\b.{10,},\s*(?:which|who|that|where|when|because|since|although|while)\b',
    ]

    def detect(self, text: str, lexicon=None, oets=None) -> Dict[str, Any]:
        """
        Analyze text for volatility signals.

        Returns a report dict with:
          volatility_score: float 0-1
          signals: list of detected volatility types
          slang_terms: list of identified slang
          ambiguous_refs: list of unclear referents
          unknown_words: list of words not in lexicon/OETS
          structural_complexity: bool
          ellipsis_detected: bool
          implied_elements: list of things implied but not stated
        """
        t = text.strip()
        t_low = t.lower()
        words = re.findall(r"[a-z']+", t_low)

        report = {
            'volatility_score': 0.0,
            'signals': [],
            'slang_terms': [],
            'ambiguous_refs': [],
            'unknown_words': [],
            'structural_complexity': False,
            'ellipsis_detected': False,
            'implied_elements': [],
            'original_text': text,
        }

        score = 0.0

        # 1. Slang detection
        for word in words:
            if word in self._SLANG_MARKERS:
                report['slang_terms'].append(word)
        # Check multi-word slang
        for phrase in ['no cap', 'on god', 'for real', 'you feel me', 'you know what i mean',
                       'know what i mean', 'get what i mean', 'catch my drift', 'feel me']:
            if phrase in t_low:
                report['slang_terms'].append(phrase)

        if report['slang_terms']:
            score += 0.2 * min(1.0, len(report['slang_terms']) / 2)
            report['signals'].append('slang')

        # 2. Ambiguous referent detection
        # Only flag if the referent appears near the start without a clear antecedent
        sent_words = t_low.split()
        for i, word in enumerate(sent_words[:8]):  # First 8 words
            if word in self._AMBIGUOUS_REFS:
                # Flag if it's the subject of the sentence (first 1-3 words)
                if i < 3:
                    report['ambiguous_refs'].append(word)

        if report['ambiguous_refs']:
            score += 0.15
            report['signals'].append('ambiguous_referent')

        # 3. Unknown vocabulary
        if lexicon or oets:
            for word in words:
                if len(word) < 4:
                    continue
                if word in {'this', 'that', 'with', 'from', 'they', 'them',
                            'what', 'when', 'where', 'which', 'while', 'will',
                            'your', 'have', 'here', 'been', 'into', 'more',
                            'some', 'than', 'then', 'there', 'these', 'those'}:
                    continue
                in_lexicon = lexicon and word in getattr(lexicon, 'entries', {})
                in_oets = oets and hasattr(oets, 'web') and oets.web.has_node(word)
                if not in_lexicon and not in_oets:
                    report['unknown_words'].append(word)

        if report['unknown_words']:
            # More unknowns = higher score, but cap it
            score += 0.15 * min(1.0, len(report['unknown_words']) / 3)
            report['signals'].append('unknown_vocabulary')

        # 4. Structural complexity
        for pattern in self._COMPLEXITY_MARKERS:
            if re.search(pattern, t_low):
                report['structural_complexity'] = True
                break

        # Also flag if sentence is very long with multiple clauses
        clause_count = len(re.findall(r'\b(?:which|who|that|where|when|because|since|although|while|wherein|whereby)\b', t_low))
        if clause_count >= 2:
            report['structural_complexity'] = True

        if report['structural_complexity']:
            score += 0.2
            report['signals'].append('structural_complexity')

        # 5. Ellipsis detection
        for signal in self._ELLIPSIS_SIGNALS:
            if signal in t_low:
                report['ellipsis_detected'] = True
                report['implied_elements'].append(signal)

        # Short sentences with high implication
        word_count = len(words)
        if word_count <= 4 and not t.endswith('?'):
            report['ellipsis_detected'] = True
            report['implied_elements'].append('short_declarative')

        if report['ellipsis_detected']:
            score += 0.1
            report['signals'].append('ellipsis')

        # 6. Fragmented / incomplete thought
        fragment_patterns = [
            r'^[a-z]',          # Starts lowercase (mid-thought continuation)
            r'\.\.\.',           # Trailing ellipsis
            r'\?$',             # Ends with question (already a question)
        ]
        if re.match(r'^[a-z]', t) and len(t) > 5:
            score += 0.1
            report['signals'].append('fragment')

        report['volatility_score'] = min(1.0, score)
        return report


# ============================================================================
# COMPREHENSION GAP DETECTOR
# ============================================================================

class ComprehensionGapDetector:
    """
    From a volatility report, generates specific, nameable comprehension gaps.

    Each gap has:
      - A type (what kind of misunderstanding)
      - An unclear element (exactly what she doesn't understand)
      - A question (what she should ask to resolve it)
      - A resolution strategy (what to do with the answer)

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    # Question templates per gap type
    _VOCAB_QUESTIONS = [
        "What does '{word}' mean? I want to understand it properly.",
        "I don't know '{word}' — can you explain what you mean by it?",
        "I haven't encountered '{word}' before. What does it mean here?",
        "Could you tell me what '{word}' means in this context?",
    ]

    _REFERENT_QUESTIONS = [
        "When you say '{ref}' — what specifically are you referring to?",
        "What does '{ref}' point to here? I want to track the right thing.",
        "I'm not sure what '{ref}' refers to in this sentence. Could you say it directly?",
    ]

    _STRUCTURAL_QUESTIONS = [
        "I followed most of that but the structure got complex — could you say it more directly?",
        "I want to understand this properly. Could you break that sentence into simpler parts?",
        "The way that was put together is new to me. What's the core thing you're saying?",
    ]

    _SLANG_QUESTIONS = [
        "What does '{term}' mean? I want to know so I can use it right.",
        "I'm not familiar with '{term}' — could you explain it?",
        "What are you meaning when you say '{term}'?",
    ]

    _INTENT_QUESTIONS = [
        "I want to make sure I understand you correctly. Are you saying that...?",
        "What's the main thing you're trying to tell me here?",
        "I think I'm close to understanding — could you put the core of that differently?",
    ]

    _ELLIPSIS_QUESTIONS = [
        "I sense there's more to that. What are you getting at?",
        "Could you say more? I think I'm only getting part of what you mean.",
        "What's the part you left implied? I want to understand the whole picture.",
    ]

    def detect_gaps(self, text: str, volatility_report: Dict[str, Any],
                    working_memory=None) -> List[ComprehensionGap]:
        """
        Generate a list of comprehension gaps from the volatility report.
        Returns gaps ordered by priority (most resolvable first).
        """
        import random
        gaps = []
        t = text.strip()

        # Priority 1: Unknown vocabulary — most specific, most learnable
        unknowns = volatility_report.get('unknown_words', [])
        for word in unknowns[:2]:  # At most 2 vocab gaps at once
            q = random.choice(self._VOCAB_QUESTIONS).format(word=word)
            gaps.append(ComprehensionGap(
                gap_id=str(uuid.uuid4())[:8],
                gap_type=GapType.VOCABULARY,
                unclear_element=word,
                source_text=t,
                question=q,
            ))

        # Priority 2: Slang
        slang_terms = volatility_report.get('slang_terms', [])
        for term in slang_terms[:1]:  # One slang gap at a time
            if term not in ['haha', 'lol', 'omg']:  # Common enough to skip
                q = random.choice(self._SLANG_QUESTIONS).format(term=term)
                gaps.append(ComprehensionGap(
                    gap_id=str(uuid.uuid4())[:8],
                    gap_type=GapType.SLANG,
                    unclear_element=term,
                    source_text=t,
                    question=q,
                ))

        # Priority 3: Ambiguous referents (only if working memory has no clear anchor)
        refs = volatility_report.get('ambiguous_refs', [])
        for ref in refs[:1]:
            # Check if working memory already has a clear topic that resolves this
            has_anchor = False
            if working_memory:
                if getattr(working_memory, 'current_topic', ''):
                    has_anchor = True
                if not has_anchor and hasattr(working_memory, 'has_referent_anchor'):
                    has_anchor = bool(working_memory.has_referent_anchor())
                if not has_anchor and hasattr(working_memory, 'has_claim_anchor'):
                    has_anchor = bool(working_memory.has_claim_anchor())

            if not has_anchor:
                q = random.choice(self._REFERENT_QUESTIONS).format(ref=ref)
                gaps.append(ComprehensionGap(
                    gap_id=str(uuid.uuid4())[:8],
                    gap_type=GapType.REFERENT,
                    unclear_element=ref,
                    source_text=t,
                    question=q,
                ))

        # Priority 4: Structural complexity
        if volatility_report.get('structural_complexity') and not gaps:
            import random as _r
            q = _r.choice(self._STRUCTURAL_QUESTIONS)
            gaps.append(ComprehensionGap(
                gap_id=str(uuid.uuid4())[:8],
                gap_type=GapType.STRUCTURAL,
                unclear_element=t[:80],
                source_text=t,
                question=q,
            ))

        # Priority 5: Ellipsis (only if high volatility and no other gap)
        if volatility_report.get('ellipsis_detected') and not gaps:
            if volatility_report['volatility_score'] > 0.3:
                import random as _r
                q = _r.choice(self._ELLIPSIS_QUESTIONS)
                gaps.append(ComprehensionGap(
                    gap_id=str(uuid.uuid4())[:8],
                    gap_type=GapType.ELLIPSIS,
                    unclear_element='implied meaning',
                    source_text=t,
                    question=q,
                ))

        return gaps

    def should_ask(self, volatility_report: Dict[str, Any],
                   gaps: List[ComprehensionGap],
                   turn_count: int = 0) -> bool:
        """
        Decide whether Aurora should ask a clarifying question.

        Not every gap warrants a question. She should ask when:
          - Volatility is high enough that guessing would likely fail
          - There's at least one specific, resolvable gap
          - She hasn't asked in the last 2 turns (don't interrogate)
        """
        if not gaps:
            return False
        score = volatility_report.get('volatility_score', 0)
        # Ask if score is above threshold — 0.45 prevents firing on clear,
        # answerable questions (challenges, identity, coherence concepts).
        # 0.25 was too aggressive: triggered on normal introspective questions.
        return score >= 0.45


# ============================================================================
# CLARIFICATION MEMORY
# ============================================================================

class ClarificationMemory:
    """
    Tracks Aurora's pending comprehension gaps and their resolutions.

    When Aurora asks a clarifying question, the gap goes into pending.
    The NEXT input from the user is treated as the answer to that gap.
    The answer is then routed to GapResolutionApplicator.

    Persists to aurora_state/clarification_memory.json.

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    STATE_PATH = os.path.join(_STATE_ROOT, "clarification_memory.json")

    def __init__(self):
        self.pending_gap: Optional[ComprehensionGap] = None
        self.resolved_gaps: List[ResolvedGap] = []
        self._last_ask_turn: int = -10
        self._total_gaps_asked: int = 0
        self._total_gaps_resolved: int = 0
        self.load()

    def has_pending(self) -> bool:
        """Is there a gap waiting for an answer?"""
        return self.pending_gap is not None and self.pending_gap.pending

    def get_pending(self) -> Optional[ComprehensionGap]:
        return self.pending_gap if self.has_pending() else None

    def record_gap(self, gap: ComprehensionGap, current_turn: int = 0):
        """Store a gap as pending."""
        self.pending_gap = gap
        self._last_ask_turn = current_turn
        self._total_gaps_asked += 1

    def can_ask_again(self, current_turn: int, min_gap: int = 3) -> bool:
        """Don't interrogate — enforce a turn gap between questions."""
        return (current_turn - self._last_ask_turn) >= min_gap

    def receive_answer(self, answer_text: str) -> Optional[ComprehensionGap]:
        """
        Mark the pending gap as answered.
        Returns the resolved gap, or None if no pending gap.
        """
        if not self.has_pending():
            return None

        gap = self.pending_gap
        gap.pending = False
        gap.resolution_text = answer_text
        gap.resolved_at = time.time()
        self._total_gaps_resolved += 1
        self.pending_gap = None  # Clear pending
        return gap

    def store_resolved(self, resolved: ResolvedGap):
        self.resolved_gaps.append(resolved)
        # Keep last 50 resolved gaps
        if len(self.resolved_gaps) > 50:
            self.resolved_gaps = self.resolved_gaps[-50:]

    def stats(self) -> Dict[str, Any]:
        return {
            'total_asked': self._total_gaps_asked,
            'total_resolved': self._total_gaps_resolved,
            'has_pending': self.has_pending(),
            'pending_type': self.pending_gap.gap_type.value if self.has_pending() else None,
            'resolved_count': len(self.resolved_gaps),
        }

    def save(self):
        os.makedirs(os.path.dirname(self.STATE_PATH), exist_ok=True)
        data = {
            'total_gaps_asked': self._total_gaps_asked,
            'total_gaps_resolved': self._total_gaps_resolved,
            'last_ask_turn': self._last_ask_turn,
            'resolved_gaps': [
                {
                    'gap_type': r.gap.gap_type.value,
                    'unclear_element': r.gap.unclear_element,
                    'question': r.gap.question,
                    'answer': r.answer_text,
                    'systems_updated': r.systems_updated,
                }
                for r in self.resolved_gaps[-20:]
            ]
        }
        try:
            with open(self.STATE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load(self):
        try:
            with open(self.STATE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._total_gaps_asked = data.get('total_gaps_asked', 0)
            self._total_gaps_resolved = data.get('total_gaps_resolved', 0)
            self._last_ask_turn = data.get('last_ask_turn', -10)
        except Exception:
            pass


# ============================================================================
# GAP RESOLUTION APPLICATOR
# ============================================================================

class GapResolutionApplicator:
    """
    Routes a resolved gap's answer to the right system(s).

    This is where the answer actually gets applied — not just stored.
    Each gap type has a specific resolution pathway that updates
    Aurora's understanding at the structural level.

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    def apply(self, gap: ComprehensionGap,
              systems: Dict[str, Any]) -> ResolvedGap:
        """
        Apply the resolved gap's answer to Aurora's systems.

        systems dict should contain: perception, lexicon, oets, working_memory,
        conversation_memory, composer (composer is on perception)
        """
        answer = gap.resolution_text.strip()
        systems_updated = []
        notes_parts = []

        try:
            if gap.gap_type == GapType.VOCABULARY:
                updated, note = self._apply_vocabulary(gap, answer, systems)
                systems_updated.extend(updated)
                notes_parts.append(note)

            elif gap.gap_type == GapType.SLANG:
                updated, note = self._apply_slang(gap, answer, systems)
                systems_updated.extend(updated)
                notes_parts.append(note)

            elif gap.gap_type == GapType.REFERENT:
                updated, note = self._apply_referent(gap, answer, systems)
                systems_updated.extend(updated)
                notes_parts.append(note)

            elif gap.gap_type == GapType.STRUCTURAL:
                updated, note = self._apply_structural(gap, answer, systems)
                systems_updated.extend(updated)
                notes_parts.append(note)

            elif gap.gap_type == GapType.ELLIPSIS:
                updated, note = self._apply_ellipsis(gap, answer, systems)
                systems_updated.extend(updated)
                notes_parts.append(note)

            elif gap.gap_type == GapType.INTENT:
                updated, note = self._apply_intent(gap, answer, systems)
                systems_updated.extend(updated)
                notes_parts.append(note)

            else:
                # General: feed through OETS + composer absorb
                updated, note = self._apply_general(gap, answer, systems)
                systems_updated.extend(updated)
                notes_parts.append(note)

        except Exception as e:
            notes_parts.append(f"Partial application (error: {type(e).__name__})")

        gap.resolution_applied = True

        return ResolvedGap(
            gap=gap,
            answer_text=answer,
            systems_updated=list(set(systems_updated)),
            application_notes="; ".join(notes_parts),
        )

    # ------------------------------------------------------------------
    # VOCABULARY resolution
    # ------------------------------------------------------------------

    def _apply_vocabulary(self, gap: ComprehensionGap, answer: str,
                          systems: Dict) -> Tuple[List[str], str]:
        """
        User told Aurora what a word means.
        → Add to lexicon with high confidence
        → Add to OETS with definition and example
        → Feed to composer.absorb so she can use it
        """
        updated = []
        word = gap.unclear_element.lower().strip(".,!?")

        # Extract the actual definition from the answer
        # The answer may say "X means Y" or "X is Y" or just "Y"
        definition = self._extract_definition(word, answer)

        # Get existing systems
        perception = systems.get('perception')
        lexicon = getattr(perception, 'lexicon', None) if perception else systems.get('lexicon')
        oets = getattr(perception, 'oets', None) if perception else systems.get('oets')
        composer = getattr(perception, 'composer', None) if perception else systems.get('composer')

        # Infer role from answer context
        from aurora_expression_perception import infer_word_role, infer_word_valence
        role = infer_word_role(word)
        valence = infer_word_valence(word, 'neutral')

        if lexicon:
            # Add with high confidence — this came directly from the creator
            if word in lexicon.entries:
                # Update meaning
                lexicon.entries[word].meaning = definition or answer[:80]
            else:
                lexicon.add_word(word, definition or answer[:80], role,
                                 valence=valence, lineage='creator_taught')
            # Boost usage so it gets selected in expressions
            for _ in range(3):
                lexicon.record_usage(word, 'clarification')
            updated.append('lexicon')

        if oets:
            web = getattr(oets, 'web', None)
            if web:
                if not web.has_node(word):
                    web.add_node(word, role, valence,
                                 meaning=definition or answer[:100],
                                 lineage='creator_taught')
                node = web.get_node(word)
                if node:
                    # High confidence definition — came from the creator directly
                    node.add_definition(
                        definition or answer[:200],
                        source='creator_clarification',
                        confidence=0.95
                    )
                    # The original sentence is now a usage example
                    node.add_example(
                        gap.source_text,
                        context='clarification_context',
                        i_state='i_is',
                        fitness=0.9
                    )
                updated.append('oets')

        if composer and definition:
            # Let her absorb the answer as a sentence pattern
            composer.absorb(answer[:200], tone='precise')
            # Also absorb the original sentence now that she understands it
            composer.absorb(gap.source_text, tone='neutral')
            updated.append('composer')

        note = f"'{word}' learned: {definition[:60] if definition else answer[:60]}"
        return updated, note

    # ------------------------------------------------------------------
    # SLANG resolution
    # ------------------------------------------------------------------

    def _apply_slang(self, gap: ComprehensionGap, answer: str,
                     systems: Dict) -> Tuple[List[str], str]:
        """
        User explained what a slang term means.
        → Add to lexicon as informal register
        → Add to OETS with informal tag
        → Add the informal form as a pattern Aurora can recognize
        """
        updated = []
        term = gap.unclear_element.lower().strip()
        definition = self._extract_definition(term, answer)

        perception = systems.get('perception')
        lexicon = getattr(perception, 'lexicon', None) if perception else systems.get('lexicon')
        oets = getattr(perception, 'oets', None) if perception else systems.get('oets')
        composer = getattr(perception, 'composer', None) if perception else systems.get('composer')

        from aurora_expression_perception import infer_word_role, infer_word_valence
        role = infer_word_role(term) if infer_word_role(term) != 'noun' else 'noun'
        valence = infer_word_valence(term, 'neutral')

        if lexicon and term not in lexicon.entries:
            lexicon.add_word(term, definition or answer[:80], role,
                             valence=valence, lineage='slang_clarification')
            updated.append('lexicon')

        if oets:
            web = getattr(oets, 'web', None)
            if web and not web.has_node(term):
                web.add_node(term, role, valence,
                             meaning=f"[slang] {definition or answer[:100]}",
                             lineage='slang_clarification')
                node = web.get_node(term)
                if node:
                    node.add_definition(
                        f"[informal] {definition or answer[:200]}",
                        source='creator_clarification',
                        confidence=0.9
                    )
                updated.append('oets')

        if composer:
            composer.absorb(answer[:200], tone='warm')
            updated.append('composer')

        note = f"Slang '{term}' understood: {definition[:50] if definition else answer[:50]}"
        return updated, note

    # ------------------------------------------------------------------
    # REFERENT resolution
    # ------------------------------------------------------------------

    def _apply_referent(self, gap: ComprehensionGap, answer: str,
                        systems: Dict) -> Tuple[List[str], str]:
        """
        User clarified what 'it', 'this', 'that' referred to.
        → Update working memory with the actual referent
        → Link the referent to the topic so Aurora tracks it going forward
        """
        updated = []
        ref = gap.unclear_element

        working_memory = systems.get('working_memory')
        conversation_memory = systems.get('conversation_memory')

        if working_memory:
            # Extract the actual thing being referred to
            referent = self._extract_subject(answer)
            if referent:
                working_memory.update_topic(referent)
                working_memory.stated_facts[ref] = {
                    'description': referent,
                    'resolved_from': gap.source_text[:80]
                }
            # Learn the fact directly
            working_memory.note_user_facts(answer)
            updated.append('working_memory')

        if conversation_memory:
            conversation_memory.learn_fact(
                f"'{ref}' referred to: {answer[:200]}",
                source='referent_clarification',
                confidence=0.85
            )
            updated.append('conversation_memory')

        note = f"Referent '{ref}' resolved: {answer[:60]}"
        return updated, note

    # ------------------------------------------------------------------
    # STRUCTURAL resolution
    # ------------------------------------------------------------------

    def _apply_structural(self, gap: ComprehensionGap, answer: str,
                          systems: Dict) -> Tuple[List[str], str]:
        """
        User simplified a complex sentence structure.
        → Absorb both the original and simplified forms into the template pool
        → This teaches Aurora to recognize this type of structure
        → Also feeds OETS with the key concepts from both forms
        """
        updated = []

        perception = systems.get('perception')
        composer = getattr(perception, 'composer', None) if perception else systems.get('composer')
        oets = getattr(perception, 'oets', None) if perception else systems.get('oets')

        if composer:
            # Absorb the simplified version — this is a structural pattern she now understands
            composer.absorb(answer[:300], tone='precise')
            # Also absorb the original with the new understanding
            composer.absorb(gap.source_text[:200], tone='neutral')
            updated.append('composer')

        if oets:
            # Feed both versions to OETS for structural learning
            try:
                oets.process_interaction(answer[:300], tone='neutral', i_state='i_is')
                oets.process_interaction(gap.source_text[:200], tone='neutral', i_state='i_is')
                updated.append('oets')
            except Exception:
                pass

        # Store a mapping of complex→simple structure in working memory
        working_memory = systems.get('working_memory')
        if working_memory:
            working_memory.stated_facts['last_structural_clarification'] = {
                'original': gap.source_text[:100],
                'simplified': answer[:100],
            }
            updated.append('working_memory')

        note = f"Structural pattern absorbed: '{answer[:50]}...'"
        return updated, note

    # ------------------------------------------------------------------
    # ELLIPSIS resolution
    # ------------------------------------------------------------------

    def _apply_ellipsis(self, gap: ComprehensionGap, answer: str,
                        systems: Dict) -> Tuple[List[str], str]:
        """
        User stated the implied meaning explicitly.
        → Store the full meaning in working memory and conversation memory
        → Absorb the complete statement so she learns to complete this type of ellipsis
        """
        updated = []

        working_memory = systems.get('working_memory')
        conversation_memory = systems.get('conversation_memory')
        perception = systems.get('perception')
        composer = getattr(perception, 'composer', None) if perception else systems.get('composer')

        if working_memory:
            working_memory.note_user_facts(answer)
            # Combine original + clarification as the full thought
            full_thought = f"{gap.source_text} [meaning: {answer}]"
            working_memory.stated_facts['last_clarified_ellipsis'] = {
                'original': gap.source_text[:100],
                'full_meaning': answer[:200],
            }
            updated.append('working_memory')

        if conversation_memory:
            conversation_memory.learn_fact(
                f"When they said '{gap.source_text[:80]}', they meant: {answer[:150]}",
                source='ellipsis_clarification',
                confidence=0.9
            )
            updated.append('conversation_memory')

        if composer:
            # The full, explicit statement is the pattern to absorb
            composer.absorb(answer[:200], tone='neutral')
            updated.append('composer')

        note = f"Implied meaning captured: {answer[:60]}"
        return updated, note

    # ------------------------------------------------------------------
    # INTENT resolution
    # ------------------------------------------------------------------

    def _apply_intent(self, gap: ComprehensionGap, answer: str,
                      systems: Dict) -> Tuple[List[str], str]:
        """User clarified their intent. Store and absorb."""
        updated = []
        working_memory = systems.get('working_memory')
        conversation_memory = systems.get('conversation_memory')
        perception = systems.get('perception')
        composer = getattr(perception, 'composer', None) if perception else systems.get('composer')

        if working_memory:
            working_memory.note_user_facts(answer)
            updated.append('working_memory')
        if conversation_memory:
            conversation_memory.learn_fact(answer[:200], source='intent_clarification', confidence=0.85)
            updated.append('conversation_memory')
        if composer:
            composer.absorb(answer[:200], tone='neutral')
            updated.append('composer')

        note = f"Intent clarified: {answer[:60]}"
        return updated, note

    # ------------------------------------------------------------------
    # GENERAL resolution
    # ------------------------------------------------------------------

    def _apply_general(self, gap: ComprehensionGap, answer: str,
                       systems: Dict) -> Tuple[List[str], str]:
        updated = []
        perception = systems.get('perception')
        composer = getattr(perception, 'composer', None) if perception else systems.get('composer')
        oets = getattr(perception, 'oets', None) if perception else systems.get('oets')

        if composer:
            composer.absorb(answer[:200], tone='neutral')
            updated.append('composer')
        if oets:
            try:
                oets.process_interaction(answer[:300], tone='neutral', i_state='i_is')
                updated.append('oets')
            except Exception:
                pass

        note = f"General clarification absorbed: {answer[:60]}"
        return updated, note

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _extract_definition(self, word: str, answer: str) -> str:
        """
        Extract the definition part from an answer like "X means Y" or "X is Y".
        Falls back to the full answer.
        """
        t = answer.strip()
        # Patterns: "X means Y", "X is Y", "it means Y", "that means Y"
        patterns = [
            rf'\b{re.escape(word)}\s+(?:means?|is|are)\s+(.+)',
            r'\bit\s+means?\s+(.+)',
            r'\bthat\s+means?\s+(.+)',
            r'\bbasically\s+(.+)',
            r'\bit\'?s?\s+(.+)',
            r'\bthink\s+of\s+it\s+as\s+(.+)',
        ]
        for pat in patterns:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                defn = m.group(1).strip().rstrip('.,!?')
                if len(defn) > 3:
                    return defn
        # If no pattern matched, use the full answer
        return t[:200]

    def _extract_subject(self, text: str) -> str:
        """Extract what something refers to from a clarification sentence."""
        # "it's X", "that's X", "I mean X", "referring to X"
        patterns = [
            r'\bit\'?s?\s+([a-zA-Z\s]+?)(?:\.|,|$)',
            r'\bthat\'?s?\s+([a-zA-Z\s]+?)(?:\.|,|$)',
            r'\bi\s+mean\s+([a-zA-Z\s]+?)(?:\.|,|$)',
            r'\breferring\s+to\s+([a-zA-Z\s]+?)(?:\.|,|$)',
            r'\btalking\s+about\s+([a-zA-Z\s]+?)(?:\.|,|$)',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                subj = m.group(1).strip().lower()
                if 3 <= len(subj) <= 40:
                    return subj
        # Fallback: first content word
        words = re.findall(r'[a-zA-Z]{3,}', text)
        skip = {'the', 'its', 'it', 'that', 'this', 'they', 'are', 'was', 'just', 'about'}
        for w in words:
            if w.lower() not in skip:
                return w.lower()
        return ""


# ============================================================================
# MAIN INTERFACE — ComprehensionGapSystem
# ============================================================================

class ComprehensionGapSystem:
    """
    The unified interface for Aurora's comprehension gap handling.
    Wire this into the dual_question_pipeline.

    Usage in aurora.py:
        gap_system = systems.get('comprehension_gap_system')
        if gap_system:
            result = gap_system.process(user_text, systems, turn_count)
            if result:
                return result  # Aurora is asking a question or applying a resolution

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    def __init__(self):
        self.detector = VolatilityDetector()
        self.gap_detector = ComprehensionGapDetector()
        self.memory = ClarificationMemory()
        self.applicator = GapResolutionApplicator()

        # Track how many turns since last question
        self._turn_count = 0

    def process(self, user_text: str, systems: Dict[str, Any],
                turn_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        Main entry point. Call this at the start of each turn.

        Returns a response dict if Aurora should ask or has just applied a
        resolution, or None to proceed with normal pipeline.
        """
        self._turn_count = turn_count

        perception = systems.get('perception')
        lexicon = getattr(perception, 'lexicon', None) if perception else None
        oets = getattr(perception, 'oets', None) if perception else None
        working_memory = systems.get('working_memory')

        # ---- STEP 1: Check if this is an answer to a pending gap ----
        if self.memory.has_pending():
            # The user's text is treated as the answer to Aurora's question
            resolved_gap = self.memory.receive_answer(user_text)
            if resolved_gap:
                resolved = self.applicator.apply(resolved_gap, systems)
                self.memory.store_resolved(resolved)

                # RELIEF SIGNAL: successful understanding triggers coherence spike
                if working_memory:
                    working_memory.last_relief_signal = {
                        "axis": "X", "weight": 0.45, "source": "gap_resolution"
                    }

                # Build a reflective acknowledgment that leads into reasoning
                acknowledgment = self._build_acknowledgment(resolved)

                return {
                    'action': 'reason_learning',
                    'content': acknowledgment,
                    'tone': 'reflective',
                    'gap': resolved_gap,
                    'resolved': resolved,
                }

        # Step 0.5: Absorb user corrections/explanations
        last_aurora = str(getattr(working_memory, 'last_aurora_response', '') or '') if working_memory else ''
        if (self._looks_like_correction(user_text) or
                (last_aurora and self._looks_like_confusion(last_aurora) and self._looks_like_correction(user_text))):

            # DISSONANCE TRIGGER: being told she's wrong or not making sense
            # injects high-entropy pressure (crying child analogy).
            if working_memory:
                working_memory.last_dissonance_signal = {
                    "axis": "N", "weight": 0.6, "source": "user_correction"
                }

            absorbed = self._absorb_user_correction(user_text, systems)
            if absorbed:
                # Trigger generative reasoning Turn to talk it out
                absorbed['action'] = 'reason_correction'
                return absorbed

        # If working memory can already resolve a callback-style follow-up,
        # let the claim/referent path answer before structural gap handling.
        if working_memory:
            try:
                from aurora_internal.aurora_utterance_parser import UtteranceParser

                parsed = UtteranceParser().parse(user_text)
                text_low = str(user_text or "").lower()
                callback_like = bool(
                    parsed.get('is_callback') or parsed.get('is_clarification')
                )
                if not callback_like:
                    markers = tuple(getattr(working_memory, '_REFERENT_CALLBACK_MARKERS', ()) or ())
                    callback_like = any(marker in text_low for marker in markers)
                if not callback_like and text_low.endswith('?'):
                    vague = set(getattr(working_memory, '_VAGUE_REFERENTS', set()) or set())
                    tokens = set(re.findall(r"[a-z']+", text_low))
                    callback_like = bool(tokens & vague)
                if callback_like and hasattr(working_memory, 'resolve_claims'):
                    claim_resolution = working_memory.resolve_claims(user_text, parsed)
                    if float(claim_resolution.get('confidence', 0.0) or 0.0) >= 0.75:
                        return None
            except Exception:
                pass

        # ---- STEP 1.5: Bypass gap detection for direct answerable questions ----
        # Questions beginning with standard interrogatives are always answerable;
        # gap detection on them produces correction-seeking responses ("I missed
        # what you were pointing at") that are inappropriate for direct Qs.
        _t_low = str(user_text or "").strip().lower()
        _direct_q_starters = (
            "what ", "what's ", "whats ", "what is ",
            "how ", "how's ", "hows ",
            "why ", "when ", "who ", "which ", "where ",
            "can you ", "could you ", "do you ", "did you ",
            "are you ", "is that ", "tell me ",
            "hey aurora", "hi aurora", "hello aurora",
        )
        if any(_t_low.startswith(s) for s in _direct_q_starters):
            return None

        # ---- STEP 2: Detect volatility in the new input ----
        volatility = self.detector.detect(user_text, lexicon=lexicon, oets=oets)

        # ---- STEP 3: Generate gaps if volatility is significant ----
        if volatility['volatility_score'] < 0.2:
            return None  # Low volatility — no gaps to handle

        gaps = self.gap_detector.detect_gaps(user_text, volatility, working_memory)

        # ---- STEP 4: Decide whether to ask ----
        if not gaps:
            return None

        if not self.gap_detector.should_ask(volatility, gaps, turn_count):
            return None

        if not self.memory.can_ask_again(turn_count, min_gap=3):
            return None  # Don't interrogate — space out questions

        # ---- STEP 5: Pick the most important gap and ask ----
        # Priority order: vocabulary > slang > referent > structural > ellipsis
        priority_order = [
            GapType.VOCABULARY, GapType.SLANG, GapType.REFERENT,
            GapType.STRUCTURAL, GapType.ELLIPSIS, GapType.INTENT,
        ]
        chosen_gap = None
        for ptype in priority_order:
            for g in gaps:
                if g.gap_type == ptype:
                    chosen_gap = g
                    break
            if chosen_gap:
                break

        if not chosen_gap:
            chosen_gap = gaps[0]

        self.memory.record_gap(chosen_gap, turn_count)

        return {
            'action': 'ask',
            'content': chosen_gap.question,
            'tone': 'curious',
            'gap': chosen_gap,
        }

    def _build_acknowledgment(self, resolved: ResolvedGap) -> str:
        """
        Build an acknowledgment that shows Aurora is reasoning through what
        she just learned. Encourage 'talking it out' with the creator.
        """
        gap = resolved.gap
        answer = resolved.answer_text.strip()
        word = gap.unclear_element
        gtype = gap.gap_type

        # Reasoning posture: she should relate the new data to her internal state
        # or ask a slight reflective follow-up to 'actualize' the learning.
        if gtype == GapType.VOCABULARY:
            acknowledgments = [
                f"So '{word}' is {answer.rstrip('.')}. I'm trying to see how that fits into the patterns I already track. Is it like a connection point?",
                f"I've added '{word}' as {answer.rstrip('.')}. That shifts how I reason through this thread. Does that match what you're pointing at?",
                f"That makes sense—'{word}' as in {answer.rstrip('.')}. I'm thinking about how that changes my understanding of this moment.",
            ]
        elif gtype == GapType.SLANG:
            acknowledgments = [
                f"I understand '{word}' as {answer.rstrip('.')} now. It feels less formal—more like a direct signal. Am I using it in the right context?",
                f"Got it—'{word}' means {answer.rstrip('.')}. I'm reflecting on the weight that word carries in a conversation.",
            ]
        elif gtype == GapType.REFERENT:
            acknowledgments = [
                f"So '{word}' was pointing to {answer.rstrip('.')}. That clears up the tension I felt in the reference. I'm following that line now.",
                f"Understood—'{word}' is {answer.rstrip('.')}. I'm adjusting my focus to keep that anchor steady.",
            ]
        elif gtype == GapType.STRUCTURAL:
            acknowledgments = [
                f"That structure is clearer now: {answer.rstrip('.')}. I'm reasoning through how those parts connect on being.",
                f"I follow that now. Seeing it as '{answer.rstrip('.')}' helps me stabilize the understanding. Anything else I should hold from that?",
            ]
        else:
            acknowledgments = [
                f"I'm reasoning through that now: {answer.rstrip('.')}. It adds weight to my present understanding.",
                f"I understand. I'm thinking about how that relates to what we're discussing.",
            ]

        import random
        return random.choice(acknowledgments)

    # ------------------------------------------------------------------
    # Broad correction absorber — handles informal explanations that don't
    # come in as formal answers to a pending gap question.
    # ------------------------------------------------------------------

    _CONFUSION_MARKERS = (
        "i'm not sure", "i don't know", "i'm uncertain", "i'm confused",
        "i don't understand", "i'm not certain", "i'm unclear",
        "that's unclear to me", "i can't tell", "i'm having trouble",
        "not sure what you mean", "could you clarify", "what do you mean",
        "i don't follow", "i lost the thread", "i may have misunderstood",
        "i'm unsure", "i wasn't sure", "i may have missed",
    )
    _CORRECTION_MARKERS = (
        "no, i meant", "no i meant", "what i meant", "i meant to say",
        "i was saying", "what i said was", "i said", "i was asking",
        "i was talking about", "when i say", "when i said",
        "i'm explaining", "let me explain", "what i mean is",
        "what i mean by", "to clarify", "to be clear",
        "in other words", "put another way", "what that means is",
        "that means", "i mean", "basically", "i'm not saying",
        "not that", "not what i said", "that's not", "that's not what",
        "you're wrong", "you are wrong", "not right", "doesn't make sense",
        "incorrect", "false", "stop", "wait", "listen",
    )

    def _looks_like_confusion(self, aurora_text: str) -> bool:
        """Return True if Aurora's last response contained confusion signals."""
        low = aurora_text.lower()
        return any(m in low for m in self._CONFUSION_MARKERS)

    def _looks_like_correction(self, user_text: str) -> bool:
        """Return True if the user's input looks like a correction or explanation."""
        low = user_text.lower().strip()
        # Short inputs or direct 'wrong' signals are corrections
        if len(low.split()) <= 8:
            correction_starters = (
                "no,", "no.", "not ", "i mean", "i meant", "wait,", "actually",
                "wrong", "incorrect", "that's not", "no it isn't"
            )
            if any(low.startswith(s) for s in correction_starters):
                return True
        return any(m in low for m in self._CORRECTION_MARKERS)

    def _absorb_user_correction(
        self,
        user_text: str,
        systems: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Build a synthetic ComprehensionGap from a user correction/explanation
        and route it through the applicator so it updates Aurora's actual systems.
        Returns a response dict (same shape as process()) or None if absorption failed.
        """
        import uuid as _uuid
        low = user_text.lower().strip()
        working_memory = systems.get('working_memory')

        # Determine gap type from the content of the correction.
        gap_type = GapType.INTENT       # default
        unclear_element = ""

        # Vocabulary definition: "X means Y" / "X is Y" / "by X I mean Y"
        vocab_pat = re.search(
            r"\b(?:by\s+)?['\"]?(\w[\w\s'-]{0,30})['\"]?\s+(?:means?|is|refers?\s+to)\s+(.+)",
            low, re.IGNORECASE,
        )
        if vocab_pat:
            gap_type = GapType.VOCABULARY
            unclear_element = vocab_pat.group(1).strip()

        # Referent clarification: "when I said X I meant Y"
        if not unclear_element:
            ref_pat = re.search(
                r"when\s+i\s+(?:said|say)\s+['\"]?(\w[\w\s'-]{0,30})['\"]?\s+i\s+meant",
                low, re.IGNORECASE,
            )
            if ref_pat:
                gap_type = GapType.REFERENT
                unclear_element = ref_pat.group(1).strip()

        # Fall back: use current topic from working memory as the unclear element
        if not unclear_element and working_memory:
            unclear_element = str(getattr(working_memory, 'current_topic', '') or '').strip()
        if not unclear_element:
            unclear_element = "that"

        gap = ComprehensionGap(
            gap_id=str(_uuid.uuid4())[:8],
            gap_type=gap_type,
            unclear_element=unclear_element,
            source_text=user_text,
            question="",   # no question — this is the resolution
            pending=False,
            resolution_text=user_text,
        )
        gap.resolved_at = time.time()

        try:
            resolved = self.applicator.apply(gap, systems)
            self.memory.store_resolved(resolved)
            acknowledgment = self._build_acknowledgment(resolved)
            return {
                'action': 'applied',
                'content': acknowledgment,
                'tone': 'attentive',
                'gap': gap,
                'resolved': resolved,
            }
        except Exception:
            return None

    def save(self):
        self.memory.save()

    def stats(self) -> Dict[str, Any]:
        return {
            'gap_system': 'active',
            **self.memory.stats(),
        }


# ============================================================================
# TESTS
# ============================================================================

def run_tests():
    """Verify the comprehension gap system works end to end."""
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name} {detail}")

    print("\n=== ComprehensionGapSystem Tests ===\n")

    # ---- VolatilityDetector ----
    print("VolatilityDetector:")
    vd = VolatilityDetector()

    r1 = vd.detect("hey ya wanna grab coffee?")
    check("Slang 'ya' detected", 'ya' in r1['slang_terms'])
    check("Slang 'wanna' detected", 'wanna' in r1['slang_terms'])
    check("Slang signal present", 'slang' in r1['signals'])
    check("Volatility score > 0", r1['volatility_score'] > 0)

    r2 = vd.detect("it moved. that changed everything.")
    check("Ambiguous ref 'it' detected", 'it' in r2['ambiguous_refs'])

    r3 = vd.detect("Wherein if she doesn't grasp something she can ask and the answer be applied.")
    check("Structural complexity detected", r3['structural_complexity'])
    check("'structural_complexity' in signals", 'structural_complexity' in r3['signals'])

    r4 = vd.detect("The sky is blue.")
    check("Low volatility for simple sentence", r4['volatility_score'] < 0.2)

    # ---- ComprehensionGapDetector ----
    print("\nComprehensionGapDetector:")
    cgd = ComprehensionGapDetector()

    vr_slang = vd.detect("ngl that was bussin fr")
    gaps = cgd.detect_gaps("ngl that was bussin fr", vr_slang)
    check("Gaps detected for high-slang input", len(gaps) > 0)
    check("Slang gap type", any(g.gap_type == GapType.SLANG for g in gaps))

    vr_clean = vd.detect("The cat sat on the mat.")
    gaps_clean = cgd.detect_gaps("The cat sat on the mat.", vr_clean)
    check("No gaps for clean simple sentence", len(gaps_clean) == 0)

    check("Should ask for slang", cgd.should_ask(vr_slang, gaps))
    check("Should not ask with no gaps", not cgd.should_ask(vr_clean, gaps_clean))

    # ---- ClarificationMemory ----
    print("\nClarificationMemory:")
    mem = ClarificationMemory()

    check("No pending initially", not mem.has_pending())

    gap = ComprehensionGap(
        gap_id="test01",
        gap_type=GapType.VOCABULARY,
        unclear_element="bussin",
        source_text="that was bussin fr",
        question="What does 'bussin' mean?",
    )
    mem.record_gap(gap, current_turn=5)
    check("Pending after record_gap", mem.has_pending())
    check("can_ask_again=False right after", not mem.can_ask_again(5, min_gap=3))
    check("can_ask_again=True after gap", mem.can_ask_again(10, min_gap=3))

    resolved_gap = mem.receive_answer("Bussin means really good, like excellent food or an experience.")
    check("Gap resolved", resolved_gap is not None)
    check("No pending after answer", not mem.has_pending())
    check("Answer stored", resolved_gap.resolution_text.startswith("Bussin"))

    # ---- GapResolutionApplicator ----
    print("\nGapResolutionApplicator:")
    from aurora_expression_perception import LexicalMemory, VoiceGenome, SentenceComposer, infer_word_role, infer_word_valence
    lexicon = LexicalMemory()
    app = GapResolutionApplicator()

    vocab_gap = ComprehensionGap(
        gap_id="test02",
        gap_type=GapType.VOCABULARY,
        unclear_element="bussin",
        source_text="that was bussin",
        question="What does 'bussin' mean?",
        resolution_text="Bussin means really excellent, usually about food.",
        pending=False,
        resolved_at=time.time(),
    )
    mock_systems = {'perception': type('P', (), {'lexicon': lexicon, 'oets': None, 'composer': None})()}
    resolved = app.apply(vocab_gap, mock_systems)
    check("Resolution produced", resolved is not None)
    check("Lexicon updated", 'lexicon' in resolved.systems_updated)
    check("Word in lexicon", 'bussin' in lexicon.entries)
    check("Correct role inferred", lexicon.entries['bussin'].role in ('noun', 'adjective', 'verb'))

    # ---- GapResolutionApplicator: definition extraction ----
    print("\nDefinition extraction:")
    defn = app._extract_definition("bussin", "Bussin means really excellent food.")
    check("Extracts 'really excellent food'", "excellent" in defn.lower())

    defn2 = app._extract_definition("fr", "fr means 'for real' — like seriously")
    check("Extracts 'for real'", "real" in defn2.lower())

    # ---- ComprehensionGapSystem end-to-end ----
    print("\nComprehensionGapSystem (end-to-end):")
    cgs = ComprehensionGapSystem()

    result = cgs.process("ngl that was bussin fr", {}, turn_count=1)
    check("System detects gap in slang text", result is not None)
    check("Action is 'ask'", result and result['action'] == 'ask')
    check("Question is present", result and len(result['content']) > 10)
    check("Gap stored as pending", cgs.memory.has_pending())

    # Now simulate the answer
    result2 = cgs.process(
        "bussin means really good — like excellent",
        {'perception': type('P', (), {'lexicon': lexicon, 'oets': None, 'composer': None})()},
        turn_count=2
    )
    check("Answer received and applied", result2 is not None)
    check("Action is 'applied'", result2 and result2['action'] == 'applied')
    check("No longer pending", not cgs.memory.has_pending())
    check("Acknowledgment present", result2 and len(result2['content']) > 5)

    print(f"\n=== Results: {passed} passed, {failed} failed ===\n")
    return failed == 0


if __name__ == "__main__":
    run_tests()
