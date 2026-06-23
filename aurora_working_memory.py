#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_working_memory.py
========================
WorkingMemory: per-session short-term context for Aurora.
Tracks topics, claims, facts, conversation history, and semantic anchors.

Extracted from aurora.py to its dedicated module.
"""

import re
import json
import time
import hashlib
import logging
from collections import deque
from types import SimpleNamespace
from typing import Optional, Dict, Any, List, Tuple, Set
from dataclasses import field

from aurora_support_stack import UtteranceParser
from aurora_internal.aurora_language_state import _merge_native_meaning_bundle
from aurora_internal.aurora_identity_persistence import ConversationMemory

logger = logging.getLogger(__name__)


def _recall_semantic_sedimemory(systems, query, **kwargs):
    try:
        from aurora import _recall_semantic_sedimemory as _fn
        return _fn(systems, query, **kwargs)
    except Exception:
        return []


def _answer_from_sedimemory_context(user_text, recalled, **kwargs):
    try:
        from aurora import _answer_from_sedimemory_context as _fn
        return _fn(user_text, recalled, **kwargs)
    except Exception:
        return ""


def _render_runtime_intent(systems, core_claim, **kwargs):
    try:
        from aurora import _render_runtime_intent as _fn
        return _fn(systems, core_claim, **kwargs)
    except Exception:
        return core_claim or ""

class WorkingMemory:
    """
    Per-session short-term memory that tracks what's being talked about,
    what facts have been stated, and what was recently learned  -- so Aurora
    can connect events across turns instead of treating each one in isolation.
    """

    _COLOR_WORDS = {
        'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
        'black', 'white', 'gray', 'grey', 'brown', 'violet', 'cyan',
        'magenta', 'indigo', 'gold', 'silver', 'maroon', 'olive', 'teal',
    }
    _VAGUE_REFERENTS = {'it', 'this', 'that', 'these', 'those', 'they', 'them'}
    _REFERENT_CALLBACK_MARKERS = (
        "you said", "you were saying", "what you said", "what you meant",
        "when you said", "i meant", "i was asking", "that thing", "this thing",
        "i said it", "i told you", "i already told you", "i already said",
        "you already know", "you heard me", "as i said",
    )
    _WEAK_ANCHOR_LABELS = {
        'be', 'do', 'does', 'did', 'explain', 'go', 'have', 'help', 'is',
        'mean', 'means', 'need', 'want', 'was', 'were',
    }
    _SURFACE_META_ANCHORS = {
        'answer', 'answers', 'communication', 'context', 'conversation',
        'conversations', 'definition', 'definitions', 'dialogue', 'dialogues',
        'discussion', 'discussions', 'exchange', 'exchanges', 'interaction',
        'interactions', 'meaning', 'question', 'questions', 'response',
        'responses', 'talk', 'talking', 'thread', 'threads', 'topic', 'topics',
    }
    _EXPLICIT_MEANING_CONTINUITY_MARKERS = (
        'what did you mean', 'what do you mean', 'what you meant', 'mean by that',
        'what do i mean by', 'what do you think i mean by', 'what do you mean by',
        'why that and not', 'why that instead of', 'why not',
        'still apply', 'still applies', 'apply here', 'apply now', 'apply later',
        'apply to the present', 'apply to the future', 'apply to the past',
        'past consequences', 'future consequences', 'past effects', 'future effects',
        'preserve across turns', 'keep across turns',
        'what should i preserve', 'what should be preserved',
        'what should stay connected', 'what should stay anchored',
        'what happens to meaning', 'what breaks', 'what would break',
        'what falls apart', 'what fails', 'what degrades', 'what fragments',
        'why does that matter', 'why is that important', 'why does this matter',
    )
    _CONTEXT_CONTROL_SKIP = {
        'clear', 'context', 'correct', 'delete', 'drop', 'forget', 'ignore',
        'remove', 'scratch', 'thread', 'wrong',
    }
    _SESSION_UTTERANCE_SKIP_TERMS = {
        'again', 'back', 'before', 'earlier', 'from', 'part', 'phrase',
        'point', 'previous', 'prior', 'question', 'readress', 'readdress',
        'revisit', 'said', 'saying', 'statement', 'tell', 'term', 'thing',
        'used', 'using', 'where', 'word',
    }
    _SESSION_READDRESS_MARKERS = (
        'readdress', 'readress', 'address again', 'go back to', 'revisit',
        'previous statement', 'earlier statement', 'prior statement',
        'previous question', 'earlier question', 'prior question',
        'what i said before', 'where i used that word', 'where i used that term',
        'where i used that phrase', 'what did i say before',
        'what should you call me', 'what should i call me', 'what do you call me',
        'what name do you have for me', 'i told you', 'i already told you',
        'i said it', 'i already said', 'you already know',
    )
    _CLAIM_SKIP_SUBJECTS = {
        'how', 'what', 'why', 'where', 'when', 'who', 'which', 'it',
        'this', 'that', 'these', 'those', 'they', 'them', 'he', 'she',
        'we', 'you', 'i', 'my', 'your', 'our', 'their', 'there', 'here',
    }
    _CLAIM_RELATION_ALIASES = {
        'is': 'is',
        'are': 'is',
        'was': 'is',
        'were': 'is',
        'means': 'means',
        'mean': 'means',
        'causes': 'causes',
        'cause': 'causes',
        'creates': 'creates',
        'create': 'creates',
        'requires': 'requires',
        'require': 'requires',
        'needs': 'requires',
        'need': 'requires',
        'blocks': 'blocks',
        'block': 'blocks',
        'prevents': 'blocks',
        'prevent': 'blocks',
        'breaks': 'breaks',
        'break': 'breaks',
        'forms': 'forms',
        'form': 'forms',
        'anchors': 'anchors',
        'anchor': 'anchors',
        'grounds': 'grounds',
        'ground': 'grounds',
        'tracks': 'tracks',
        'track': 'tracks',
        'carries': 'carries',
        'carry': 'carries',
        'wires': 'wires',
        'wire': 'wires',
        'drives': 'drives',
        'drive': 'drives',
        'improves': 'improves',
        'improve': 'improves',
        'degrades': 'degrades',
        'degrade': 'degrades',
        'connects to': 'connects_to',
        'connect to': 'connects_to',
        'links to': 'connects_to',
        'link to': 'connects_to',
        'maps to': 'connects_to',
        'map to': 'connects_to',
        'relates to': 'relates_to',
        'relate to': 'relates_to',
        'pertains to': 'relates_to',
        'pertain to': 'relates_to',
    }
    _REPORTING_VERBS = {
        'says', 'said', 'thinks', 'thought', 'believes', 'believed',
        'claims', 'claimed', 'insists', 'insisted',
    }
    _LOCATION_PREPOSITION_TO_RELATION = {
        'in': 'located_in',
        'inside': 'located_in',
        'on': 'located_on',
        'at': 'located_at',
        'under': 'located_under',
        'by': 'located_near',
        'near': 'located_near',
    }
    _EXCLUSIVE_PREDICATE_WORDS = {
        'true', 'false', 'yes', 'no', 'on', 'off',
        'open', 'closed', 'present', 'absent',
    }

    def __init__(self):
        self.current_topic: str = ""
        self.topic_stack: list = []
        # Active contexts: parallel topics held simultaneously.
        # Maps topic label → {salience: float, opened_turn: int, last_turn: int}
        # Salience decays with idle turns; current_topic always stays at 1.0.
        self.active_contexts: Dict[str, Dict[str, Any]] = {}
        self.stated_facts: dict = {}       # {subject: {property: value, ...}}
        self.recent_entities: list = []
        self.last_search_results: list = []
        self.last_search_query: str = ""
        self.last_question_understood: dict = {}
        self.last_aurora_response: str = ""
        self.turn_count: int = 0
        self.recent_mentions = deque(maxlen=32)
        self.recent_claims = deque(maxlen=24)
        self.claim_conflicts = deque(maxlen=12)
        self.last_referent_resolution: dict = {}
        self.last_claim_resolution: dict = {}
        self.lineage_activation_state: Dict[str, Any] = {}
        self.lineage_activation_targets: List[str] = []
        self.lineage_runtime_flags: Dict[str, Any] = {}
        self.proposition_understanding_enabled: bool = True
        try:
            from aurora_internal.aurora_proposition_substrate import PropositionSubstrate as _PS
            self.proposition_substrate = _PS()
        except Exception:
            self.proposition_substrate = None
        # Semantic anchor pool: persists concept anchors beyond semantic_frames rotation.
        # Keys are normalized concept terms; values carry term, meaning, turn, weight.
        # Used by the understanding contract for long-horizon continuity scoring.
        self.semantic_anchor_pool: Dict[str, Dict[str, Any]] = {}
        self.last_uncertainty_focus: str = ""
        self.pending_lookup_offer: Dict[str, Any] = {}
        self.pending_hypothesis_offer: Dict[str, Any] = {}
        self.last_response_anchor_claim: Dict[str, Any] = {}
        self.last_conflict_relief: Dict[str, Any] = {}
        self.concept_meanings: Dict[str, Dict[str, Any]] = {}
        self.pending_concept_clarification: Dict[str, Any] = {}
        self.last_concept_anchor: str = ""
        self.last_lineage_emergence: List[Dict[str, Any]] = []
        self.last_behavior_alignment_request: Dict[str, Any] = {}
        self.semantic_frames = deque(maxlen=48)
        self.last_semantic_frame_resolution: Dict[str, Any] = {}
        self.recent_user_utterances = deque(maxlen=40)
        self.last_session_readdress_resolution: Dict[str, Any] = {}
        self.recent_response_forms = deque(maxlen=18)
        self.last_context_control: Dict[str, Any] = {}
        self._context_control_skip_text: str = ""
        self._context_control_response_text: str = ""
        self._skip_next_aurora_claim_ingest: bool = False
        self.pending_teaching_offer: bool = False

    def _ensure_runtime_deques(self) -> None:
        """Repair deque-backed runtime fields after JSON restore or list assignment."""
        specs = (
            ("recent_mentions", 32),
            ("recent_claims", 24),
            ("claim_conflicts", 12),
            ("semantic_frames", 48),
            ("recent_user_utterances", 40),
            ("recent_response_forms", 18),
        )
        for attr, maxlen in specs:
            value = getattr(self, attr, None)
            if isinstance(value, deque):
                if value.maxlen == maxlen:
                    continue
                items = list(value)
            else:
                try:
                    items = list(value or [])
                except Exception:
                    items = []
            setattr(self, attr, deque(items, maxlen=maxlen))

    def _is_broad_surface_meta_anchor(self, term: str) -> bool:
        normalized = self._normalize_mention(term)
        if not normalized:
            return False
        if normalized in self._SURFACE_META_ANCHORS:
            return True
        words = [
            word
            for word in re.findall(r"[a-z]{3,}", normalized)
            if word not in self._WEAK_ANCHOR_LABELS
        ]
        return len(words) == 1 and words[0] in self._SURFACE_META_ANCHORS

    def _is_explicit_meaning_or_continuity_request(
        self,
        user_text: str,
        understood: Optional[dict] = None,
    ) -> bool:
        text_low = str(user_text or "").lower()
        understood = dict(understood or {})
        if str(understood.get("query_type", "") or "") == "definition":
            return True
        return any(marker in text_low for marker in self._EXPLICIT_MEANING_CONTINUITY_MARKERS)

    def should_suppress_surface_meta_answer(
        self,
        user_text: str,
        *,
        understood: Optional[dict] = None,
        term: str = "",
    ) -> bool:
        if not self._is_broad_surface_meta_anchor(term):
            return False
        return not self._is_explicit_meaning_or_continuity_request(user_text, understood)

    def apply_lineage_activation(self, manifest: Dict[str, Any], payload: dict | None = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        self.lineage_activation_state = dict(manifest or {})
        target_ability = str(manifest.get('target_ability', '') or '')
        if target_ability and target_ability not in self.lineage_activation_targets:
            self.lineage_activation_targets.append(target_ability)

        runtime_contract = dict(manifest.get('runtime_contract', {}) or {})
        working_memory_schema = dict(runtime_contract.get('working_memory_schema', {}) or {})
        working_memory_schema.update(dict(payload.get('working_memory_schema', {}) or {}))
        shadow_state = dict(manifest.get('shadow_state', {}) or {})
        pipeline_flags = dict(shadow_state.get('pipeline', {}) or {})
        if not (
            bool(working_memory_schema.get('enable_proposition_substrate', False))
            or bool(pipeline_flags.get('proposition_understanding', False))
            or bool(pipeline_flags.get('proposition_graph_enabled', False))
        ):
            return {}

        from aurora_internal.aurora_proposition_substrate import PropositionSubstrate

        if self.proposition_substrate is None:
            self.proposition_substrate = PropositionSubstrate()

        activated_manifest = dict(manifest or {})
        activated_contract = dict(runtime_contract)
        activated_contract['working_memory_schema'] = working_memory_schema
        activated_manifest['runtime_contract'] = activated_contract
        self.lineage_runtime_flags = dict(pipeline_flags)
        self.proposition_understanding_enabled = True
        return dict(self.proposition_substrate.configure(activated_manifest) or {})

    def proposition_report(self) -> Dict[str, Any]:
        if self.proposition_substrate is None:
            return {
                'enabled': False,
                'targets': list(self.lineage_activation_targets),
            }
        out = dict(self.proposition_substrate.report() or {})
        out['enabled'] = bool(self.proposition_understanding_enabled)
        out['targets'] = list(self.lineage_activation_targets)
        return out

    def _normalize_mention(self, text: str) -> str:
        clean = re.sub(r"[^a-z0-9\s'\-]", " ", str(text or "").lower())
        return re.sub(r"\s+", " ", clean).strip()

    def _register_mention(self, label: str, kind: str, source: str, salience: float = 0.5):
        self._ensure_runtime_deques()
        normalized = self._normalize_mention(label)
        if (not normalized or normalized in self._VAGUE_REFERENTS or
                len(normalized) < 2):
            return

        for item in self.recent_mentions:
            if item.get('label') == normalized and item.get('source') == source:
                item['turn'] = self.turn_count
                item['salience'] = max(float(item.get('salience', 0.0)), salience)
                if salience >= float(item.get('salience', 0.0)):
                    item['kind'] = kind
                return

        if not isinstance(self.recent_mentions, deque):


            self.recent_mentions = deque(list(self.recent_mentions or []), maxlen=40)


        self.recent_mentions.appendleft({
            'label': normalized,
            'kind': kind,
            'source': source,
            'salience': max(0.0, min(1.0, float(salience))),
            'turn': self.turn_count,
        })

    def _is_weak_anchor_label(self, label: str) -> bool:
        normalized = self._normalize_mention(label)
        if not normalized or normalized in self._VAGUE_REFERENTS:
            return True
        parts = normalized.split()
        if not parts:
            return True
        if len(parts) == 1 and parts[0] in self._WEAK_ANCHOR_LABELS:
            return True
        return all(part in self._WEAK_ANCHOR_LABELS for part in parts)

    def _normalize_claim_object(self, text: str) -> str:
        normalized = self._normalize_mention(text)
        normalized = re.sub(r'^(?:the|a|an)\s+', '', normalized)
        return normalized.strip()

    def _canonical_relation(self, relation: str) -> str:
        normalized = self._normalize_mention(relation)
        return self._CLAIM_RELATION_ALIASES.get(normalized, normalized.replace(' ', '_'))

    def _build_claim(
        self,
        subject: str,
        relation: str,
        obj: str,
        source: str,
        negated: bool = False,
        raw_text: str = "",
        understood: dict | None = None,
    ) -> Dict[str, Any]:
        claim = {
            'subject': self._normalize_mention(subject),
            'relation': self._canonical_relation(relation),
            'object': self._normalize_claim_object(obj),
            'negated': bool(negated),
            'source': source,
            'turn': self.turn_count,
            'text': raw_text[:280],
            'topic': self._normalize_mention((understood or {}).get('topic', '')),
        }
        claim['summary'] = self._claim_to_text(claim)
        return claim

    def _copy_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(claim, dict):
            return {}
        out = dict(claim)
        summary = str(out.get('summary', '') or '').strip()
        if not summary:
            out['summary'] = self._claim_to_text(out)
        return out

    def _semantic_frame_id(self, kind: str, anchor: str, summary: str, source: str) -> str:
        raw = json.dumps(
            {
                'kind': str(kind or ''),
                'anchor': str(anchor or ''),
                'summary': str(summary or ''),
                'source': str(source or ''),
            },
            sort_keys=True,
        )
        return "SF:" + hashlib.sha1(raw.encode()).hexdigest()[:12]

    def _frame_terms(self, frame: Dict[str, Any]) -> set:
        terms = set()
        if not isinstance(frame, dict):
            return terms
        for key in ('anchor', 'summary'):
            for part in self._normalize_mention(frame.get(key, '')).split():
                if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS:
                    terms.add(part)
        roles = dict(frame.get('roles', {}) or {})
        for value in roles.values():
            for part in self._normalize_mention(value).split():
                if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS:
                    terms.add(part)
        return terms

    def _register_semantic_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_runtime_deques()
        if not isinstance(frame, dict):
            return {}
        summary = str(frame.get('summary', '') or '').strip()
        anchor = self._normalize_mention(frame.get('anchor', ''))
        if not summary or (not anchor and self._is_weak_anchor_label(summary)):
            return {}
        registered = dict(frame)
        registered['anchor'] = anchor
        registered['summary'] = summary
        registered['frame_id'] = self._semantic_frame_id(
            registered.get('kind', ''),
            anchor,
            summary,
            registered.get('source', ''),
        )
        for item in self.semantic_frames:
            if item.get('frame_id') == registered['frame_id']:
                item.update(registered)
                item['turn'] = self.turn_count
                return item
        if not isinstance(self.semantic_frames, deque):

            self.semantic_frames = deque(list(self.semantic_frames or []), maxlen=40)

        self.semantic_frames.appendleft(registered)
        return registered

    def _semantic_frame_from_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        claim_copy = self._copy_claim(claim)
        summary = str(claim_copy.get('summary', '') or self._claim_to_text(claim_copy)).strip()
        return {
            'kind': 'claim',
            'anchor': str(claim_copy.get('subject', '') or ''),
            'summary': summary,
            'roles': {
                'subject': str(claim_copy.get('subject', '') or ''),
                'relation': str(claim_copy.get('relation', '') or ''),
                'object': str(claim_copy.get('object', '') or ''),
                'topic': str(claim_copy.get('topic', '') or ''),
            },
            'source': str(claim_copy.get('source', '') or ''),
            'turn': int(claim_copy.get('turn', self.turn_count) or self.turn_count),
            'confidence': float(claim_copy.get('confidence', 0.76) or 0.76),
            'reason': 'claim_assertion',
        }

    def _semantic_frame_from_concept(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        term = str(concept.get('term', '') or '').strip()
        meaning = str(concept.get('meaning', '') or '').strip()
        contrast = str(concept.get('contrast', '') or '').strip()
        return {
            'kind': 'concept',
            'anchor': term,
            'summary': str(concept.get('summary', '') or f"{term} means {meaning}").strip(),
            'roles': {
                'term': term,
                'meaning': meaning,
                'contrast': contrast,
            },
            'source': str(concept.get('source', '') or ''),
            'turn': int(concept.get('turn', self.turn_count) or self.turn_count),
            'confidence': float(concept.get('confidence', 0.9) or 0.9),
            'reason': 'meaning_clarification',
        }

    def _utterance_terms(self, text: str, understood: dict | None = None) -> List[str]:
        seen = set()
        terms: List[str] = []

        def _push(raw: str):
            normalized = self._normalize_mention(raw)
            for part in normalized.split():
                if (
                    len(part) < 3 or
                    part in self._WEAK_ANCHOR_LABELS or
                    part in self._VAGUE_REFERENTS or
                    part in self._SESSION_UTTERANCE_SKIP_TERMS
                ):
                    continue
                if part in seen:
                    continue
                seen.add(part)
                terms.append(part)

        _push(text)
        if isinstance(understood, dict):
            _push(str(understood.get('topic', '') or ''))
            for value in list(understood.get('topic_words', []) or [])[:6]:
                _push(str(value or ''))
            for value in list(understood.get('entities', []) or [])[:4]:
                _push(str(value or ''))
        return terms[:18]

    def _register_user_utterance(
        self,
        text: str,
        understood: dict | None = None,
        *,
        claims: Optional[List[Dict[str, Any]]] = None,
        semantic_frames: Optional[List[Dict[str, Any]]] = None,
        concept_clarification: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw = str(text or '').strip()
        if not raw:
            return {}
        self._ensure_runtime_deques()
        understood = dict(understood or {})
        normalized = self._normalize_mention(raw)
        if self.recent_user_utterances:
            latest = dict(self.recent_user_utterances[0] or {})
            if (
                latest.get('normalized_text') == normalized and
                int(latest.get('turn', -1) or -1) == int(self.turn_count or 0)
            ):
                return latest

        concept = dict(concept_clarification or {})
        entry = {
            'turn': int(self.turn_count or 0),
            'text': raw[:2000],
            'normalized_text': normalized[:2000],
            'topic': self._normalize_mention(understood.get('topic', '')),
            'entities': [
                self._normalize_mention(entity)
                for entity in list(understood.get('entities', []) or [])[:4]
                if self._normalize_mention(entity)
            ],
            'topic_words': [
                self._normalize_mention(word)
                for word in list(understood.get('topic_words', []) or [])[:6]
                if self._normalize_mention(word)
            ],
            'is_question': bool(raw.endswith('?') or understood.get('utterance_type') == 'question'),
            'is_callback': bool(understood.get('is_callback')),
            'is_clarification': bool(understood.get('is_clarification')),
            'query_type': str(understood.get('query_type', '') or ''),
            'intent': str(_classify_input_intent(raw) or ''),
            'terms': self._utterance_terms(raw, understood),
            'claims': [self._copy_claim(item) for item in list(claims or [])[:3]],
            'semantic_frames': [
                {
                    'kind': str(frame.get('kind', '') or ''),
                    'anchor': self._normalize_mention(frame.get('anchor', '')),
                    'summary': str(frame.get('summary', '') or '').strip(),
                    'confidence': float(frame.get('confidence', 0.0) or 0.0),
                }
                for frame in list(semantic_frames or [])[:3]
                if isinstance(frame, dict)
            ],
            'concept_term': self._normalize_mention(concept.get('term', '')),
            'concept_meaning': str(concept.get('meaning', '') or '').strip(),
        }
        if not isinstance(self.recent_user_utterances, deque):

            self.recent_user_utterances = deque(list(self.recent_user_utterances or []), maxlen=40)

        self.recent_user_utterances.appendleft(entry)
        return entry

    def _detect_session_readdress_mode(self, text_low: str) -> str:
        clean = str(text_low or '').lower()
        if not clean:
            return ""
        if any(marker in clean for marker in self._SESSION_READDRESS_MARKERS):
            if any(token in clean for token in ('what did i say', 'remind me', 'repeat what i said')):
                return 'remind'
            return 'readdress'
        if re.search(r'\bwhat\s+did\s+i\s+say\s+before\b', clean):
            return 'remind'
        if re.search(r'\b(?:readdress|readress|revisit|go back to)\b', clean):
            return 'readdress'
        return ""

    def _resolve_session_readdress_anchor(self, user_text: str, understood: dict | None = None) -> str:
        text = str(user_text or '').strip()
        text_low = text.lower()
        quoted = re.findall(r"[\"']([^\"']{2,40})[\"']", text)
        for item in quoted:
            normalized = self._normalize_mention(item)
            if normalized and normalized not in self._SESSION_UTTERANCE_SKIP_TERMS:
                return normalized

        explicit_patterns = (
            r'\bused\s+([a-z][a-z0-9_\-]{2,40})\b',
            r'\bword\s+([a-z][a-z0-9_\-]{2,40})\b',
            r'\bterm\s+([a-z][a-z0-9_\-]{2,40})\b',
            r'\bphrase\s+([a-z][a-z0-9_\-\s]{2,40})\b',
        )
        for pat in explicit_patterns:
            match = re.search(pat, text_low)
            if not match:
                continue
            normalized = self._normalize_mention(match.group(1))
            if (
                normalized and
                normalized not in self._SESSION_UTTERANCE_SKIP_TERMS and
                normalized not in self._VAGUE_REFERENTS and
                not self._is_weak_anchor_label(normalized)
            ):
                return normalized

        try:
            resolved = self.resolve_concept_meaning(user_text, understood) or {}
        except Exception:
            resolved = {}
        term = self._normalize_mention(resolved.get('term', ''))
        if term:
            return term

        pending_term = self._normalize_mention(
            dict(self.pending_concept_clarification or {}).get('term', '')
        )
        if pending_term:
            return pending_term

        return self._normalize_mention(self.last_concept_anchor)

    def resolve_session_readdress(
        self,
        user_text: str,
        understood: dict | None = None,
    ) -> Dict[str, Any]:
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}

        text_low = str(user_text or '').lower()
        mode = self._detect_session_readdress_mode(text_low)
        result = {
            'matched': False,
            'mode': mode,
            'anchor_term': '',
            'confidence': 0.0,
            'matched_utterance': {},
            'clarification_turn': 0,
        }
        if not mode or not self.recent_user_utterances:
            self.last_session_readdress_resolution = result
            return result

        anchor_term = self._resolve_session_readdress_anchor(user_text, understood)
        clarification_turn = int(
            dict(self.concept_meanings.get(anchor_term, {}) or {}).get('turn', 0) or 0
        ) if anchor_term else 0
        current_terms = set(self._utterance_terms(user_text, understood))

        candidates: List[Tuple[float, Dict[str, Any]]] = []
        for idx, utterance in enumerate(self.recent_user_utterances):
            candidate = dict(utterance or {})
            candidate_text = str(candidate.get('normalized_text', '') or '')
            if not candidate_text or candidate_text == self._normalize_mention(user_text):
                continue

            score = max(0.0, 1.18 - idx * 0.05)
            terms = set(candidate.get('terms', []) or [])
            if anchor_term:
                if anchor_term in terms:
                    score += 0.9
                elif anchor_term in candidate_text:
                    score += 0.72
                else:
                    score -= 0.18
            if clarification_turn:
                turn = int(candidate.get('turn', 0) or 0)
                if turn < clarification_turn:
                    score += 0.26
                else:
                    score -= 0.34
            if current_terms and terms:
                score += 0.18 * len(current_terms & terms)
            if bool(candidate.get('is_clarification')):
                score -= 0.28
            if mode == 'readdress' and bool(candidate.get('is_question')):
                score += 0.12
            if mode == 'remind' and not bool(candidate.get('is_question')):
                score += 0.05
            if score >= 0.28:
                candidates.append((score, candidate))

        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            score, matched = candidates[0]
            result.update({
                'matched': True,
                'anchor_term': anchor_term,
                'confidence': round(min(1.0, float(score or 0.0)), 4),
                'matched_utterance': matched,
                'clarification_turn': clarification_turn,
            })

        self.last_session_readdress_resolution = result
        return result

    def _build_semantic_principle_frame(
        self,
        *,
        kind: str,
        anchor: str,
        summary: str,
        roles: Dict[str, Any],
        source: str,
        confidence: float,
        verification_needed: bool = False,
        reason: str = 'semantic_principle',
    ) -> Dict[str, Any]:
        return {
            'kind': str(kind or 'principle'),
            'anchor': self._normalize_mention(anchor),
            'summary': str(summary or '').strip(),
            'roles': dict(roles or {}),
            'source': str(source or ''),
            'turn': int(self.turn_count or 0),
            'confidence': max(0.0, min(1.0, float(confidence or 0.0))),
            'verification_needed': bool(verification_needed),
            'reason': str(reason or 'semantic_principle'),
        }

    def _infer_semantic_anchor(
        self,
        *values: Any,
        understood: dict | None = None,
    ) -> str:
        ordered: List[str] = []
        if understood:
            ordered.extend([
                str((understood or {}).get('topic', '') or ''),
                self.last_concept_anchor,
                self.current_topic,
            ])
            ordered.extend(
                str(item or '')
                for item in list((understood or {}).get('entities', []) or []) +
                list((understood or {}).get('topic_words', []) or [])
            )
        for value in values:
            ordered.append(str(value or ''))
        for candidate in ordered:
            normalized = self._normalize_claim_object(candidate)
            if not normalized:
                continue
            if len(normalized.split()) > 4:
                normalized = self._infer_concept_anchor_from_phrase(normalized)
            if normalized and not self._is_weak_anchor_label(normalized):
                return normalized
        return ""

    def note_semantic_principles(
        self,
        text: str,
        *,
        source: str = 'user',
        understood: dict | None = None,
    ) -> List[Dict[str, Any]]:
        raw = str(text or '').strip()
        if not raw or raw.endswith('?'):
            return []
        if understood is None:
            try:
                understood = UtteranceParser().parse(raw)
            except Exception:
                understood = {}

        native = self._native_turn_payload(raw, understood)
        normalized = (
            native["native_text"].rstrip('.! ').strip()
            if native.get("has_native_projection")
            else raw.rstrip('.! ').strip()
        )
        frames: List[Dict[str, Any]] = []
        seen_keys = set()

        def _remember(frame: Dict[str, Any]) -> None:
            if not frame:
                return
            registered = self._register_semantic_frame(frame)
            if not registered:
                return
            key = (
                str(registered.get('kind', '') or ''),
                str(registered.get('anchor', '') or ''),
                str(registered.get('summary', '') or ''),
            )
            if key in seen_keys:
                return
            seen_keys.add(key)
            frames.append(dict(registered))
            anchor = str(registered.get('anchor', '') or '')
            if anchor and not self._is_weak_anchor_label(anchor):
                self._register_mention(anchor, 'semantic_frame', source, 0.82)
            for part in self._frame_terms(registered):
                self._register_mention(part, 'semantic_frame', source, 0.68)

        if native.get("has_native_projection"):
            native_anchor = self._infer_semantic_anchor(
                native["understood"].get("topic", ""),
                native["noncomp_state"].get("dominant_target", ""),
                native["noncomp_state"].get("basis_channel", ""),
                understood=native["understood"],
            )
            native_summary = str(
                native["understood"].get("summary", "")
                or native["native_text"]
                or ""
            ).strip()
            if native_anchor and native_summary:
                _remember(
                    self._build_semantic_principle_frame(
                        kind='native_projection',
                        anchor=native_anchor,
                        summary=native_summary,
                        roles={
                            'topic': native["understood"].get("topic", ""),
                            'constraint': native["understood"].get("constraint", ""),
                            'dimension': native["understood"].get("dimension", ""),
                        },
                        source=source,
                        confidence=0.82,
                        reason='native_projection',
                    )
                )

        eval_match = re.match(
            r'^([A-Za-z0-9][A-Za-z0-9_\-\s]{1,80}?)\s+matters(?:\s+because\s+(.+))?$',
            normalized,
            re.IGNORECASE,
        )
        if eval_match:
            subject = self._normalize_claim_object(eval_match.group(1))
            reason = self._normalize_claim_object(eval_match.group(2) or '')
            anchor = self._infer_semantic_anchor(subject, reason, understood=understood)
            if anchor:
                summary = f"{subject} matters"
                if reason:
                    summary = f"{summary} because {reason}"
                _remember(
                    self._build_semantic_principle_frame(
                        kind='evaluation',
                        anchor=anchor,
                        summary=summary,
                        roles={'subject': subject, 'reason': reason, 'predicate': 'matters'},
                        source=source,
                        confidence=0.84,
                        reason='evaluative_uptake',
                    )
                )

        coexistence_match = re.match(
            r'^([A-Za-z0-9][A-Za-z0-9_\-\s]{1,80}?)\s+can\s+both\s+be\s+(.+?)(?:\s+(?:if|when|because)\s+(.+))?$',
            normalized,
            re.IGNORECASE,
        )
        if coexistence_match:
            subject = self._normalize_claim_object(coexistence_match.group(1))
            predicate = self._normalize_claim_object(coexistence_match.group(2))
            condition = self._normalize_claim_object(coexistence_match.group(3) or '')
            anchor = self._infer_semantic_anchor(subject, predicate, condition, understood=understood)
            if anchor:
                summary = f"{subject} can both be {predicate}"
                if condition:
                    summary = f"{summary} when {condition}"
                _remember(
                    self._build_semantic_principle_frame(
                        kind='coexistence_principle',
                        anchor=anchor,
                        summary=summary,
                        roles={
                            'subject': subject,
                            'predicate': predicate,
                            'condition': condition,
                        },
                        source=source,
                        confidence=0.82,
                        reason='coexistence_uptake',
                    )
                )

        preserve_match = re.match(
            r'^([A-Za-z0-9][A-Za-z0-9_\-\s]{1,80}?)\s+should\s+stay\s+(.+?)(?:\s+across\s+turns)?$',
            normalized,
            re.IGNORECASE,
        )
        if preserve_match:
            subject = self._normalize_claim_object(preserve_match.group(1))
            value = self._normalize_claim_object(preserve_match.group(2))
            anchor = self._infer_semantic_anchor(subject, value, understood=understood)
            if anchor:
                _remember(
                    self._build_semantic_principle_frame(
                        kind='preservation_principle',
                        anchor=anchor,
                        summary=f"{subject} should stay {value}",
                        roles={'subject': subject, 'value': value, 'predicate': 'should_stay'},
                        source=source,
                        confidence=0.8,
                        reason='preservation_uptake',
                    )
                )

        causal_match = re.match(
            r'^if\s+(.+?)(?:,\s*|\s+then\s+)(.+)$',
            normalized,
            re.IGNORECASE,
        )
        if causal_match:
            condition = self._normalize_claim_object(causal_match.group(1))
            consequence = self._normalize_claim_object(causal_match.group(2))
            anchor = self._infer_semantic_anchor(condition, consequence, understood=understood)
            if anchor:
                _remember(
                    self._build_semantic_principle_frame(
                        kind='causal_principle',
                        anchor=anchor,
                        summary=f"if {condition}, {consequence}",
                        roles={'condition': condition, 'consequence': consequence},
                        source=source,
                        confidence=0.78,
                        reason='causal_uptake',
                    )
                )

        if frames:
            frame_anchor = str(frames[0].get('anchor', '') or '').strip()
            if frame_anchor and not self._is_weak_anchor_label(frame_anchor):
                self.update_topic(frame_anchor)
            self.last_semantic_frame_resolution = {
                'frame': dict(frames[0]),
                'confidence': float(frames[0].get('confidence', 0.0) or 0.0),
                'summary': str(frames[0].get('summary', '') or ''),
                'anchor': frame_anchor,
                'verification_needed': bool(frames[0].get('verification_needed', False)),
            }
        return frames

    def _semantic_frame_summary_claim(self, frame: Dict[str, Any]) -> str:
        if not isinstance(frame, dict):
            return ""
        kind = str(frame.get('kind', '') or '')
        roles = dict(frame.get('roles', {}) or {})
        anchor = str(frame.get('anchor', '') or '')
        summary = str(frame.get('summary', '') or '').strip()
        if kind == 'evaluation':
            reason = str(roles.get('reason', '') or '').strip()
            subject = str(roles.get('subject', '') or anchor).strip()
            return f"{subject} matters because {reason}" if reason else f"{subject} matters in this thread"
        if kind == 'preservation_principle':
            subject = str(roles.get('subject', '') or anchor).strip()
            value = str(roles.get('value', '') or '').strip()
            if subject and value:
                return f"{subject} should stay {value}"
        if kind == 'coexistence_principle':
            subject = str(roles.get('subject', '') or anchor).strip()
            predicate = str(roles.get('predicate', '') or '').strip()
            condition = str(roles.get('condition', '') or '').strip()
            if subject and predicate:
                return (
                    f"{subject} can both be {predicate} when {condition}"
                    if condition else
                    f"{subject} can both be {predicate}"
                )
        if kind == 'causal_principle':
            condition = str(roles.get('condition', '') or '').strip()
            consequence = str(roles.get('consequence', '') or '').strip()
            if condition and consequence:
                return f"if {condition}, {consequence}"
        return summary

    def compose_semantic_frame_acknowledgement(
        self,
        frame: Dict[str, Any],
        *,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        core_claim = self._semantic_frame_summary_claim(frame)
        if not core_claim:
            return ""
        supporting = [
            str(frame.get('anchor', '') or ''),
            str(frame.get('summary', '') or ''),
        ]
        return self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone='attentive',
            certainty=float(frame.get('confidence', 0.8) or 0.8),
            supporting_concepts=supporting,
            constraints=[str(frame.get('kind', '') or 'semantic_frame')],
        )

    def resolve_semantic_frame(
        self,
        user_text: str,
        understood: dict | None = None,
    ) -> Dict[str, Any]:
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}
        result = {
            'frame': {},
            'confidence': 0.0,
            'summary': '',
            'anchor': '',
            'verification_needed': False,
        }
        if not self.semantic_frames:
            self.last_semantic_frame_resolution = result
            return result

        text_low = str(user_text or '').lower()
        callback_like = bool(
            understood.get('is_callback') or
            understood.get('is_clarification') or
            any(marker in text_low for marker in self._REFERENT_CALLBACK_MARKERS)
        )
        target_terms = set()
        for value in (
            [str((understood or {}).get('topic', '') or ''), self.last_concept_anchor, self.current_topic] +
            [str(item or '') for item in list((understood or {}).get('entities', []) or [])] +
            [str(item or '') for item in list((understood or {}).get('topic_words', []) or [])]
        ):
            target_terms.update(
                part for part in self._normalize_mention(value).split()
                if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS
            )

        preferred_frame_id = str(
            dict(self.last_semantic_frame_resolution or {}).get('frame', {}).get('frame_id', '') or ''
        )
        candidates: List[Tuple[float, Dict[str, Any]]] = []
        for idx, frame in enumerate(self.semantic_frames):
            if not isinstance(frame, dict):
                continue
            kind = str(frame.get('kind', '') or '')
            if kind in {'claim', 'concept', 'speaker_identity', 'speaker_fact', 'behavior_alignment'}:
                continue
            score = max(0.0, 1.05 - idx * 0.05)
            frame_terms = self._frame_terms(frame)
            overlap = len(frame_terms & target_terms)
            if overlap:
                score += overlap * 0.18
            anchor = self._normalize_mention(frame.get('anchor', ''))
            if anchor and anchor in target_terms:
                score += 0.34
            if preferred_frame_id and str(frame.get('frame_id', '') or '') == preferred_frame_id:
                score += 0.28
            if callback_like:
                score += 0.18
            if any(
                marker in text_low for marker in (
                    'why', 'how', 'what breaks', 'what would break', 'what happens',
                    'what should', 'stay connected', 'stay anchored', 'matters',
                )
            ):
                score += 0.14
            candidates.append((score, dict(frame)))

        if not candidates:
            self.last_semantic_frame_resolution = result
            return result

        candidates.sort(key=lambda item: item[0], reverse=True)
        score, frame = candidates[0]
        result = {
            'frame': frame,
            'confidence': max(0.0, min(1.0, float(score or 0.0) * float(frame.get('confidence', 0.8) or 0.8))),
            'summary': str(frame.get('summary', '') or ''),
            'anchor': str(frame.get('anchor', '') or ''),
            'verification_needed': bool(frame.get('verification_needed', False)),
        }
        self.last_semantic_frame_resolution = dict(result)
        return result

    def _infer_concept_anchor_from_phrase(self, phrase: str) -> str:
        normalized = self._normalize_claim_object(phrase)
        skip = {'real', 'actual', 'just', 'mere', 'plain', 'only'}
        for part in normalized.split():
            if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS and part not in skip:
                return part
        return ""

    def _remember_response_form(self, family: str, variant: str, text: str = "") -> None:
        self._ensure_runtime_deques()
        if not isinstance(self.recent_response_forms, deque):

            self.recent_response_forms = deque(list(self.recent_response_forms or []), maxlen=40)

        self.recent_response_forms.appendleft({
            'family': str(family or ''),
            'variant': str(variant or ''),
            'text': str(text or ''),
            'turn': int(self.turn_count),
        })

    def _choose_response_variant(
        self,
        family: str,
        variants: List[Tuple[str, str]],
    ) -> Tuple[str, str]:
        if not variants:
            return "", ""

        recent_variants = [
            str(item.get('variant', '') or '')
            for item in self.recent_response_forms
            if str(item.get('family', '') or '') == family
        ][:4]
        last_text = str(self.last_aurora_response or '').strip().lower()

        for variant_id, text in variants:
            if variant_id in recent_variants:
                continue
            if last_text and text.strip().lower() == last_text:
                continue
            return variant_id, text

        for variant_id, text in variants:
            if not last_text or text.strip().lower() != last_text:
                return variant_id, text

        return variants[0]

    def compose_claim_acknowledgement(
        self,
        summary: str,
        systems: Optional[Dict[str, Any]] = None,
        claim: Optional[Dict[str, Any]] = None,
    ) -> str:
        clean = str(summary or '').strip()
        if not clean:
            return ""

        core_claim = clean
        claim = dict(claim or {})
        if claim:
            subject = str(claim.get('subject', '') or '').strip()
            relation = str(claim.get('relation', '') or '').strip()
            obj = str(claim.get('object', '') or '').strip()
            if subject and relation == 'requires' and obj:
                core_claim = f"{subject} depends on {obj}"
            elif subject and relation == 'means' and obj:
                core_claim = f"{subject} is being defined through {obj}"
            elif subject and relation == 'causes' and obj:
                core_claim = f"{subject} leads into {obj}"
            elif subject and relation == 'blocks' and obj:
                core_claim = f"{subject} stands in the way of {obj}"
            elif subject and relation == 'can_be' and obj:
                if 'conflict' in obj:
                    core_claim = f"{subject} can both hold at once when they do not actually conflict"
                else:
                    core_claim = f"{subject} can hold as {obj}"

        response = self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone='precise',
            relationship_signal='neutral',
            certainty=0.82,
            supporting_concepts=(core_claim or clean).split()[:6],
        )
        self._remember_response_form('claim_ack', clean, response)
        return response

    def compose_context_control_response(
        self,
        action: str,
        removed_summary: str = "",
        replacement_summary: str = "",
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        removed = str(removed_summary or 'that part').strip() or 'that part'
        replacement = str(replacement_summary or '').strip()

        if action == 'delete_context':
            # Give the language field just the concept — not internal tracking language.
            core_claim = removed
            tone = 'firm'
            certainty = 0.84
            family = 'context_delete'
        elif action == 'revise_context' and removed_summary and replacement:
            # The replacement concept is the content — no "replaces ... in active context".
            core_claim = replacement
            tone = 'precise'
            certainty = 0.86
            family = 'context_revise'
        elif action == 'revise_context':
            target = replacement or removed
            core_claim = target
            tone = 'precise'
            certainty = 0.8
            family = 'context_revise'
        else:
            core_claim = removed
            tone = 'gentle'
            certainty = 0.68
            family = 'context_clarify'

        # Fire the correction as a real field event before generating the response.
        # Without this the correction is text-only — it never reaches the constraint
        # field, so the field balancer has nothing to rebalance from and T stays pinned.
        try:
            ifield = (systems or {}).get("identity_field")
            if ifield and hasattr(ifield, "ingest_external_input"):
                ifield.ingest_external_input(
                    {"X": 0.3, "T": 0.10, "N": 0.40, "B": 0.45, "A": 0.70},
                    intensity=0.80,
                    source="correction_event",
                )
        except Exception:
            pass

        response = self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone=tone,
            relationship_signal='neutral',
            certainty=certainty,
            supporting_concepts=[removed, replacement] if replacement else [removed],
        )
        self._remember_response_form(family, core_claim, response)
        return response

    def _target_terms(self, targets: List[str]) -> set:
        terms = set()
        for target in list(targets or []):
            normalized = self._normalize_mention(target)
            if not normalized:
                continue
            for part in normalized.split():
                if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS:
                    terms.add(part)
        return terms

    def _claim_matches_targets(self, claim: Dict[str, Any], target_terms: set, target_labels: List[str]) -> bool:
        if not claim:
            return False
        labels = {self._normalize_mention(label) for label in list(target_labels or []) if self._normalize_mention(label)}
        fields = [
            str(claim.get('subject', '') or ''),
            str(claim.get('object', '') or ''),
            str(claim.get('topic', '') or ''),
            str(claim.get('summary', '') or self._claim_to_text(claim) or ''),
        ]
        normalized_fields = [self._normalize_mention(field) for field in fields if field]
        if labels and any(field in labels or field.startswith(tuple(f"{label} " for label in labels)) for field in normalized_fields):
            return True
        claim_terms = self._claim_terms(claim)
        return bool(target_terms and claim_terms & target_terms)

    def _mention_matches_targets(self, mention: Dict[str, Any], target_terms: set, target_labels: List[str]) -> bool:
        label = self._normalize_mention((mention or {}).get('label', ''))
        if not label:
            return False
        labels = {self._normalize_mention(item) for item in list(target_labels or []) if self._normalize_mention(item)}
        if label in labels:
            return True
        label_terms = {part for part in label.split() if len(part) >= 3}
        return bool(target_terms and label_terms & target_terms)

    def _extract_focus_bound_claims(
        self,
        text: str,
        focus_claim: Dict[str, Any],
        source: str,
        understood: dict | None = None,
    ) -> List[Dict[str, Any]]:
        if not focus_claim:
            return []
        subject = self._normalize_mention(focus_claim.get('subject', ''))
        if not subject or self._is_weak_anchor_label(subject):
            return []
        raw = str(text or '').strip()
        if not raw or raw.endswith('?'):
            return []
        raw = re.sub(r"\b(that|it|this|he|she)'s\b", r"\1 is", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\b(they)'re\b", r"\1 are", raw, flags=re.IGNORECASE)

        out: List[Dict[str, Any]] = []
        locative_match = re.match(
            r'^(?:no,\s*|actually,\s*)?(?:it|this|that|he|she|they|them)\s+'
            r'(?:is|are|was|were)\s+(not\s+)?(in|inside|on|at|under|by|near)\s+(.+)$',
            raw,
            re.IGNORECASE,
        )
        if locative_match:
            neg_token, prep, obj = locative_match.groups()
            relation = self._LOCATION_PREPOSITION_TO_RELATION.get(prep.lower(), 'located_at')
            out.append(self._build_claim(subject, relation, obj, source, bool(neg_token), raw, understood))
            return out

        copula_match = re.match(
            r'^(?:no,\s*|actually,\s*)?(?:it|this|that|he|she|they|them)\s+'
            r'(?:is|are|was|were)\s+(not\s+)?(.+)$',
            raw,
            re.IGNORECASE,
        )
        if copula_match:
            neg_token, obj = copula_match.groups()
            out.append(self._build_claim(subject, 'is', obj, source, bool(neg_token), raw, understood))
        return out

    def _selector_terms(self, selector: str) -> set:
        normalized = self._normalize_mention(selector)
        skip = {'one', 'ones', 'claim', 'claims', 'part', 'thread', 'that', 'this', 'it'}
        return {
            part for part in normalized.split()
            if len(part) >= 3 and part not in skip and part not in self._WEAK_ANCHOR_LABELS
        }

    def _match_claim_selector(
        self,
        selector: str,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        selector_terms = self._selector_terms(selector)
        if not selector_terms:
            return {}
        best_claim = {}
        best_score = 0.0
        for claim in list(candidates or []):
            claim_terms = self._claim_terms(claim) | set(
                self._normalize_mention(self._claim_to_text(claim)).split()
            )
            overlap = len(selector_terms & claim_terms)
            if overlap <= 0:
                continue
            score = float(overlap)
            obj = self._normalize_claim_object(claim.get('object', ''))
            if obj and obj in selector_terms:
                score += 0.4
            if score > best_score:
                best_score = score
                best_claim = dict(claim)
        return best_claim

    def _extract_conflict_selection(
        self,
        user_text: str,
    ) -> Dict[str, Any]:
        raw = str(user_text or '').strip()
        if not raw:
            return {}
        keep_match = re.search(r'\bkeep\s+(.+?)(?=\s+(?:and|but)\b|$)', raw, re.IGNORECASE)
        drop_match = re.search(r'\b(?:drop|remove|forget|clear|ignore)\s+(.+?)(?=\s+(?:and|but)\b|$)', raw, re.IGNORECASE)
        if not keep_match and not drop_match:
            return {}
        candidates = list(self.recent_claims)[:8]
        keep_claim = self._match_claim_selector(str(keep_match.group(1) or ''), candidates) if keep_match else {}
        drop_claim = self._match_claim_selector(str(drop_match.group(1) or ''), candidates) if drop_match else {}
        if keep_claim and drop_claim and self._claim_signature(keep_claim) == self._claim_signature(drop_claim):
            drop_claim = {}
        return {
            'keep_claim': keep_claim,
            'drop_claim': drop_claim,
        }

    def _extract_context_targets(
        self,
        user_text: str,
        understood: dict | None = None,
    ) -> Dict[str, Any]:
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}
        text_low = str(user_text or '').lower()
        explicit_target = ""
        patterns = (
            r'\bremove\s+(.+?)\s+from\s+context\b',
            r'\bclear\s+(.+?)\s+from\s+context\b',
            r'\bforget\s+(?:about\s+)?(.+)$',
            r'\bdrop\s+(.+)$',
            r'\bignore\s+(.+)$',
        )
        for pat in patterns:
            match = re.search(pat, text_low, re.IGNORECASE)
            if match:
                explicit_target = self._normalize_claim_object(match.group(1))
                break
        vague_context_targets = {
            'that', 'this', 'it', 'that part', 'this part',
            'that thread', 'this thread', 'that line', 'this line',
        }
        if explicit_target in self._VAGUE_REFERENTS or explicit_target in self._CONTEXT_CONTROL_SKIP:
            explicit_target = ""
        explicit_target = re.sub(
            r'\b(?:from context|for now|right now|please|instead|going forward)\b',
            '',
            explicit_target,
            flags=re.IGNORECASE,
        ).strip()
        if (
            explicit_target in self._VAGUE_REFERENTS or
            explicit_target in self._CONTEXT_CONTROL_SKIP or
            explicit_target in vague_context_targets
        ):
            explicit_target = ""

        focus_claim = dict((self.resolve_claims(user_text, understood) or {}).get('focus_claim', {}) or {})
        if not focus_claim and self.current_topic:
            current_anchor = self._normalize_mention(self.current_topic)
            for claim in self.recent_claims:
                if (
                    self._normalize_mention(claim.get('subject', '')) == current_anchor or
                    current_anchor in self._claim_terms(claim)
                ):
                    focus_claim = dict(claim)
                    break
        if not focus_claim and self.last_response_anchor_claim:
            focus_claim = self._copy_claim(self.last_response_anchor_claim)
        referents = self.resolve_referents(user_text, understood) or {}
        concept = self.resolve_concept_meaning(user_text, understood) or {}

        targets: List[str] = []
        if explicit_target:
            targets.append(explicit_target)
        topic = self._normalize_mention((understood or {}).get('topic', ''))
        if (
            topic and topic not in self._VAGUE_REFERENTS and
            topic not in self._CONTEXT_CONTROL_SKIP and
            not self._is_weak_anchor_label(topic)
        ):
            targets.append(topic)
        for item in list((understood or {}).get('entities', []) or []) + list((understood or {}).get('topic_words', []) or []):
            label = self._normalize_mention(item)
            if (
                label and label not in self._VAGUE_REFERENTS and
                label not in self._CONTEXT_CONTROL_SKIP and
                not self._is_weak_anchor_label(label)
            ):
                targets.append(label)
        referent_topic = self._normalize_mention(referents.get('topic', ''))
        if (
            referent_topic and referent_topic not in self._VAGUE_REFERENTS and
            referent_topic not in self._CONTEXT_CONTROL_SKIP and
            not self._is_weak_anchor_label(referent_topic)
        ):
            targets.append(referent_topic)
        concept_term = self._normalize_mention(concept.get('term', ''))
        if concept_term and not self._is_weak_anchor_label(concept_term):
            targets.append(concept_term)
        if focus_claim:
            for field in ('subject', 'object', 'summary'):
                label = self._normalize_mention(focus_claim.get(field, ''))
                if (
                    label and label not in self._VAGUE_REFERENTS and
                    label not in self._CONTEXT_CONTROL_SKIP and
                    not self._is_weak_anchor_label(label)
                ):
                    targets.append(label)
        if not targets and self.current_topic and not self._is_weak_anchor_label(self.current_topic):
            targets.append(self.current_topic)

        deduped: List[str] = []
        seen = set()
        for target in targets:
            normalized = self._normalize_mention(target)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)

        return {
            'explicit_target': explicit_target,
            'focus_claim': focus_claim,
            'referents': referents,
            'concept': concept,
            'targets': deduped,
            'target_terms': self._target_terms(deduped),
        }

    def detect_context_directive(self, user_text: str, understood: dict | None = None) -> Dict[str, Any]:
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}
        text_low = str(user_text or '').lower().strip()
        explicit_delete = any(
            phrase in text_low for phrase in (
                'forget this', 'forget that', 'forget it',
                'remove this from context', 'remove that from context', 'remove it from context',
                'clear this from context', 'clear that from context',
                'drop that', 'drop this', 'ignore that', 'ignore this',
                'scratch that', 'stop using that', 'do not use that', "don't use that",
            )
        ) or bool(re.search(
            r'\b(?:forget|remove|clear|drop|ignore)\s+(?:that|this|it|what\s+i\s+said|the\s+last)',
            text_low
        ))
        lexical_correction = bool(re.search(
                r"\b(?:no,\s*that(?:'s| is)?\s+not|that's not|that is not|i meant|i misspoke|that's wrong|that was wrong)\b",
                text_low,
            )
        )
        correction_like = bool(
            lexical_correction or
            str((understood or {}).get('utterance_type', '') or '') in {'correction', 'negation'}
        )
        target_info = self._extract_context_targets(user_text, understood)
        resolved_targets = list(target_info.get('targets', []) or [])
        concept_info = dict(target_info.get('concept', {}) or {})
        valid_concept = bool(
            str(concept_info.get('term', '') or '').strip() or
            str(concept_info.get('meaning', '') or '').strip()
        )
        grounded = bool(resolved_targets or target_info.get('focus_claim') or valid_concept)
        return {
            'detected': bool(explicit_delete or correction_like),
            'explicit_delete': bool(explicit_delete),
            'correction_like': bool(correction_like),
            'grounded': grounded,
            'target_info': target_info,
        }

    def extract_behavior_alignment_request(self, user_text: str) -> Dict[str, Any]:
        raw = str(user_text or '').strip()
        if not raw or raw.endswith('?'):
            return {}
        patterns = (
            r'^(?:please\s+)?i\s+(?:need|want|would\s+like)\s+you\s+to\s+(.+)$',
            r'^(?:please\s+)?i\s+(?:need|want|would\s+like)\s+your\s+(?:responses|reply|replies)\s+to\s+(.+)$',
            r'^(?:please\s+)?stop\s+(.+)$',
        )
        fragment = ""
        for pat in patterns:
            match = re.match(pat, raw, re.IGNORECASE)
            if match:
                fragment = str(match.group(1) or '').strip()
                break
        if not fragment:
            return {}
        fragment = re.sub(r'\s+', ' ', fragment).strip(' .')
        if len(fragment.split()) < 2:
            return {}

        recentered = fragment
        substitutions = (
            (r'\bmy\b', 'your'),
            (r'\bmine\b', 'yours'),
            (r'\bme\b', 'you'),
            (r'\bi\b', 'you'),
        )
        for pat, repl in substitutions:
            recentered = re.sub(pat, repl, recentered, flags=re.IGNORECASE)
        recentered = re.sub(r'\s+', ' ', recentered).strip(' .')
        if not recentered:
            return {}

        result = {
            'raw_fragment': fragment,
            'requested_behavior': recentered,
            'summary': f"my replies should {recentered}",
        }
        self.last_behavior_alignment_request = dict(result)
        return result

    def extract_user_identity_assertion(self, user_text: str) -> Dict[str, Any]:
        raw = str(user_text or '').strip()
        if not raw or raw.endswith('?'):
            return {}
        patterns = (
            r'\bmy\s+name\s+is\s+([A-Za-z][A-Za-z\'\-]{1,40})\b',
            r'\bcall\s+me\s+([A-Za-z][A-Za-z\'\-]{1,40})\b',
            r'\byou\s+can\s+call\s+me\s+([A-Za-z][A-Za-z\'\-]{1,40})\b',
            r'\bi\s+go\s+by\s+([A-Za-z][A-Za-z\'\-]{1,40})\b',
            r'\bi\s+am\s+called\s+([A-Za-z][A-Za-z\'\-]{1,40})\b',
            # Natural self-introduction: "I'm Sunni" / "I am Sunni"
            r"(?:^|\s)i(?:'m|m|\s+am)\s+([A-Z][a-z][A-Za-z\'\-]{1,39})\b",
        )
        for pat in patterns:
            match = re.search(pat, raw, re.IGNORECASE)
            if not match:
                continue
            value = str(match.group(1) or '').strip()
            if not value:
                continue
            clean_value = value.capitalize()
            # Reject common non-name words that often follow "I'm"
            _not_names = {
                'not', 'just', 'here', 'fine', 'okay', 'good', 'sorry', 'ready',
                'sure', 'trying', 'going', 'the', 'a', 'an', 'that', 'this',
                'your', 'her', 'him', 'them', 'their', 'our', 'its',
            }
            if clean_value.lower() in _not_names:
                continue
            return {
                'speaker': 'user',
                'field': 'name',
                'value': clean_value,
                'summary': f"user name is {clean_value}",
                'source_text': raw,
            }
        return {}

    def extract_user_owned_fact_assertion(self, user_text: str) -> Dict[str, Any]:
        raw = str(user_text or '').strip()
        if not raw or raw.endswith('?'):
            return {}
        patterns = (
            r'\bmy\s+([A-Za-z][A-Za-z0-9_\-\s]{1,40}?)\s+(?:is|are|was|were)\s+(.+)$',
        )
        for pat in patterns:
            match = re.search(pat, raw, re.IGNORECASE)
            if not match:
                continue
            field = self._normalize_mention(match.group(1))
            value = str(match.group(2) or '').strip()
            value = re.split(r'[.?!](?:\s|$)', value, maxsplit=1)[0].strip()
            value = re.sub(r'\s+', ' ', value).strip(' .')
            if (
                not field or
                field in {'name', 'identity label'} or
                field in self._VAGUE_REFERENTS or
                self._is_weak_anchor_label(field) or
                not value or
                len(value.split()) > 18
            ):
                continue
            return {
                'speaker': 'user',
                'field': field,
                'value': value,
                'summary': f"user {field} is {value}",
                'source_text': raw,
            }
        return {}

    def note_user_owned_fact(
        self,
        field: str,
        value: str,
        *,
        source: str = 'user',
        kind: str = 'speaker_fact',
        confidence: float = 0.92,
        reason: str = 'speaker_owned_fact',
    ) -> Dict[str, Any]:
        field_key = self._normalize_mention(field)
        clean_value = re.sub(r'\s+', ' ', str(value or '').strip()).strip(' .')
        if not field_key or not clean_value:
            return {}

        user_bucket = self.stated_facts.setdefault('user', {})
        user_bucket[field_key] = clean_value
        if field_key == 'name':
            user_bucket['identity_label'] = clean_value

        summary = f"user {field_key} is {clean_value}"
        frame = {
            'kind': kind,
            'anchor': 'user',
            'summary': summary,
            'roles': {
                'speaker': 'user',
                'field': field_key,
                'value': clean_value,
            },
            'source': source,
            'turn': self.turn_count,
            'confidence': float(confidence or 0.92),
            'reason': reason,
        }
        self._register_semantic_frame(frame)
        self._register_mention('user', 'speaker', source, 0.92)
        self._register_mention(field_key, kind, source, 0.88)
        for idx, part in enumerate(field_key.split()[:4]):
            if not self._is_weak_anchor_label(part):
                self._register_mention(part, kind, source, max(0.46, 0.82 - idx * 0.08))
        if len(clean_value.split()) <= 4 and not self._is_weak_anchor_label(clean_value):
            self._register_mention(clean_value, kind, source, 0.84)
        return {
            'speaker': 'user',
            'field': field_key,
            'value': clean_value,
            'summary': summary,
        }

    def note_user_identity_fact(
        self,
        field: str,
        value: str,
        *,
        source: str = 'user',
    ) -> Dict[str, Any]:
        return self.note_user_owned_fact(
            field,
            value,
            source=source,
            kind='speaker_identity',
            confidence=0.98,
            reason='speaker_owned_identity',
        )

    def note_behavior_alignment_request(
        self,
        user_text: str,
        *,
        source: str = 'user',
    ) -> Dict[str, Any]:
        request = dict(self.extract_behavior_alignment_request(user_text) or {})
        if not request:
            return {}

        requested_behavior = str(request.get('requested_behavior', '') or '').strip()
        summary = str(request.get('summary', '') or '').strip()
        frame = {
            'kind': 'behavior_alignment',
            'anchor': 'aurora_behavior',
            'summary': summary,
            'roles': {
                'speaker': 'user',
                'target': 'aurora',
                'requested_behavior': requested_behavior,
            },
            'source': source,
            'turn': self.turn_count,
            'confidence': 0.9,
            'reason': 'user_behavior_alignment',
        }
        self._register_semantic_frame(frame)
        self._register_mention('aurora behavior', 'behavior_alignment', source, 0.9)
        for idx, part in enumerate(re.findall(r"[a-z]{3,}", requested_behavior.lower())[:6]):
            if not self._is_weak_anchor_label(part):
                self._register_mention(part, 'behavior_alignment', source, max(0.44, 0.84 - idx * 0.08))
        return request

    def integrate_speaker_owned_utterance(
        self,
        user_text: str,
        understood: dict | None = None,
    ) -> Dict[str, Any]:
        identity = self.extract_user_identity_assertion(user_text)
        if identity:
            noted = self.note_user_identity_fact(
                str(identity.get('field', '') or 'identity'),
                str(identity.get('value', '') or ''),
                source='user',
            )
            return {
                'kind': 'user_identity',
                'handled': True,
                'summary': str(noted.get('summary', '') or identity.get('summary', '') or ''),
                'speaker': 'user',
                'field': str(identity.get('field', '') or ''),
                'value': str(identity.get('value', '') or ''),
                'confidence': 0.98,
            }

        owned_fact = self.extract_user_owned_fact_assertion(user_text)
        if owned_fact:
            noted = self.note_user_owned_fact(
                str(owned_fact.get('field', '') or ''),
                str(owned_fact.get('value', '') or ''),
                source='user',
            )
            return {
                'kind': 'speaker_fact',
                'handled': True,
                'summary': str(noted.get('summary', '') or owned_fact.get('summary', '') or ''),
                'speaker': 'user',
                'field': str(noted.get('field', '') or owned_fact.get('field', '') or ''),
                'value': str(noted.get('value', '') or owned_fact.get('value', '') or ''),
                'confidence': 0.94,
            }

        behavior = self.note_behavior_alignment_request(user_text, source='user')
        if behavior:
            return {
                'kind': 'behavior_alignment',
                'handled': True,
                'summary': str(behavior.get('summary', '') or ''),
                'speaker': 'user',
                'requested_behavior': str(behavior.get('requested_behavior', '') or ''),
                'confidence': 0.9,
            }
        return {}

    def render_speaker_owned_acknowledgement(
        self,
        speaker_event: Dict[str, Any],
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        kind = str((speaker_event or {}).get('kind', '') or '')
        if kind == 'user_identity':
            value = str((speaker_event or {}).get('value', '') or '').strip()
            if value:
                return self._render_from_comprehension_intent(
                    systems,
                    core_claim=f"your name is {value}",
                    intent_type='statement',
                    emotion_tone='precise',
                    relationship_signal='neutral',
                    certainty=0.95,
                    supporting_concepts=[value, 'name', 'user'],
                    constraints=['speaker_identity'],
                )
            return ""
        if kind == 'speaker_fact':
            field = str((speaker_event or {}).get('field', '') or '').strip()
            value = str((speaker_event or {}).get('value', '') or '').strip()
            if field and value:
                return self._render_from_comprehension_intent(
                    systems,
                    core_claim=f"your {field} is {value}",
                    intent_type='statement',
                    emotion_tone='precise',
                    relationship_signal='neutral',
                    certainty=float((speaker_event or {}).get('confidence', 0.92) or 0.92),
                    supporting_concepts=[field, value, 'user'],
                    constraints=['speaker_fact'],
                )
            return ""
        if kind == 'behavior_alignment':
            requested = str((speaker_event or {}).get('requested_behavior', '') or '').strip()
            core_claim = f"you want my replies to {requested}" if requested else str((speaker_event or {}).get('summary', '') or '')
            return self._render_from_comprehension_intent(
                systems,
                core_claim=core_claim,
                intent_type='statement',
                emotion_tone='careful',
                relationship_signal='alignment',
                certainty=float((speaker_event or {}).get('confidence', 0.86) or 0.86),
                supporting_concepts=[requested, 'reply', 'behavior'],
            )
        return self._render_from_comprehension_intent(
            systems,
            core_claim=str((speaker_event or {}).get('summary', '') or ''),
            intent_type='statement',
            emotion_tone='attentive',
            certainty=float((speaker_event or {}).get('confidence', 0.8) or 0.8),
        )

    def memory_sweep_snapshot(
        self,
        *,
        conversation_memory: Optional['ConversationMemory'] = None,
        max_topics: int = 5,
        max_claims: int = 5,
        max_concepts: int = 5,
    ) -> Dict[str, Any]:
        facts = []
        for topic, bucket in list(self.stated_facts.items())[:max_topics]:
            description = "; ".join(
                f"{key}={value}" for key, value in (bucket or {}).items() if key and value
            )
            facts.append({
                'topic': topic,
                'description': description or "no detail",
            })
        claims = [
            self._claim_to_text(claim)
            for claim in list(self.recent_claims)[:max_claims]
        ]
        concept_details = []
        for term, concept in list(self.concept_meanings.items())[:max_concepts]:
            profile = dict(concept.get('meaning_profile', {}) or {})
            axes = tuple(profile.get('axes') or ())
            concept_details.append({
                'term': term,
                'meaning': str(concept.get('meaning', '') or profile.get('label', '')),
                'axes': axes,
                'stage': str(concept.get('meaning_stage', '') or profile.get('stage', '')),
                'representation': str(concept.get('meaning_representation', '') or profile.get('representation', '')),
            })
        conversation_summary = {}
        if conversation_memory is not None:
            try:
                conversation_summary = conversation_memory.memory_sweep_summary()
            except Exception:
                conversation_summary = {}
        # Build a readable summary of all live contexts (ordered by salience).
        # No salience numbers in output — those are internal.
        bg_ctx = sorted(
            [(k, v['salience']) for k, v in self.active_contexts.items() if k != self.current_topic],
            key=lambda x: x[1], reverse=True,
        )
        ctx_summary = self.current_topic or 'none'
        if bg_ctx:
            bg_labels = [k for k, _s in bg_ctx[:3]]
            ctx_summary += " | also: " + ", ".join(bg_labels)
        location_summary = [{
            'name': 'working_memory',
            'counts': {
                'facts': len(self.stated_facts),
                'concepts': len(self.concept_meanings),
                'claims': len(self.recent_claims),
                'active_contexts': len(self.active_contexts),
            },
            'summary': f"active topic={ctx_summary}",
        }]
        if conversation_summary:
            location_summary.append({
                'name': 'conversation_memory',
                'counts': {
                    'entries': len(conversation_summary.get('entries_summary', [])),
                    'learned_facts': len(conversation_summary.get('learned_facts', [])),
                },
                'summary': conversation_summary.get('summary', ''),
            })
        return {
            'current_topic': self.current_topic,
            'topic_stack': list(self.topic_stack)[-max_topics:],
            'facts': facts,
            'concepts': concept_details,
            'claims': [claim for claim in claims if claim],
            'locations': location_summary,
            'conversation_memory': conversation_summary,
        }

    def answer_from_behavior_alignment(
        self,
        user_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        request = dict(self.last_behavior_alignment_request or {})
        requested_behavior = str(request.get('requested_behavior', '') or '').strip()
        if not requested_behavior:
            return ""

        text_low = str(user_text or '').lower()
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}
        behavior_markers = (
            'what did i ask',
            'what do you think i asked',
            'what did i want',
            'what do i want',
            'what did i need',
            'what do i need',
            'what did i tell you',
            'what did i mean',
            'what do you want from',
            'what do you need from',
            'want from you',
            'need from you',
            'understand what i want',
            'understand what i need',
            'respond',
            'reply',
            'replies',
            'responses',
            'wording',
            'say back',
            'carry',
            'repeat me',
            'mirror me',
        )
        callback_like = bool(
            understood.get('is_callback') or
            understood.get('is_clarification') or
            any(marker in text_low for marker in self._REFERENT_CALLBACK_MARKERS)
        )
        if not (callback_like or any(marker in text_low for marker in behavior_markers)):
            return ""

        return self._render_from_comprehension_intent(
            systems,
            core_claim=f"you asked me to {requested_behavior}",
            intent_type='statement',
            emotion_tone='precise',
            relationship_signal='alignment',
            certainty=0.88,
            supporting_concepts=[requested_behavior, 'reply', 'behavior'],
        )

    def answer_from_speaker_owned_facts(
        self,
        user_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        user_bucket = dict(self.stated_facts.get('user', {}) or {})
        if not user_bucket:
            return ""
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}
        text_low = self._normalize_mention(user_text)
        if not text_low:
            return ""

        best_field = ""
        best_score = 0.0
        text_terms = set(text_low.split())
        for field, value in user_bucket.items():
            field_key = self._normalize_mention(field)
            if not field_key or field_key == 'identity_label' or not str(value or '').strip():
                continue
            score = 0.0
            if f"my {field_key}" in text_low:
                score += 1.3
            field_terms = {
                part for part in field_key.split()
                if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS
            }
            overlap = len(field_terms & text_terms)
            if overlap:
                score += overlap * 0.34
            if field_key == 'name' and re.search(r'\b(?:my\s+name|who\s+am\s+i)\b', text_low):
                score += 1.4
            if score > best_score:
                best_score = score
                best_field = field_key
        if not best_field or best_score < 0.68:
            return ""

        value = str(user_bucket.get(best_field, '') or '').strip()
        if not value:
            return ""
        core_claim = f"I should call you {value}" if best_field == 'name' else f"your {best_field} is {value}"
        rendered = self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone='precise',
            relationship_signal='neutral',
            certainty=min(0.95, 0.78 + best_score * 0.1),
            supporting_concepts=[best_field, value, 'user'],
            constraints=['recall', 'speaker_fact'],
        )
        return str(rendered or "").strip()

    def answer_from_recent_utterance_recall(
        self,
        user_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self.recent_user_utterances:
            return ""
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}
        text_low = str(user_text or '').lower()
        current_terms = set(self._utterance_terms(user_text, understood))
        target_terms = set(dict(self._extract_context_targets(user_text, understood) or {}).get('target_terms', []) or [])
        best_match: Dict[str, Any] = {}
        best_score = 0.0
        normalized_now = self._normalize_mention(user_text)
        for idx, item in enumerate(self.recent_user_utterances):
            candidate = dict(item or {})
            candidate_text = str(candidate.get('text', '') or '').strip()
            candidate_norm = self._normalize_mention(candidate.get('normalized_text', '') or candidate_text)
            if not candidate_text or candidate_norm == normalized_now:
                continue
            score = max(0.0, 1.08 - idx * 0.06)
            terms = set(candidate.get('terms', []) or [])
            overlap = len(current_terms & terms)
            if overlap:
                score += overlap * 0.2
            if target_terms:
                score += 0.24 * len(target_terms & terms)
            if bool(candidate.get('is_clarification')):
                score -= 0.12
            if score > best_score:
                best_score = score
                best_match = candidate
        if not best_match or best_score < 0.9:
            return ""

        prior_text = str(best_match.get('text', '') or '').strip()
        if not prior_text:
            return ""
        # Don't echo user questions back as Aurora's first-person recall.
        if prior_text.endswith("?"):
            return ""
        core_claim = prior_text[:220]
        rendered = self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone='precise',
            relationship_signal='recognition',
            certainty=min(0.94, max(0.82, best_score)),
            supporting_concepts=[prior_text[:220], 'earlier', 'utterance'],
            constraints=['recall', 'utterance'],
        )
        return str(rendered or "").strip()

    def answer_from_context_carryover(
        self,
        user_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        speaker_answer = str(
            self.answer_from_speaker_owned_facts(
                user_text,
                understood=understood,
                systems=systems,
            )
            or ""
        ).strip()
        if speaker_answer:
            return speaker_answer

        text_low = str(user_text or '').lower()
        callback_like = bool(
            (understood or {}).get('is_callback') or
            (understood or {}).get('is_clarification') or
            any(marker in text_low for marker in self._REFERENT_CALLBACK_MARKERS)
        )
        definition_callback = callback_like and any(
            phrase in text_low for phrase in (
                'what do you mean by',
                'what did you mean by',
                'what do you mean',
                'what did you mean',
            )
        )
        if definition_callback:
            meaning_answer = str(
                self.answer_from_meanings(
                    user_text,
                    understood=understood,
                    systems=systems,
                )
                or ""
            ).strip()
            if meaning_answer:
                return meaning_answer

            semantic_frame_answer = str(
                self.answer_from_semantic_frames(
                    user_text,
                    understood=understood,
                    systems=systems,
                )
                or ""
            ).strip()
            if semantic_frame_answer:
                return semantic_frame_answer

            claim_answer = str(
                self.answer_from_claims(
                    user_text,
                    understood=understood,
                    systems=systems,
                )
                or ""
            ).strip()
            if claim_answer:
                return claim_answer

        if _is_understanding_challenge(user_text):
            return ""

        utterance_answer = str(
            self.answer_from_recent_utterance_recall(
                user_text,
                understood=understood,
                systems=systems,
            )
            or ""
        ).strip()
        if utterance_answer:
            return utterance_answer

        try:
            target_info = dict(self._extract_context_targets(user_text, understood) or {})
            targets = list(target_info.get('targets', []) or [])
        except Exception:
            targets = []

        if isinstance(systems, dict):
            sedimemory_queries = list(dict.fromkeys(targets[:4] + ([str(user_text or '').strip()] if str(user_text or '').strip() else [])))
            for query in sedimemory_queries:
                recalled = _recall_semantic_sedimemory(
                    systems,
                    query,
                    axis_filter=("T", "B", "A"),
                    max_results=5,
                    min_score=0.4,
                )
                rendered = _answer_from_sedimemory_context(
                    user_text,
                    recalled,
                    systems=systems,
                    understood=understood,
                )
                if rendered:
                    return rendered

        conversation_memory = systems.get('conversation_memory') if isinstance(systems, dict) else None
        if conversation_memory is not None and hasattr(conversation_memory, 'recall_about'):
            for target in targets[:4]:
                try:
                    recalled = list(conversation_memory.recall_about(target) or [])
                except Exception:
                    recalled = []
                if recalled:
                    rendered = _render_runtime_intent(
                        systems,
                        str(recalled[0]).strip(),
                        emotion_tone='precise',
                        relationship_signal='recognition',
                        certainty=0.82,
                        supporting_concepts=[target],
                        constraints=['recall', 'memory'],
                    )
                    if rendered:
                        return rendered
        return ""

    def apply_context_control(
        self,
        user_text: str,
        understood: dict | None = None,
        conversation_memory: Any = None,
        intent: str = "",
        systems: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}

        preview = self.detect_context_directive(user_text, understood)
        result = {
            'handled': False,
            'applied': False,
            'needs_clarification': False,
            'response': '',
            'tone': 'attentive',
            'confidence': 0.88,
            'action': '',
            'reason': '',
            'targets': [],
            'turn_text': str(user_text or '').strip(),
            'removed_claims': 0,
            'removed_mentions': 0,
            'removed_frames': 0,
            'persistent_removed': {},
            'added_claims': [],
            'added_concept': {},
        }
        if not preview.get('detected'):
            self.last_context_control = result
            return result

        target_info = dict(preview.get('target_info', {}) or {})
        targets = list(target_info.get('targets', []) or [])
        explicit_target = str(target_info.get('explicit_target', '') or '').strip()
        focus_claim = dict(target_info.get('focus_claim', {}) or {})
        focus_concept = dict(target_info.get('concept', {}) or {})
        conflict_selection = self._extract_conflict_selection(user_text)
        keep_selected_claim = dict(conflict_selection.get('keep_claim', {}) or {})
        drop_selected_claim = dict(conflict_selection.get('drop_claim', {}) or {})
        if keep_selected_claim:
            focus_claim = dict(keep_selected_claim)
        valid_focus_concept = bool(
            str(focus_concept.get('term', '') or '').strip() or
            str(focus_concept.get('meaning', '') or '').strip()
        )
        target_terms = set(target_info.get('target_terms', set()) or set())
        if drop_selected_claim:
            target_terms |= self._claim_terms(drop_selected_claim)
            for label in (
                self._claim_to_text(drop_selected_claim),
                str(drop_selected_claim.get('object', '') or ''),
                str(drop_selected_claim.get('subject', '') or ''),
            ):
                normalized = self._normalize_mention(label)
                if normalized and normalized not in targets:
                    targets.append(normalized)
        explicit_delete = bool(preview.get('explicit_delete'))
        correction_like = bool(preview.get('correction_like'))

        extracted_claims = self._extract_claims(user_text, source='user', understood=understood)
        if not extracted_claims and focus_claim:
            extracted_claims = self._extract_focus_bound_claims(
                user_text,
                focus_claim,
                source='user',
                understood=understood,
            )

        concept_clarification = {}
        if correction_like or explicit_delete:
            concept_clarification = self.note_concept_clarification(
                user_text,
                source='user',
                understood=understood,
            ) or {}

        has_replacement = bool(extracted_claims or concept_clarification or keep_selected_claim)
        if correction_like and not explicit_delete and not has_replacement:
            self.last_context_control = result
            self._context_control_response_text = ""
            return result
        if explicit_delete and not targets and not focus_claim and not valid_focus_concept:
            result.update({
                'handled': True,
                'needs_clarification': True,
                'response': "I can remove it, but I need to know what part of the thread you want out of context.",
                'reason': 'ambiguous_context_removal',
                'action': 'clarify_delete_target',
            })
            self.last_context_control = result
            self._context_control_response_text = str(result.get('response', '') or '')
            return result

        if correction_like and not preview.get('grounded') and not has_replacement:
            result.update({
                'handled': True,
                'needs_clarification': True,
                'response': "I can revise it, but I need to know which part I identified incorrectly and what it should be instead.",
                'reason': 'ungrounded_correction',
                'action': 'clarify_revision_target',
            })
            self.last_context_control = result
            self._context_control_response_text = str(result.get('response', '') or '')
            return result

        removed_claims: List[Dict[str, Any]] = []
        kept_claims = deque(maxlen=self.recent_claims.maxlen)
        for claim in self.recent_claims:
            if drop_selected_claim and self._claim_signature(claim) == self._claim_signature(drop_selected_claim):
                removed_claims.append(dict(claim))
                continue
            if keep_selected_claim and self._claim_signature(claim) == self._claim_signature(keep_selected_claim):
                kept_claims.append(claim)
                continue
            if self._claim_matches_targets(claim, target_terms, targets):
                removed_claims.append(dict(claim))
                continue
            if has_replacement and focus_claim and self._claims_conflict(claim, extracted_claims[0] if extracted_claims else focus_claim):
                removed_claims.append(dict(claim))
                continue
            kept_claims.append(claim)
        if removed_claims:
            self.recent_claims = deque(kept_claims, maxlen=24)

        removed_mentions = 0
        kept_mentions = deque(maxlen=self.recent_mentions.maxlen)
        for mention in self.recent_mentions:
            if self._mention_matches_targets(mention, target_terms, targets):
                removed_mentions += 1
                continue
            kept_mentions.append(mention)
        if removed_mentions:
            self.recent_mentions = kept_mentions

        removed_frames = 0
        kept_frames = deque(maxlen=self.semantic_frames.maxlen)
        for frame in self.semantic_frames:
            frame_terms = self._frame_terms(frame)
            if (target_terms and frame_terms & target_terms) or (
                targets and self._normalize_mention(frame.get('anchor', '')) in targets
            ):
                removed_frames += 1
                continue
            kept_frames.append(frame)
        if removed_frames:
            self.semantic_frames = kept_frames

        for target in targets:
            if target == self.current_topic:
                self.current_topic = ""
            self.topic_stack = [item for item in self.topic_stack if self._normalize_mention(item) != target]
            self.stated_facts.pop(target, None)
            if target in self.concept_meanings:
                self.concept_meanings.pop(target, None)
                if self.last_concept_anchor == target:
                    self.last_concept_anchor = ""

        if focus_claim and self._claim_matches_targets(self.last_response_anchor_claim, target_terms, targets):
            self.last_response_anchor_claim = {}
        elif targets and self._claim_matches_targets(self.last_response_anchor_claim, target_terms, targets):
            self.last_response_anchor_claim = {}

        if targets:
            referent_topic = self._normalize_mention(self.last_referent_resolution.get('topic', ''))
            if referent_topic in targets:
                self.last_referent_resolution = {}
            claim_focus = dict(self.last_claim_resolution.get('focus_claim', {}) or {})
            if self._claim_matches_targets(claim_focus, target_terms, targets):
                self.last_claim_resolution = {'claims': [], 'focus_claim': {}, 'confidence': 0.0, 'source': ''}

        persistent_removed = {}
        if conversation_memory is not None and hasattr(conversation_memory, 'forget_matching_context'):
            try:
                persistent_targets = list(targets)
                if not persistent_targets and focus_claim:
                    persistent_targets.extend([
                        str(focus_claim.get('subject', '') or ''),
                        str(focus_claim.get('object', '') or ''),
                        str(focus_claim.get('summary', '') or self._claim_to_text(focus_claim) or ''),
                    ])
                persistent_targets = [
                    self._normalize_mention(item)
                    for item in persistent_targets
                    if self._normalize_mention(item)
                ]
                if explicit_delete or any(target.startswith('user') for target in persistent_targets):
                    persistent_removed = dict(
                        conversation_memory.forget_matching_context(
                            persistent_targets,
                            reason='user_context_control',
                        ) or {}
                    )
            except Exception:
                persistent_removed = {}

        added_claims: List[Dict[str, Any]] = []
        if extracted_claims:
            for claim in extracted_claims:
                self.note_user_facts(claim.get('summary', '') or self._claim_to_text(claim))
            added_claims = self.note_claims(user_text, source='user', understood=understood)
            if not added_claims and extracted_claims:
                # Use focus-bound claims directly when the raw utterance stays pronoun-heavy.
                recent_snapshot = list(self.recent_claims)
                for claim in extracted_claims:
                    if not isinstance(self.recent_claims, deque):

                        self.recent_claims = deque(list(self.recent_claims or []), maxlen=40)

                    self.recent_claims.appendleft(claim)
                    self._register_mention(claim['subject'], 'fact', 'user', 0.84)
                    if claim.get('object') and not self._is_weak_anchor_label(claim['object']):
                        self._register_mention(claim['object'], 'fact', 'user', 0.78)
                    self._register_semantic_frame(self._semantic_frame_from_claim(claim))
                    recent_snapshot = [claim] + recent_snapshot[:7]
                    if self.proposition_substrate is not None:
                        try:
                            node = self.proposition_substrate.note_claim(claim, recent_claims=recent_snapshot)
                            claim['proposition_id'] = str(node.get('proposition_id', '') or '')
                            claim['branch_id'] = str(node.get('branch_id', '') or '')
                            claim['confidence'] = float(node.get('confidence', 0.0) or 0.0)
                        except Exception:
                            pass
                added_claims = extracted_claims

        if concept_clarification:
            term = str(concept_clarification.get('term', '') or '').strip()
            meaning = str(concept_clarification.get('meaning', '') or '').strip()
            if term:
                profile = _meaning_profile_for_value(meaning or term)
                if profile:
                    concept_clarification['meaning_profile'] = dict(profile)
                    concept_clarification['meaning_axes'] = tuple(
                        axis for axis in (profile.get('axes') or ()) if axis
                    )
                    concept_clarification['meaning_signature'] = str(profile.get('signature', '') or '')
                    concept_clarification['meaning_stage'] = str(profile.get('stage', '') or '')
                    concept_clarification['meaning_representation'] = str(profile.get('representation', '') or '')
                self.concept_meanings[term] = dict(concept_clarification)
                self.last_concept_anchor = term
                if term not in self.stated_facts:
                    self.stated_facts[term] = {}
                if meaning:
                    self.stated_facts[term]['meaning'] = meaning
                self._register_mention(term, 'concept', 'user', 0.94)
            self._register_semantic_frame(self._semantic_frame_from_concept(concept_clarification))

        if added_claims:
            anchor_claim = self._copy_claim(added_claims[0])
            self.last_response_anchor_claim = anchor_claim
            self.update_topic(anchor_claim.get('subject', '') or anchor_claim.get('object', ''))
        elif concept_clarification:
            self.update_topic(str(concept_clarification.get('term', '') or ''))
        elif explicit_delete and not has_replacement:
            self.last_response_anchor_claim = {}
            self.last_claim_resolution = {'claims': [], 'focus_claim': {}, 'confidence': 0.0, 'source': ''}
            self.last_referent_resolution = {}
            if not targets or self.current_topic in targets:
                self.current_topic = ""
            if not explicit_target:
                self.current_topic = ""
                self.last_concept_anchor = ""
                self.last_question_understood = {}
                self.last_response_anchor_claim = {}
                self.last_claim_resolution = {'claims': [], 'focus_claim': {}, 'confidence': 0.0, 'source': ''}
                self.last_referent_resolution = {}
                if self.topic_stack:
                    self.topic_stack = []

        removed_summary = ""
        if drop_selected_claim:
            removed_summary = self._claim_to_text(drop_selected_claim)
        if explicit_delete and not explicit_target and not removed_summary:
            removed_summary = self._normalize_mention(
                focus_claim.get('topic', '') or
                focus_claim.get('subject', '') or
                self.current_topic
            )
        if not removed_summary and removed_claims:
            removed_summary = self._claim_to_text(removed_claims[0])
        elif not removed_summary and targets:
            removed_summary = targets[0]
        replacement_summary = ""
        if added_claims:
            replacement_summary = self._claim_to_text(added_claims[0])
        elif keep_selected_claim:
            replacement_summary = self._claim_to_text(keep_selected_claim)
        elif concept_clarification:
            replacement_summary = str(concept_clarification.get('summary', '') or '')

        if explicit_delete and not has_replacement:
            if not removed_summary and targets:
                removed_summary = targets[0]
            result['action'] = 'delete_context'
            result['reason'] = 'user_withdrawal'
        elif has_replacement:
            result['action'] = 'revise_context'
            result['reason'] = 'user_correction'
        else:
            result['action'] = 'clarify_delete_target'
            result['reason'] = 'ambiguous_context_removal'
            result['needs_clarification'] = True

        result['response'] = self.compose_context_control_response(
            result['action'],
            removed_summary=removed_summary,
            replacement_summary=replacement_summary,
            systems=systems,
        )

        result.update({
            'handled': True,
            'applied': not result['needs_clarification'],
            'targets': targets,
            'removed_claims': len(removed_claims),
            'removed_mentions': removed_mentions,
            'removed_frames': removed_frames,
            'persistent_removed': persistent_removed,
            'added_claims': added_claims,
            'added_concept': concept_clarification,
        })
        preferred_resolution_claim: Dict[str, Any] = {}
        if added_claims:
            preferred_resolution_claim = dict(added_claims[0] or {})
        elif keep_selected_claim:
            preferred_resolution_claim = dict(keep_selected_claim)
        elif removed_claims:
            removed_subjects = [
                self._normalize_mention(claim.get('subject', ''))
                for claim in removed_claims
                if self._normalize_mention(claim.get('subject', ''))
            ]
            for claim in self.recent_claims:
                if any(self._subjects_match(claim.get('subject', ''), subject) for subject in removed_subjects):
                    preferred_resolution_claim = dict(claim or {})
                    break
        if not preferred_resolution_claim and focus_claim and self._claim_exists(focus_claim):
            preferred_resolution_claim = dict(focus_claim)
        self.refresh_claim_conflicts(
            systems=systems,
            preferred_claim=preferred_resolution_claim,
            reason=result['reason'] or result['action'],
        )
        self.last_context_control = dict(result)
        self._context_control_response_text = str(result.get('response', '') or '')
        if result['applied']:
            self._context_control_skip_text = str(user_text or '').strip()
        return result

    def _resolve_concept_anchor_for_clarification(self) -> str:
        prior = dict(self.last_question_understood or {})
        prior_invites_definition = bool(prior.get('is_clarification')) or str(
            prior.get('query_type', '') or ''
        ) in {'clarification', 'definition'}
        candidates = []
        if prior_invites_definition:
            candidates.append(self._normalize_mention(prior.get('topic', '')))
        candidates.append(self._normalize_mention(self.last_concept_anchor))
        if prior_invites_definition:
            candidates.append(self._normalize_mention(self.current_topic))
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen or self._is_weak_anchor_label(candidate):
                continue
            seen.add(candidate)
            return candidate
        return ""

    def note_concept_clarification(
        self,
        text: str,
        source: str = 'user',
        understood: dict | None = None,
    ) -> Dict[str, Any]:
        raw = str(text or '').strip()
        if not raw or source != 'user' or raw.endswith('?'):
            return {}
        if understood is None:
            try:
                understood = UtteranceParser().parse(raw)
            except Exception:
                understood = {}

        native = self._native_turn_payload(raw, understood)
        native_topic = self._normalize_mention(native["understood"].get('topic', ''))
        native_translation = str(
            native["understood"].get("summary", "")
            or native["native_text"]
            or ""
        ).strip()
        if native.get("has_native_projection") and (
            native["understood"].get("is_clarification")
            or str(native["understood"].get("query_type", "") or "").strip() in {'clarification', 'definition'}
        ):
            term = self._resolve_concept_anchor_for_clarification() or native_topic
            if term and native_translation and not self._is_weak_anchor_label(term):
                concept = {
                    'term': term,
                    'meaning': native_translation,
                    'contrast': str(native["noncomp_state"].get("dominant_target", "") or "").strip(),
                    'source': source,
                    'turn': self.turn_count,
                    'text': native_translation[:280],
                    'summary': f"{term} means {native_translation}",
                    'confidence': 0.86,
                    'verification_needed': False,
                    'anchor_mode': 'native_projection',
                }
                self.concept_meanings[term] = dict(concept)
                self.pending_concept_clarification = dict(concept)
                self._register_semantic_frame(self._semantic_frame_from_concept(concept))
                self.last_concept_anchor = term
                if term not in self.stated_facts:
                    self.stated_facts[term] = {}
                self.stated_facts[term]['meaning'] = native_translation
                if native["noncomp_state"].get("semantic_translation"):
                    self.stated_facts[term]['native_translation'] = str(native["noncomp_state"].get("semantic_translation", "") or "")
                if native["noncomp_state"].get("manifold_translation"):
                    self.stated_facts[term]['native_manifold'] = str(native["noncomp_state"].get("manifold_translation", "") or "")
                self._register_mention(term, 'concept', source, 0.94)
                for idx, word in enumerate(re.findall(r"[a-z]{3,}", native_translation.lower())[:4]):
                    if not self._is_weak_anchor_label(word):
                        self._register_mention(word, 'meaning', source, max(0.44, 0.78 - idx * 0.08))
                return concept

        raw_low = raw.lower()
        explicit_marker = (
            'i mean ' in raw_low or
            (' i mean ' in raw_low and raw_low.startswith('by ')) or
            bool(re.search(r'\bmeans\b', raw_low))
        )
        if not explicit_marker:
            return {}

        patterns = (
            r'^(?:no,\s*)?(?:i\s+(?:mean|meant))\s+([a-z][a-z0-9_\-\s]{1,40}?)(?:\s+(?:as|in|by|through))\s+(.+)$',
            r'^(?:by)\s+([a-z][a-z0-9_\-\s]{1,40}?)\s+i\s+mean\s+(.+)$',
            r'^([a-z][a-z0-9_\-\s]{1,40}?)\s+means\s+(.+)$',
        )
        term = ""
        meaning = ""
        contrast = ""
        concept_confidence = 0.9
        verification_needed = False
        anchor_mode = 'explicit'
        for pat in patterns:
            match = re.match(pat, raw, re.IGNORECASE)
            if match:
                term = self._normalize_mention(match.group(1))
                meaning = self._normalize_claim_object(match.group(2))
                break

        contrastive_match = re.match(
            r'^(?:no,\s*)?(?:i\s+(?:mean|meant))\s+(.+?),\s*not\s+(.+)$',
            raw,
            re.IGNORECASE,
        )
        if contrastive_match and (not term or not meaning):
            primary = self._normalize_claim_object(contrastive_match.group(1))
            contrast = self._normalize_claim_object(contrastive_match.group(2))
            inherited_term = self._resolve_concept_anchor_for_clarification()
            term = inherited_term or self._infer_concept_anchor_from_phrase(primary)
            meaning = f"{primary} rather than {contrast}".strip()
            if inherited_term:
                concept_confidence = 0.88
                verification_needed = False
                anchor_mode = 'contrastive_grounded'
            else:
                concept_confidence = 0.62
                verification_needed = True
                anchor_mode = 'contrastive_inherited'

        if not term or not meaning:
            inherited_term = self._resolve_concept_anchor_for_clarification()
            inherited_match = re.match(
                r'^(?:no,\s*)?(?:i\s+(?:mean|meant))\s+(.+)$',
                raw,
                re.IGNORECASE,
            )
            if inherited_term and inherited_match:
                inherited_low = inherited_term.lower()
                remainder = str(inherited_match.group(1) or '').strip()
                remainder_low = remainder.lower()
                explicit_restatement = (
                    remainder_low == inherited_low or
                    remainder_low.startswith(f"{inherited_low} ") or
                    remainder_low.startswith(f"{inherited_low} as ") or
                    remainder_low.startswith(f"{inherited_low} in ") or
                    remainder_low.startswith(f"{inherited_low} by ") or
                    remainder_low.startswith(f"{inherited_low} through ")
                )
                if remainder and not explicit_restatement:
                    term = inherited_term
                    meaning = self._normalize_claim_object(remainder)
                    concept_confidence = 0.64
                    verification_needed = True
                    anchor_mode = 'inherited'

        if not term or not meaning or self._is_weak_anchor_label(term):
            return {}

        concept = {
            'term': term,
            'meaning': meaning.strip(),
            'contrast': contrast.strip(),
            'source': source,
            'turn': self.turn_count,
            'text': raw[:280],
            'summary': f"{term} means {meaning.strip()}",
            'confidence': concept_confidence,
            'verification_needed': verification_needed,
            'anchor_mode': anchor_mode,
        }
        self.concept_meanings[term] = dict(concept)
        self.pending_concept_clarification = dict(concept)
        self._register_semantic_frame(self._semantic_frame_from_concept(concept))
        self.last_concept_anchor = term
        if term not in self.stated_facts:
            self.stated_facts[term] = {}
        self.stated_facts[term]['meaning'] = meaning.strip()
        self._register_mention(term, 'concept', source, 0.94)
        for idx, word in enumerate(re.findall(r"[a-z]{3,}", meaning.lower())[:4]):
            if not self._is_weak_anchor_label(word):
                self._register_mention(word, 'meaning', source, max(0.44, 0.78 - idx * 0.08))
        return concept

    def _native_turn_payload(self, user_text: str, understood: dict | None = None) -> Dict[str, Any]:
        understood = dict(understood or {})
        noncomp_input = dict(understood.get("noncomp_input") or {})
        noncomp_state = dict(
            understood.get("noncomp_state")
            or noncomp_input.get("noncomp_state")
            or {}
        )
        noncomp_manifold = dict(
            noncomp_state.get("manifold")
            or understood.get("noncomp_manifold")
            or {}
        )
        native_terms: List[str] = []
        for candidate in (
            understood.get("intent", ""),
            understood.get("query_type", ""),
            understood.get("constraint", ""),
            understood.get("dimension", ""),
            understood.get("topic", ""),
            noncomp_input.get("anchor", ""),
        ):
            label = str(candidate or "").strip()
            if label and label.lower() not in {item.lower() for item in native_terms}:
                native_terms.append(label)
        native_topic_words = [
            str(word).strip()
            for word in list(understood.get("topic_words", []) or [])
            if str(word).strip()
        ]
        native_entities = [
            str(entity).strip()
            for entity in list(understood.get("entities", []) or [])
            if str(entity).strip()
        ]
        native_text = " ".join(
            part for part in (
                " ".join(native_terms),
                " ".join(native_topic_words[:6]),
                " ".join(native_entities[:4]),
            )
            if part
        ).strip()
        if not native_text:
            native_text = str(user_text or "").strip()
        return {
            "understood": understood,
            "noncomp_input": noncomp_input,
            "noncomp_state": noncomp_state,
            "noncomp_manifold": noncomp_manifold,
            "native_terms": native_terms,
            "native_topic_words": native_topic_words,
            "native_entities": native_entities,
            "native_text": native_text,
            "native_low": native_text.lower(),
            "has_native_projection": bool(noncomp_state or noncomp_input.get("noncomp_state") or noncomp_manifold),
        }

    def resolve_concept_meaning(
        self,
        user_text: str,
        understood: dict | None = None,
    ) -> Dict[str, Any]:
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}

        result = {
            'term': '',
            'meaning': '',
            'contrast': '',
            'summary': '',
            'confidence': 0.0,
            'source': '',
            'verification_needed': False,
            'meaning_profile': {},
            'meaning_signature': '',
            'meaning_axes': (),
            'meaning_stage': '',
            'meaning_representation': '',
        }
        if not self.concept_meanings:
            return result

        native = self._native_turn_payload(user_text, understood)
        text_low = str(native.get("native_low", "") or "")
        callback_like = (
            native["understood"].get('is_callback') or
            native["understood"].get('is_clarification') or
            any(marker in text_low for marker in self._REFERENT_CALLBACK_MARKERS)
        )

        explicit_term = ""
        explicit_match = re.search(
            r'\bmean\s+by\s+([a-z][a-z0-9_\-\s]{1,40})\b',
            text_low,
        )
        if explicit_match:
            explicit_term = self._normalize_mention(explicit_match.group(1))

        candidates: List[Tuple[float, Dict[str, Any]]] = []
        seen_terms = set()

        # If the anchor was already the primary subject of Aurora's last response,
        # move it to the back of the queue.  This breaks the two-state oscillator
        # where alternating draft variants keep expressing the same concept every
        # turn.  An explicit user request (explicit_term) always overrides this.
        _last_resp_lo = str(getattr(self, 'last_aurora_response', '') or '').lower()
        _anchor_stale = bool(
            self.last_concept_anchor and
            _last_resp_lo and
            self.last_concept_anchor.lower() in _last_resp_lo and
            self.last_concept_anchor != explicit_term
        )

        ordered_terms = []
        if explicit_term:
            ordered_terms.append(explicit_term)
        ordered_terms.extend(
            [
                self._normalize_mention(native["understood"].get('topic', '')),
                None if _anchor_stale else self.last_concept_anchor,
                self.current_topic,
            ]
        )
        ordered_terms.extend(
            self._normalize_mention(term)
            for term in native.get('native_topic_words', []) + native.get('native_entities', [])
        )
        # Stale anchor appended at lowest priority rather than dropped entirely
        if _anchor_stale and self.last_concept_anchor:
            ordered_terms.append(self.last_concept_anchor)

        for idx, term in enumerate(ordered_terms):
            if not term or term in seen_terms or term not in self.concept_meanings:
                continue
            seen_terms.add(term)
            score = max(0.0, 1.1 - idx * 0.08)
            if term == explicit_term:
                score += 0.55
            if callback_like and term == self.last_concept_anchor and not _anchor_stale:
                score += 0.32
            if term == self.current_topic:
                score += 0.18
            candidates.append((score, dict(self.concept_meanings[term])))

        if not candidates:
            return result

        candidates.sort(key=lambda item: item[0], reverse=True)
        score, concept = candidates[0]
        retrieval_score = min(float(score or 0.0), 1.0)
        concept_confidence = float(concept.get('confidence', 0.9) or 0.9)
        result['term'] = str(concept.get('term', '') or '')
        result['meaning'] = str(concept.get('meaning', '') or '')
        result['contrast'] = str(concept.get('contrast', '') or '')
        result['summary'] = str(concept.get('summary', '') or '')
        result['confidence'] = max(0.0, min(1.0, retrieval_score * concept_confidence))
        result['source'] = str(concept.get('source', '') or '')
        result['verification_needed'] = bool(concept.get('verification_needed', False))
        profile = dict(concept.get('meaning_profile', {}) or {})
        result['meaning_profile'] = profile
        result['meaning_signature'] = str(concept.get('meaning_signature', '') or profile.get('signature', '') or '')
        axes = tuple(concept.get('meaning_axes', ()) or profile.get('axes', ()))
        result['meaning_axes'] = axes
        result['meaning_stage'] = str(concept.get('meaning_stage', '') or profile.get('stage', '') or '')
        result['meaning_representation'] = str(concept.get('meaning_representation', '') or profile.get('representation', '') or '')
        return result
    def _render_from_comprehension_intent(
        self,
        systems: Optional[Dict[str, Any]],
        core_claim: str,
        *,
        intent_type: str = 'statement',
        emotion_tone: str = 'neutral',
        relationship_signal: str = 'neutral',
        certainty: float = 0.7,
        supporting_concepts: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
    ) -> str:
        """
        Turn a comprehension result into speech through Aurora's existing language
        compiler instead of hand-authoring a user-facing sentence in aurora.py.
        """
        clean = str(core_claim or '').strip().strip('.')
        if not clean:
            return ""
        # Surface boundary guard — reject any string that carries raw mechanism data.
        # Internal labels, mutation tracking strings, and system state keys must never
        # cross into the language template layer.  Only compressed semantic content
        # (the result of waveform traversal) is permitted past this point.
        _MECH_LEAK_PATTERNS = (
            "earlier user utterance",
            "mutation_id=", "mutation_id =",
            "code evolution outcome",
            "accepted=false", "accepted=true", "accepted=0", "accepted=1",
            "operator_key=", "change_count=", "avg_fitness=",
            "genealogy_pressure=", "apply_duration=", "temporal_overhead=",
            "researcher lookup failed",
            "http error",
        )
        _clean_low = clean.lower()
        if any(pat in _clean_low for pat in _MECH_LEAK_PATTERNS):
            return ""

        perception = systems.get('perception') if isinstance(systems, dict) else None
        expression_candidate = ""
        try:
            if perception is not None and hasattr(perception, 'express') and hasattr(perception, 'composer'):
                context_terms = [
                    str(item).strip()
                    for item in list(supporting_concepts or [])
                    if str(item).strip()
                ]
                context_terms.extend(
                    word for word in re.findall(r"[a-z]{4,}", clean.lower())
                    if word not in {
                        'that', 'this', 'with', 'from', 'have', 'your', 'about',
                        'there', 'which', 'would', 'could', 'should',
                    }
                )
                if context_terms and hasattr(perception.composer, 'set_context'):
                    perception.composer.set_context(context_terms[:12])

                from aurora_consciousness_engine import AssemblyResult

                mock_assembly = AssemblyResult(
                    synthesis=SimpleNamespace(active_count=10),
                    frame_applied='comprehension_intent',
                    adjusted_axes=dict(getattr(perception, '_axis_activation', {}) or {}),
                    coherence=max(0.42, min(0.95, float(certainty or 0.7))),
                    entropy_state={},
                    ds_stats={},
                    dominant_axis=str(getattr(perception, '_dominant_axis', '') or ''),
                )
                expr_result = perception.express(
                    mock_assembly,
                    i_state='i_is',
                    mode='sim',
                    moral_alignment=max(0.45, min(0.95, float(certainty or 0.7))),
                    intent_match=max(0.5, min(0.98, float(certainty or 0.7))),
                ) or {}
                expression_candidate = str(expr_result.get('expression', '') or '').strip()
        except Exception:
            expression_candidate = ""

        if expression_candidate and not self._candidate_preserves_claim(
            expression_candidate,
            clean,
            supporting_concepts=supporting_concepts,
        ):
            expression_candidate = ""

        evo = getattr(perception, 'evo', None) if perception is not None else None
        if evo is None or not hasattr(evo, 'sic') or not hasattr(evo, 'multi_draft'):
            return expression_candidate or clean

        try:
            from aurora_internal.aurora_language_state import IntentObject

            native_meaning = {}
            native_bundle = {}
            if isinstance(systems, dict):
                native_bundle = systems.get("_native_meaning_bundle")
                if native_bundle:
                    native_meaning = _merge_native_meaning_bundle(native_bundle)
                else:
                    native_meaning = dict(systems.get("_native_meaning") or {})
                if not native_meaning:
                    native_meaning_obj = systems.get("_native_meaning_obj")
                    if hasattr(native_meaning_obj, "to_dict"):
                        try:
                            native_meaning = dict(native_meaning_obj.to_dict() or {})
                        except Exception:
                            native_meaning = {}
                if not native_meaning:
                    native_meaning = dict(systems.get("native_meaning") or {})
                if not native_meaning:
                    sensory_native = systems.get("_sensory_native_meaning")
                    if isinstance(sensory_native, dict):
                        native_meaning = _merge_native_meaning_bundle({"primary": sensory_native}) or dict(sensory_native)
            native_driven = bool(native_meaning or native_bundle)

            intent = IntentObject(
                intent_type=str(intent_type or 'statement'),
                core_claim=clean,
                emotion_tone=str(emotion_tone or 'neutral'),
                relationship_signal=str(relationship_signal or 'neutral'),
                certainty=max(0.0, min(1.0, float(certainty or 0.7))),
                supporting_concepts=[
                    str(item).strip()
                    for item in list(supporting_concepts or [])
                    if str(item).strip()
                ][:8],
                constraints=[
                    str(item).strip()
                    for item in list(constraints or [])
                    if str(item).strip()
                ],
                native_meaning=dict(native_meaning),
                native_meaning_bundle=dict(native_bundle or {}),
                law_bindings=list(native_meaning.get("law_bindings", []) or []),
                diagonal_anchor=str(native_meaning.get("diagonal_anchor", "") or ""),
            )

            candidates = list(evo.sic.compile_to_speech(intent, evo.anchors) or [])
            if expression_candidate and not native_driven and expression_candidate not in candidates:
                candidates.insert(0, expression_candidate)
            elif expression_candidate and native_driven and not candidates:
                candidates = [expression_candidate]
            draft = None
            if candidates:
                while len(candidates) < 3:
                    candidates.append(candidates[-1])

                ivm_heat = 0.3
                lattice = systems.get('lattice') if isinstance(systems, dict) else None
                if lattice is not None and hasattr(lattice, 'get_global_heat'):
                    try:
                        ivm_heat = float(lattice.get_global_heat() or 0.3)
                    except Exception:
                        ivm_heat = 0.3

                # Feed crossing path geometry back into the identity field as substrate signal.
                # The field integrates this alongside all other active signals; its evolved
                # N-axis state then surfaces as autonomy_mode — no categorical branching on
                # path labels.
                _lf_rci = systems.get("language_field") if isinstance(systems, dict) else None
                _proto_rci = getattr(_lf_rci, "_last_proto", None) if _lf_rci else None
                _ifield_rci = systems.get("identity_field") if isinstance(systems, dict) else None

                if _lf_rci is not None and _proto_rci is not None and hasattr(_lf_rci, "select_crossing_path"):
                    try:
                        # Silence gate: language field decides whether to cross the B-boundary.
                        # Silence is a positive field decision — n_topology IS the message.
                        _silence_res: dict = {}
                        if hasattr(_lf_rci, "silence_check"):
                            try:
                                _silence_res = _lf_rci.silence_check(_proto_rci) or {}
                            except Exception:
                                pass
                        if _silence_res.get("silence"):
                            # Field chose silence: inject n_topology as field state, not output
                            _n_topo = _silence_res.get("n_topology") or {}
                            if _n_topo and _ifield_rci is not None and hasattr(_ifield_rci, "ingest_external_input"):
                                _ifield_rci.ingest_external_input(_n_topo, intensity=0.28, source="silence_field_state")
                        else:
                            _xing = _lf_rci.select_crossing_path(_proto_rci) or {}
                            if _xing and _ifield_rci is not None and hasattr(_ifield_rci, "ingest_external_input"):
                                _nc = float(_xing.get("n_cost", 0.5))
                                _bm = float(_xing.get("b_match", 0.5))
                                if _xing.get("is_novel"):
                                    # High N-cost → field is in uncharted territory; A-axis active (pioneering)
                                    _xpulse = {"N": 0.50 + _nc * 0.40, "A": 0.45 + _nc * 0.25, "X": 0.35, "T": 0.30, "B": 0.30}
                                    _ifield_rci.ingest_external_input(_xpulse, intensity=0.35, source="crossing_novel")
                                elif _xing.get("is_metaphor"):
                                    # Approximating via proxy: N-pressure + B-boundary tension from poor match
                                    _xpulse = {"N": 0.45 + _nc * 0.25, "B": 0.50 + (1.0 - _bm) * 0.25, "X": 0.35, "T": 0.35, "A": 0.38}
                                    _ifield_rci.ingest_external_input(_xpulse, intensity=0.30, source="crossing_metaphor")
                                else:
                                    # Worn path: field settling into familiar, grounded territory
                                    _xpulse = {"X": 0.45 + _bm * 0.20, "T": 0.50 + _bm * 0.20, "N": 0.28, "B": 0.38, "A": 0.35}
                                    _ifield_rci.ingest_external_input(_xpulse, intensity=0.25, source="crossing_worn")
                    except Exception:
                        pass

                # autonomy_mode reads the field's live N-axis after all signals have settled
                _autonomy_mode = "GUIDED"
                if _ifield_rci is not None and hasattr(_ifield_rci, "status"):
                    try:
                        _fld_axes = (_ifield_rci.status().get("axis_pressures") or {})
                        _fld_n = float(_fld_axes.get("N", 0.3))
                        if _fld_n >= 0.62:
                            _autonomy_mode = "EXPLORER"
                        elif _fld_n >= 0.48:
                            _autonomy_mode = "EXPANSIVE"
                    except Exception:
                        pass

                draft = evo.multi_draft.generate(
                    intent,
                    candidates,
                    ivm_heat=ivm_heat,
                    autonomy_mode=_autonomy_mode,
                    user_verbosity=0.5,
                )

                last_text = str(getattr(self, 'last_aurora_response', '') or '').strip().lower()
                if last_text and draft.selected_text().strip().lower() == last_text:
                    for idx, text in enumerate((draft.raw, draft.structured, draft.social)):
                        if str(text or '').strip() and str(text).strip().lower() != last_text:
                            draft.selected = idx
                            draft.reason = 'avoid_exact_repeat'
                            break

                # Concept-level repeat guard: if every non-empty draft variant
                # discusses the same concept anchor as the last response, none
                # of them is genuinely novel.  Clear the draft so the pipeline
                # falls back to _data_to_minimal_speech rather than oscillating
                # between surface forms of the same repeated concept.
                _anc_lo = str(getattr(self, 'last_concept_anchor', '') or '').lower()
                if _anc_lo and last_text and _anc_lo in last_text:
                    _all_v = [str(t or '').strip().lower()
                              for t in (draft.raw, draft.structured, draft.social)
                              if str(t or '').strip()]
                    if _all_v and all(_anc_lo in v for v in _all_v):
                        draft.raw = ''
                        draft.structured = ''
                        draft.social = ''
                        draft.reason = 'concept_repeat_suppressed'

                evo._last_draft = draft
                final_text = str(draft.selected_text() or '').strip()

                if evo.grammar is not None and final_text:
                    try:
                        suggestion = evo.grammar.suggest_structure(final_text, context_text=clean, tone=getattr(state, "response_tone", "neutral"), passion=getattr(state, "emotional_state", {}).get("passion", "observant"), drive=getattr(state, "emotional_state", {}).get("drive", "steady"))
                        if suggestion:
                            final_text = str(suggestion.get('applied_text', '') or final_text).strip()
                    except Exception:
                        pass
            else:
                final_text = expression_candidate or clean

            # Coherence guard: if the SIC output is semantically disconnected from
            # the core_claim, fall back to a synthesized assembly. 
            # NO REVERSION TO RAW FRAGMENTS.
            if final_text:
                if native_driven:
                    if not self._candidate_preserves_bundle(final_text, native_meaning):
                        final_text = self._bundle_fallback_speech(
                            native_meaning,
                            clean,
                            emotion_tone,
                            relationship_signal,
                            systems=systems,
                        )
                elif not self._candidate_preserves_claim(
                    final_text,
                    clean,
                    supporting_concepts=supporting_concepts,
                ):
                    # Fallback to synthesized assembly even for non-native claims
                    final_text = self._bundle_fallback_speech(
                        native_meaning,
                        clean,
                        emotion_tone,
                        relationship_signal,
                        systems=systems,
                    )

            reflection = None
            try:
                reflection = evo.reflect_output(
                    intent=intent,
                    final_text=final_text,
                    assembly_data={
                        "native_meaning": dict(native_meaning),
                        "axis_activation": dict(getattr(perception, "_axis_activation", {}) or {}),
                        "dominant_axis": str(getattr(perception, "_dominant_axis", "") or ""),
                        "dominant_emotion": str(
                            getattr(perception, "_dominant_emotion", "")
                            or getattr(perception, "_dominant_emotional_state", "")
                            or "neutral"
                        ),
                        "axis_depth": {"X": 0, "T": 1, "N": 2, "B": 3, "A": 4}.get(
                            str(getattr(perception, "_dominant_axis", "") or ""),
                            2,
                        ),
                    },
                    draft=draft,
                )
            except Exception:
                reflection = None

            if isinstance(systems, dict):
                systems['_rendered_from_comprehension_intent'] = True
                if reflection is not None:
                    refl_dict = reflection.to_dict()
                    systems['_native_reflection'] = refl_dict
                    try:
                        systems['_native_reflection_history'] = evo.get_last_reflections(5)
                    except Exception:
                        systems['_native_reflection_history'] = [refl_dict]
                    # Build and store RenderRecord so the turn pipeline has a
                    # complete render→meaning→stance→drift record.
                    try:
                        from aurora_internal.aurora_language_state import RenderRecord as _RenderRecord
                        import hashlib as _hl
                        _stance_id = ""
                        if draft is not None:
                            _stance_id = f"draft_{draft.selected}"
                        _lost = refl_dict.get("lost_elements", [])
                        _total_bindings = max(1, len(list(native_meaning.get("law_bindings", []) or [])))
                        _drift = round(len(_lost) / _total_bindings, 3)
                        _render_rec = _RenderRecord(
                            render_id=_hl.md5(f"{final_text}{time.time()}".encode()).hexdigest()[:12],
                            meaning_id=refl_dict.get("meaning_id", ""),
                            stance_id=_stance_id,
                            final_text=final_text,
                            tone_estimate=refl_dict.get("tone_estimate", "neutral"),
                            drift_score=_drift,
                            human_readability_score=round(max(0.0, 1.0 - _drift * 0.5), 3),
                            feedback_status="applied" if refl_dict.get("future_bias_notes") else "pending",
                        )
                        systems['_render_record'] = _render_rec.to_dict()
                    except Exception:
                        pass
            return final_text or self._data_to_minimal_speech(clean, emotion_tone, relationship_signal)
        except Exception:
            return self._data_to_minimal_speech(clean, emotion_tone, relationship_signal)

    @staticmethod
    def _candidate_content_words(text: str) -> Set[str]:
        stopwords = {
            'the', 'and', 'that', 'this', 'with', 'for', 'from', 'are',
            'was', 'can', 'may', 'its', 'also', 'such', 'some', 'any',
            'all', 'not', 'have', 'has', 'but', 'you', 'your', 'into',
            'onto', 'than', 'then', 'they', 'them', 'their', 'there',
            'what', 'when', 'where', 'which', 'would', 'could', 'should',
            'about', 'here', 'just', 'really', 'still', 'like', 'because',
            'while', 'being', 'been', 'over', 'under', 'only', 'very',
            'much', 'more', 'most', 'after', 'before', 'does', 'doing',
            'did', 'through', 'across', 'between', 'people', 'person',
        }
        return {
            word
            for word in re.findall(r"[a-z]{3,}", str(text or "").lower())
            if word not in stopwords
        }

    def _candidate_preserves_claim(
        self,
        candidate_text: str,
        core_claim: str,
        *,
        supporting_concepts: Optional[List[str]] = None,
    ) -> bool:
        candidate = str(candidate_text or "").strip()
        clean = str(core_claim or "").strip()
        if not candidate:
            return False
        if candidate.lower() == clean.lower():
            return True

        claim_terms = self._candidate_content_words(clean)
        support_terms: Set[str] = set()
        for item in list(supporting_concepts or []):
            support_terms.update(self._candidate_content_words(str(item or "")))
        anchor_terms = claim_terms | support_terms
        if not anchor_terms:
            return True

        candidate_terms = self._candidate_content_words(candidate)
        if not candidate_terms:
            return False

        claim_overlap = len(candidate_terms & claim_terms)
        anchor_overlap = len(candidate_terms & anchor_terms)
        new_terms = candidate_terms - anchor_terms
        hybrid_terms = {
            token
            for token in re.findall(r"\b[a-z]+(?:-[a-z]+)+\b", candidate.lower())
            if token not in anchor_terms
        }
        candidate_starts_first_person = candidate.lower().startswith("i ")
        clean_has_first_person = bool(re.search(r"\b(i|me|my|mine)\b", clean.lower()))

        if claim_terms and claim_overlap == 0:
            return False
        if len(claim_terms) >= 3 and claim_overlap < 2:
            return False
        if support_terms and anchor_overlap == 0:
            return False
        if candidate_starts_first_person and not clean_has_first_person and anchor_overlap < 2:
            return False
        if hybrid_terms and anchor_overlap < 2 and len(hybrid_terms) >= 2:
            return False
        if len(candidate_terms) >= 4 and anchor_overlap / max(1, len(candidate_terms)) < 0.25 and len(new_terms) >= 3:
            return False
        return True

    def _candidate_preserves_bundle(
        self,
        candidate_text: str,
        native_meaning: Dict[str, Any],
    ) -> bool:
        candidate = str(candidate_text or "").strip().lower()
        if not candidate:
            return False
        bundle = _merge_native_meaning_bundle(native_meaning or {})
        roots = [
            str(item).strip().lower()
            for item in list(bundle.get("semantic_roots", []) or [])
            if str(item).strip()
        ]
        bindings = list(bundle.get("law_bindings", []) or [])
        if not roots and not bindings:
            return True

        candidate_terms = self._candidate_content_words(candidate)
        if not candidate_terms:
            return False

        root_terms = set()
        for root in roots:
            root_terms.update(self._candidate_content_words(root))
        if root_terms and candidate_terms & root_terms:
            return True

        for binding in bindings[:8]:
            if not isinstance(binding, dict):
                continue
            nc_name = str(binding.get("nc_name", "") or "").strip().lower()
            summary = str(binding.get("summary", "") or "").strip().lower()
            family = str(binding.get("family", "") or "").strip().lower()
            dimension = str(binding.get("dimension", "") or "").strip().lower()
            tokens = set(self._candidate_content_words(nc_name)) | set(self._candidate_content_words(summary))
            if tokens and candidate_terms & tokens:
                return True
            if family and family in candidate:
                return True
            if dimension and dimension in candidate:
                return True
        return False

    def _bundle_fallback_speech(
        self,
        native_meaning: Dict[str, Any],
        core_claim: str,
        emotion_tone: str,
        relationship_signal: str,
    ) -> str:
        bundle = _merge_native_meaning_bundle(native_meaning or {})
        roots = [
            str(item).strip().lower()
            for item in list(bundle.get("semantic_roots", []) or [])
            if str(item).strip()
        ]
        bindings = list(bundle.get("law_bindings", []) or [])
        dominant_family = ""
        dominant_dimension = ""
        if bindings:
            dominant = max(bindings, key=lambda item: float(item.get("score", 0.0) or 0.0))
            dominant_family = str(dominant.get("family", "") or "").lower()
            dominant_dimension = str(dominant.get("dimension", "") or "").lower()

        if roots:
            if any(root in roots for root in ("understanding", "meaning")):
                focus = "the meaning here"
            elif any(root in roots for root in ("purpose",)):
                focus = "the purpose here"
            elif any(root in roots for root in ("scene", "visual", "audio", "presence")):
                focus = "what is present here"
            elif any(root in roots for root in ("boundary",)):
                focus = "the boundary here"
            elif any(root in roots for root in ("information",)):
                focus = "what is actually here"
            else:
                focus = " ".join(list(dict.fromkeys(root.replace("_", " ") for root in roots[:2])))
        else:
            focus = str(core_claim or "").strip()

        lead = ""
        if dominant_family == "agentive":
            lead = f"understand; {focus}"
        elif dominant_family == "boundary":
            lead = f"boundary; {focus}; clear"
        elif dominant_family == "temporal":
            lead = f"follow; {focus}"
        elif dominant_family == "energetic":
            lead = f"measured; {focus}"
        elif dominant_family == "existential":
            lead = f"ground; {focus}"
        elif dominant_dimension == "difference":
            lead = f"separate; {focus}"
        elif dominant_dimension == "polarity":
            lead = f"hold; {focus}; view"
        elif dominant_dimension == "cost":
            lead = f"cost; {focus}; low"
        elif dominant_dimension == "magnitude":
            lead = f"proportion; {focus}"
        else:
            lead = f"track; {focus}"

        if relationship_signal in ("trust", "care"):
            lead = f"{lead}; trust; with you"
        elif relationship_signal in ("inquiry", "question"):
            lead = f"{lead}; inquiry; checking"
        elif emotion_tone in ("careful", "uncertain"):
            lead = f"{lead}; uncertain; now"

        return lead

    @staticmethod
    def _data_to_minimal_speech(data: str, emotion_tone: str = '', relationship_signal: str = '') -> str:
        """
        Last-resort transform when SIC produces nothing.  NOT prescripted — this
        restructures the raw data tokens (e.g. "Sunni; calm") into a minimal
        spoken fragment by stripping semicolons and joining naturally.
        The words are entirely from the data; nothing is invented here.
        """
        if not data or not data.strip():
            return data or ""
        # Strip semicolons and collapse whitespace — keep the actual content words
        parts = [p.strip() for p in data.split(';') if p.strip()]
        if not parts:
            return data
        # Filter out internal-only tokens that shouldn't be spoken
        _internal = {'gap', 'lookup available', 'lookup', 'noted', 'stored'}
        spoken = [p for p in parts if p.lower() not in _internal]
        if not spoken:
            spoken = parts
        # Join with natural spacing — comma for lists, period for separate thoughts
        if len(spoken) == 1:
            return spoken[0]
        return ", ".join(spoken[:-1]) + ". " + spoken[-1] if len(spoken) > 2 else spoken[0] + ". " + spoken[1]

    def answer_from_meanings(
        self,
        user_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        resolved = self.resolve_concept_meaning(user_text, understood)
        term = str(resolved.get('term', '') or '').strip()
        meaning = str(resolved.get('meaning', '') or '').strip()
        stored_contrast = str(resolved.get('contrast', '') or '').strip()
        if not term or not meaning:
            return ""
        if self.should_suppress_surface_meta_answer(
            user_text,
            understood=understood,
            term=term,
        ):
            return ""

        text_low = str(user_text or '').lower()
        contrast = ""
        contrast_match = re.search(r'\b(?:not|instead of|only)\s+(.+)$', text_low)
        if contrast_match:
            contrast_text = re.split(
                r'[\?,]|(?:\bwhat\b|\bwhy\b|\bhow\b|\bthen\b|\bso\b)',
                contrast_match.group(1),
                maxsplit=1,
            )[0]
            contrast = self._normalize_claim_object(contrast_text)
        if not contrast and stored_contrast:
            contrast = stored_contrast

        concept_entry = {}
        if isinstance(systems, dict):
            working_memory = systems.get("working_memory")
            if working_memory is not None:
                try:
                    concept_entry = dict(getattr(working_memory, "concept_meanings", {}).get(term, {}) or {})
                except Exception:
                    concept_entry = {}
        representation_variants = [
            str(item).strip()
            for item in list(concept_entry.get("representation_variants", []) or [])
            if str(item).strip()
        ]

        core_claim = ""
        tone = "reflective"
        certainty = 0.76
        relationship_signal = "neutral"
        constraints: List[str] = []

        if any(phrase in text_low for phrase in (
            'what do you think i mean by',
            'what do i mean by',
            'what do you mean by',
        )):
            core_claim = f"{term} means {meaning} in this thread"
            tone = "reflective"
            certainty = 0.7

        elif re.search(rf'\bis that {re.escape(term)}\b', text_low):
            if any(cue in text_low for cue in (
                'lose the thread',
                'only ',
                'just ',
                'smooth',
                'polished',
                'word association',
            )):
                core_claim = (
                    f"surface smoothness alone is not {term} here because {term} means {meaning}"
                )
                tone = "firm"
                certainty = 0.84
            else:
                core_claim = f"{term} is {meaning} by the meaning active in this thread"
                tone = "precise"
                certainty = 0.82

        elif any(phrase in text_low for phrase in (
            'why that and not',
            'why that instead of',
            'why not',
        )):
            if contrast:
                core_claim = (
                    f"treating {term} as {meaning} keeps meaning anchored instead of collapsing into {contrast}"
                )
            else:
                core_claim = (
                    f"{term} as {meaning} keeps the chain anchored instead of thinning into surface pattern alone"
                )
            tone = "reflective"
            certainty = 0.8

        elif any(phrase in text_low for phrase in (
            'preserve across turns',
            'keep across turns',
            'what should i preserve',
            'what should be preserved',
            'what should stay connected',
            'what should stay anchored',
        )):
            core_claim = f"{term} should stay preserved as {meaning} across turns"
            tone = "firm"
            certainty = 0.84

        elif any(phrase in text_low for phrase in (
            'what happens to meaning',
            'what breaks',
            'what would break',
            'what falls apart',
        )):
            if contrast:
                core_claim = (
                    f"if {term} becomes only {contrast}, meaning loses its anchor and coherence fragments across turns"
                )
            else:
                core_claim = (
                    f"if {term} loses {meaning}, later reasoning loses the anchor that keeps meaning coherent across turns"
                )
            tone = "reflective"
            certainty = 0.82

        elif representation_variants and any(phrase in text_low for phrase in (
            'how else can you say',
            'other ways to say',
            'other ways to represent',
            'alternate phrasing',
            'paraphrase',
            'say that another way',
            'express that differently',
        )):
            core_claim = f"for {term}, I can also say {representation_variants[0]}"
            tone = "reflective"
            certainty = 0.74

        elif any(phrase in text_low for phrase in (
            'why does that matter',
            'why is that important',
            'why does this matter',
        )):
            core_claim = (
                f"{term} as {meaning} gives later turns a stable reference instead of loose word association"
            )
            tone = "reflective"
            certainty = 0.8

        if not core_claim:
            return ""
        return self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone=tone,
            relationship_signal=relationship_signal,
            certainty=certainty,
            supporting_concepts=[term, meaning, contrast],
            constraints=constraints,
        )

    def answer_from_semantic_frames(
        self,
        user_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        resolved = self.resolve_semantic_frame(user_text, understood)
        frame = dict(resolved.get('frame', {}) or {})
        if not frame:
            return ""

        text_low = str(user_text or '').lower()
        roles = dict(frame.get('roles', {}) or {})
        anchor = str(frame.get('anchor', '') or '').strip()
        summary = str(frame.get('summary', '') or '').strip()
        kind = str(frame.get('kind', '') or '')
        subject = str(roles.get('subject', '') or anchor).strip()
        reason = str(roles.get('reason', '') or '').strip()
        condition = str(roles.get('condition', '') or '').strip()
        consequence = str(roles.get('consequence', '') or '').strip()
        value = str(roles.get('value', '') or roles.get('predicate', '') or '').strip()

        core_claim = ""
        tone = 'reflective'
        certainty = max(0.7, float(resolved.get('confidence', 0.0) or 0.0))

        if any(phrase in text_low for phrase in (
            'what did you mean', 'what do you mean', 'what you meant',
            'mean by that', 'what was missing', 'when you said',
        )):
            core_claim = self._semantic_frame_summary_claim(frame)
            tone = 'reflective'

        elif 'why' in text_low:
            if kind == 'evaluation' and reason:
                core_claim = f"{subject} matters because {reason}"
            elif kind == 'evaluation':
                core_claim = f"{subject} matters because it keeps the active meaning from thinning into loose wording alone"
            elif kind == 'causal_principle' and condition and consequence:
                core_claim = f"{consequence} follows because {condition}"
            elif kind == 'preservation_principle' and value:
                core_claim = f"{subject} should stay {value} so later turns keep the same meaning"
            elif kind == 'coexistence_principle':
                core_claim = (
                    f"{subject} can coexist when {condition}"
                    if condition else
                    f"{subject} can both hold when they do not actually conflict"
                )
            elif summary:
                core_claim = summary

        elif any(phrase in text_low for phrase in (
            'what breaks', 'what would break', 'what falls apart', 'what fails',
            'what degrades', 'what fragments', 'what happens next', 'what happens then',
        )):
            if kind == 'causal_principle' and consequence:
                core_claim = consequence
            elif kind == 'preservation_principle' and value:
                core_claim = f"if {subject} stops staying {value}, meaning continuity starts to break"
            elif kind == 'evaluation' and reason:
                core_claim = f"if {subject} stops mattering here, {reason}"
            elif kind == 'coexistence_principle':
                core_claim = (
                    f"coexistence breaks when {condition} no longer holds"
                    if condition else
                    f"coexistence breaks when the active branches actually conflict"
                )

        elif any(phrase in text_low for phrase in (
            'what should stay connected', 'what should stay anchored',
            'what should be preserved', 'what should stay preserved', 'what should i preserve',
            'preserve across turns', 'keep across turns',
        )):
            if kind == 'preservation_principle' and value:
                core_claim = f"{subject} should stay {value}"
            elif kind == 'evaluation':
                core_claim = f"what should stay preserved is that {subject} matters"
            elif kind == 'causal_principle' and condition:
                core_claim = f"what should stay preserved is {condition}"

        elif (
            ('when' in text_low or 'can ' in text_low) and
            'both' in text_low and
            kind == 'coexistence_principle'
        ):
            core_claim = (
                f"two things can both be right when {condition}"
                if condition else
                f"two things can both be right when they do not actually conflict"
            )

        elif 'conflict' in text_low or 'contradict' in text_low:
            if kind == 'coexistence_principle':
                core_claim = (
                    f"two things can both hold when {condition}"
                    if condition else
                    f"two things can both hold when they do not actually conflict"
                )

        if not core_claim:
            return ""
        return self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone=tone,
            certainty=certainty,
            supporting_concepts=[anchor, summary, condition, consequence, reason, value],
            constraints=[kind or 'semantic_frame'],
        )

    def align_response_to_active_meaning(
        self,
        user_text: str,
        candidate_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        candidate = str(candidate_text or '').strip()
        if not candidate:
            return {'revised': False, 'text': candidate}
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}
        if self.detect_context_directive(user_text, understood).get('detected'):
            return {'revised': False, 'text': candidate}

        resolved = self.resolve_concept_meaning(user_text, understood)
        term = str(resolved.get('term', '') or '').strip()
        meaning = str(resolved.get('meaning', '') or '').strip()
        contrast = str(resolved.get('contrast', '') or '').strip()
        meaning_confidence = float(resolved.get('confidence', 0.0) or 0.0)
        verification_needed = bool(resolved.get('verification_needed', False))
        if not term or not meaning:
            return {'revised': False, 'text': candidate}

        candidate_low = candidate.lower()
        text_low = str(user_text or '').lower()
        callback_like = bool(
            understood.get('is_callback') or
            understood.get('is_clarification') or
            any(marker in text_low for marker in self._REFERENT_CALLBACK_MARKERS)
        )
        concept_terms = {
            term_part
            for term_part in re.findall(r"[a-z]{3,}", f"{term} {meaning}".lower())
            if term_part not in self._WEAK_ANCHOR_LABELS
        }
        candidate_terms = set(re.findall(r"[a-z]{3,}", candidate_low))
        overlap = len(candidate_terms & concept_terms)
        grounded_reasoning = bool(
            overlap > 0 and
            any(
                cue in candidate_low for cue in (
                    ' because ', ' but ', ' however ', ' if ', ' unless ',
                    ' although ', ' rather than ', ' instead of ',
                )
            )
        )
        explicit_disagreement = bool(
            overlap > 0 and any(
                cue in candidate_low for cue in (
                    "i disagree",
                    "i don't agree",
                    'not necessarily',
                    "that doesn't follow",
                    "that would not",
                )
            )
        )
        if (grounded_reasoning or explicit_disagreement):
            return {'revised': False, 'text': candidate}
        meaning_answer = str(self.answer_from_meanings(user_text, understood, systems=systems) or '').strip()
        if not meaning_answer or meaning_answer.lower() == candidate_low:
            return {'revised': False, 'text': candidate}

        reasons: List[str] = []
        generic_meta = (
            candidate_low.startswith('active point; ') or
            candidate_low.startswith('active topic; ') or
            candidate_low.startswith("hold; view; ") or
            candidate_low.startswith('stays tied; ')
        )
        if callback_like and overlap == 0 and (generic_meta or len(candidate_terms) <= 10):
            reasons.append('callback_drift_from_active_meaning')
        if contrast and contrast.lower() in candidate_low and term.lower() not in candidate_low:
            reasons.append('contrast_overtook_meaning_anchor')

        if not reasons:
            return {'revised': False, 'text': candidate}
        if verification_needed or meaning_confidence < 0.74:
            verification_text = self._render_from_comprehension_intent(
                systems,
                core_claim=(
                    f"before I change my own framing around {term}, I need to verify that you mean {meaning}"
                ),
                intent_type='statement',
                emotion_tone='careful',
                relationship_signal='neutral',
                certainty=0.72,
                supporting_concepts=[term, meaning, contrast],
                constraints=['verify_meaning_before_self_audit'],
            )
            return {
                'revised': True,
                'text': verification_text or candidate,
                'reason': 'meaning_verification_before_self_audit',
                'term': term,
                'meaning': meaning,
                'contrast': contrast,
                'verification_needed': True,
                'skip_exchange_record': True,
                'skip_cross_learning': True,
                'defer_save': True,
            }
        return {
            'revised': True,
            'text': meaning_answer,
            'reason': reasons[0],
            'term': term,
            'meaning': meaning,
            'contrast': contrast,
            'verification_needed': False,
        }

    def _looks_plural_subject(self, subject: str) -> bool:
        normalized = self._normalize_mention(subject)
        if not normalized:
            return False
        parts = normalized.split()
        head = parts[-1] if parts else normalized
        if head in {'they', 'them', 'we', 'these', 'those'}:
            return True
        if head.endswith('ss'):
            return False
        return head.endswith('s')

    def _claim_to_text(self, claim: Dict[str, Any]) -> str:
        subject = str(claim.get('subject', '')).strip()
        relation = str(claim.get('relation', '')).replace('_', ' ').strip()
        obj = str(claim.get('object', '')).strip()
        negated = bool(claim.get('negated', False))
        if not subject:
            return ""
        copula = 'are' if self._looks_plural_subject(subject) else 'is'
        if relation.startswith('located '):
            prep = relation.split(' ', 1)[1].strip()
            if obj:
                return f"{subject} {copula}{' not' if negated else ''} {prep} {obj}"
            return f"{subject} {copula}{' not' if negated else ''} {prep}".strip()
        if relation == 'is':
            if obj:
                return f"{subject} {copula}{' not' if negated else ''} {obj}"
            return f"{subject} {copula}{' not' if negated else ''}".strip()
        if relation == 'can be':
            if obj:
                return f"{subject} can{' not' if negated else ''} be {obj}"
            return f"{subject} can{' not' if negated else ''} be".strip()
        if negated:
            base_relation = relation
            if relation.endswith('ies') and len(relation) > 3:
                base_relation = relation[:-3] + 'y'
            elif relation.endswith('s') and len(relation) > 3:
                base_relation = relation[:-1]
            if obj:
                return f"{subject} does not {base_relation} {obj}"
            return f"{subject} does not {base_relation}".strip()
        if obj:
            return f"{subject} {relation} {obj}"
        return f"{subject} {relation}".strip()

    def _subjects_match(self, left_subject: str, right_subject: str) -> bool:
        left = self._normalize_mention(left_subject)
        right = self._normalize_mention(right_subject)
        if not left or not right:
            return False
        if left == right:
            return True
        left_parts = set(left.split())
        right_parts = set(right.split())
        if not left_parts or not right_parts:
            return False
        if left_parts <= right_parts or right_parts <= left_parts:
            return True
        left_head = left.split()[-1]
        right_head = right.split()[-1]
        return left_head == right_head

    def _objects_indicate_exclusive_predicates(self, left_obj: str, right_obj: str) -> bool:
        left = self._normalize_claim_object(left_obj)
        right = self._normalize_claim_object(right_obj)
        if not left or not right or left == right:
            return False
        left_parts = set(left.split())
        right_parts = set(right.split())
        if not left_parts or not right_parts:
            return False
        if left_parts <= right_parts or right_parts <= left_parts:
            return False
        if left in self._COLOR_WORDS and right in self._COLOR_WORDS:
            return True
        if left in self._EXCLUSIVE_PREDICATE_WORDS and right in self._EXCLUSIVE_PREDICATE_WORDS:
            return True
        return False

    def _claims_conflict(self, left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        if not left or not right:
            return False
        if not self._subjects_match(str(left.get('subject', '')), str(right.get('subject', ''))):
            return False
        left_relation = str(left.get('relation', ''))
        right_relation = str(right.get('relation', ''))
        both_locative = left_relation.startswith('located_') and right_relation.startswith('located_')
        if left_relation != right_relation and not both_locative:
            return False
        if bool(left.get('negated', False)) != bool(right.get('negated', False)):
            return True
        left_obj = str(left.get('object', '')).strip()
        right_obj = str(right.get('object', '')).strip()
        if not left_obj or not right_obj or left_obj == right_obj:
            return False
        left_words = set(left_obj.split())
        right_words = set(right_obj.split())
        if not left_words or not right_words:
            return False
        if left_words <= right_words or right_words <= left_words:
            return False
        if both_locative:
            return True
        if left_relation == 'is':
            return self._objects_indicate_exclusive_predicates(left_obj, right_obj)
        return False

    def _claim_signature(self, claim: Dict[str, Any]) -> Tuple[str, str, str, bool, str]:
        return (
            self._normalize_mention(claim.get('subject', '')),
            str(claim.get('relation', '') or ''),
            self._normalize_claim_object(claim.get('object', '')),
            bool(claim.get('negated', False)),
            str(claim.get('source', '') or ''),
        )

    def _claim_exists(self, target: Dict[str, Any]) -> bool:
        if not target:
            return False
        target_sig = self._claim_signature(target)
        for claim in self.recent_claims:
            if self._claim_signature(claim) == target_sig:
                return True
        return False

    def _active_conflict_pairs(self) -> List[Dict[str, Any]]:
        active: List[Dict[str, Any]] = []
        claims = list(self.recent_claims)[:12]
        seen = set()
        for idx, left in enumerate(claims):
            for right in claims[idx + 1:]:
                if not self._claims_conflict(left, right):
                    continue
                pair = tuple(sorted((self._claim_to_text(left), self._claim_to_text(right))))
                if pair in seen:
                    continue
                seen.add(pair)
                active.append({
                    'pair': pair,
                    'subject': left.get('subject', ''),
                    'relation': left.get('relation', ''),
                    'sources': sorted({str(left.get('source', '')), str(right.get('source', ''))}),
                })
        return active

    def _recenter_claim_resolution(self, preferred_claim: Optional[Dict[str, Any]] = None):
        focus_claim = {}
        if preferred_claim and self._claim_exists(preferred_claim):
            focus_claim = self._copy_claim(preferred_claim)
        elif self.last_response_anchor_claim and self._claim_exists(self.last_response_anchor_claim):
            focus_claim = self._copy_claim(self.last_response_anchor_claim)
        elif self.recent_claims:
            focus_claim = self._copy_claim(self.recent_claims[0])

        if focus_claim:
            self.last_response_anchor_claim = self._copy_claim(focus_claim)
            self.last_claim_resolution = {
                'claims': [self._copy_claim(focus_claim)],
                'focus_claim': self._copy_claim(focus_claim),
                'confidence': 0.86,
                'source': str(focus_claim.get('source', '') or ''),
            }
        else:
            self.last_response_anchor_claim = {}
            self.last_claim_resolution = {'claims': [], 'focus_claim': {}, 'confidence': 0.0, 'source': ''}

    def refresh_claim_conflicts(
        self,
        *,
        systems: Optional[Dict[str, Any]] = None,
        preferred_claim: Optional[Dict[str, Any]] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        self._ensure_runtime_deques()
        before_pairs = {
            tuple(item.get('pair', ()))
            for item in self.claim_conflicts
            if tuple(item.get('pair', ()))
        }
        active_pairs = self._active_conflict_pairs()
        active_pair_keys = {tuple(item.get('pair', ())) for item in active_pairs if tuple(item.get('pair', ()))}
        existing = {
            tuple(item.get('pair', ())): dict(item)
            for item in self.claim_conflicts
            if tuple(item.get('pair', ()))
        }
        refreshed = deque(maxlen=self.claim_conflicts.maxlen)
        for item in active_pairs:
            pair_key = tuple(item.get('pair', ()))
            row = dict(existing.get(pair_key, {}))
            row.update(item)
            row['turn'] = self.turn_count
            refreshed.append(row)
        self.claim_conflicts = refreshed

        removed_pairs = sorted(before_pairs - active_pair_keys)
        if removed_pairs:
            if not preferred_claim and self.recent_claims:
                preferred_claim = dict(self.recent_claims[0] or {})
            self._recenter_claim_resolution(preferred_claim=preferred_claim)
            self.last_conflict_relief = {
                'resolved_pairs': [list(pair)[:2] for pair in removed_pairs[:4]],
                'remaining_pairs': [list(pair)[:2] for pair in list(active_pair_keys)[:4]],
                'preferred_claim': self._claim_to_text(preferred_claim or self.last_response_anchor_claim or {}),
                'turn': self.turn_count,
                'reason': str(reason or 'resolved_claim_conflict'),
            }
            if isinstance(systems, dict):
                try:
                    _log_claim_resolution_relief(
                        systems.get('genealogy'),
                        resolved_pairs=removed_pairs,
                        remaining_pairs=list(active_pair_keys),
                        reason=reason or 'resolved_claim_conflict',
                    )
                except Exception:
                    pass
        elif self.claim_conflicts:
            self.last_conflict_relief = {}
        elif not self.claim_conflicts:
            self._recenter_claim_resolution(preferred_claim=preferred_claim)

        return {
            'removed_pairs': removed_pairs,
            'active_pairs': list(active_pair_keys),
            'active_count': len(active_pair_keys),
        }

    def _register_claim_conflict(self, left: Dict[str, Any], right: Dict[str, Any]):
        self._ensure_runtime_deques()
        if not left or not right:
            return
        pair = tuple(sorted((self._claim_to_text(left), self._claim_to_text(right))))
        for item in self.claim_conflicts:
            if tuple(item.get('pair', ())) == pair:
                item['turn'] = self.turn_count
                return
        if not isinstance(self.claim_conflicts, deque):

            self.claim_conflicts = deque(list(self.claim_conflicts or []), maxlen=40)

        self.claim_conflicts.appendleft({
            'pair': pair,
            'subject': left.get('subject', ''),
            'relation': left.get('relation', ''),
            'turn': self.turn_count,
            'sources': sorted({str(left.get('source', '')), str(right.get('source', ''))}),
        })

    def _extract_claims(self, text: str, source: str, understood: dict | None = None) -> List[Dict[str, Any]]:
        raw = str(text or "").strip()
        if not raw or raw.endswith('?'):
            return []
        if source == 'user':
            if self.extract_user_identity_assertion(raw):
                return []
            if self.extract_behavior_alignment_request(raw):
                return []

        line = raw.rstrip('.!')
        out: List[Dict[str, Any]] = []
        seen = set()

        def _append_claim(subject: str, relation: str, obj: str, negated: bool = False):
            subject_norm = self._normalize_mention(subject)
            obj_norm = self._normalize_claim_object(obj)
            if (
                not subject_norm or not obj_norm or
                subject_norm in self._CLAIM_SKIP_SUBJECTS or
                self._is_weak_anchor_label(subject_norm)
            ):
                return
            obj_norm = re.split(
                r'\b(?:because|but|so|while|although)\b',
                obj_norm,
                maxsplit=1,
            )[0].strip()
            if not obj_norm or obj_norm in self._VAGUE_REFERENTS:
                return
            claim = self._build_claim(
                subject_norm, relation, obj_norm, source, negated, raw, understood
            )
            key = (
                claim['subject'],
                claim['relation'],
                claim['object'],
                claim['negated'],
                claim['source'],
            )
            if key in seen:
                return
            seen.add(key)
            out.append(claim)

        reported_match = re.match(
            r'^(?:my\s+\w+|[A-Za-z][A-Za-z0-9_\-\s]{1,40}?)\s+'
            r'(says|said|thinks|thought|believes|believed|claims|claimed|insists|insisted)\s+(.+)$',
            line,
            re.IGNORECASE,
        )
        if reported_match:
            nested_clause = str(reported_match.group(2) or '').strip()
            if nested_clause and nested_clause.lower() != line.lower():
                nested_claims = self._extract_claims(nested_clause, source=source, understood=understood)
                for claim in nested_claims:
                    key = (
                        claim.get('subject'),
                        claim.get('relation'),
                        claim.get('object'),
                        claim.get('negated'),
                        claim.get('source'),
                    )
                    if key not in seen:
                        seen.add(key)
                        out.append(claim)
                if out:
                    return out[:3]

        locative_action_match = re.match(
            r'^(?:i|we|he|she|they|someone|my\s+\w+|[A-Za-z][A-Za-z0-9_\-\s]{1,30}?)\s+'
            r'(?:left|leave|put|placed|place|set|kept|keep|stored|store)\s+'
            r'(?:my|the|our|his|her|their|a|an)?\s*([A-Za-z][A-Za-z0-9_\-\s]{1,60}?)\s+'
            r'(in|inside|on|at|under|by|near)\s+(.+)$',
            line,
            re.IGNORECASE,
        )
        if locative_action_match:
            subject, prep, obj = locative_action_match.groups()
            relation = self._LOCATION_PREPOSITION_TO_RELATION.get(prep.lower(), 'located_at')
            _append_claim(subject, relation, obj, False)

        locative_copula_match = re.match(
            r'^(?:the\s+|a\s+|an\s+)?([A-Za-z][A-Za-z0-9_\-\s]{1,60}?)\s+'
            r'(?:is|are|was|were)\s+(not\s+)?(in|inside|on|at|under|by|near)\s+(.+)$',
            line,
            re.IGNORECASE,
        )
        if locative_copula_match:
            subject, neg_token, prep, obj = locative_copula_match.groups()
            relation = self._LOCATION_PREPOSITION_TO_RELATION.get(prep.lower(), 'located_at')
            _append_claim(subject, relation, obj, bool(neg_token))

        modal_copula_match = re.match(
            r'^([A-Za-z0-9][A-Za-z0-9_\-\s]{1,60}?)\s+'
            r'(can\s+both\s+be|can\s+be|cannot\s+be|can\'t\s+be)\s+(.+)$',
            line,
            re.IGNORECASE,
        )
        if modal_copula_match:
            subject, modal_relation, obj = modal_copula_match.groups()
            _append_claim(subject, 'can_be', obj, bool(re.match(r'^(?:cannot|can\'t)', modal_relation, re.IGNORECASE)))

        relation_patterns = [
            r'(connects?\s+to|links?\s+to|maps?\s+to|relates?\s+to|pertains?\s+to)',
            r'(blocks|block|prevents|prevent|breaks|break|causes|cause|creates|create|'
            r'requires|require|needs|need|anchors|anchor|grounds|ground|tracks|track|'
            r'carries|carry|wires|wire|drives|drive|improves|improve|degrades|degrade|'
            r'forms|form|means|mean)',
        ]
        patterns = [
            rf'^(?:the\s+|a\s+|an\s+)?([A-Za-z][A-Za-z0-9_\-\s]{{1,60}}?)\s+{relation_patterns[0]}\s+(.+)$',
            rf'^(?:the\s+|a\s+|an\s+)?([A-Za-z][A-Za-z0-9_\-\s]{{1,60}}?)\s+{relation_patterns[1]}\s+(.+)$',
            r'^(?:the\s+|a\s+|an\s+)?([A-Za-z][A-Za-z0-9_\-\s]{1,60}?)\s+(is|are|was|were)\s+(not\s+)?(.+)$',
        ]

        negated_aux_pattern = re.compile(
            rf'^(?:the\s+|a\s+|an\s+)?([A-Za-z][A-Za-z0-9_\-\s]{{1,60}}?)\s+'
            rf'(?:do|does|did)\s+not\s+{relation_patterns[1]}\s+(.+)$',
            re.IGNORECASE,
        )
        negated_aux_match = negated_aux_pattern.match(line)
        if negated_aux_match:
            subject, relation, obj = negated_aux_match.groups()
            _append_claim(subject, relation, obj, True)

        for pat in patterns:
            match = re.match(pat, line, re.IGNORECASE)
            if not match:
                continue
            groups = match.groups()
            if len(groups) == 3:
                subject, relation, obj = groups
                negated = False
            else:
                subject, relation, neg_token, obj = groups
                negated = bool(neg_token)
            if relation.lower() in {'is', 'are', 'was', 'were'} and re.match(
                r'^(?:in|inside|on|at|under|by|near)\b',
                str(obj or '').strip(),
                re.IGNORECASE,
            ):
                continue
            if re.search(r'\b(?:do|does|did)\s+not$', self._normalize_mention(subject)):
                continue
            _append_claim(subject, relation, obj, negated)
        return out[:3]

    def note_claims(self, text: str, source: str = 'user', understood: dict | None = None) -> List[Dict[str, Any]]:
        self._ensure_runtime_deques()
        raw_low = str(text or '').strip().lower()
        if source == 'aurora' and raw_low.startswith((
            'because if ',
            'because ',
            'it works by ',
            "i don't have ",
            'i do not have ',
            "follow; ",
            "track; that; ",
            "understand; that; ",
            "thread; hold; ",
            "ground; claim; ",
            'i hear you ',
            'fair ',
            'conflict; competing claims',
            'coexist; claims',
            'conflict; resolved',
        )):
            return []

        claims = self._extract_claims(text, source=source, understood=understood)
        if not claims:
            return []

        recent_snapshot = list(self.recent_claims)
        for claim in claims:
            duplicate = None
            for item in self.recent_claims:
                if (
                    item.get('subject') == claim['subject'] and
                    item.get('relation') == claim['relation'] and
                    item.get('object') == claim['object'] and
                    bool(item.get('negated', False)) == bool(claim.get('negated', False)) and
                    item.get('source') == claim['source']
                ):
                    duplicate = item
                    break
            if duplicate:
                duplicate['turn'] = self.turn_count
                duplicate['text'] = claim['text']
                duplicate['topic'] = claim['topic']
                if self.proposition_substrate is not None:
                    node = self.proposition_substrate.note_claim(duplicate, recent_claims=recent_snapshot)
                    duplicate['proposition_id'] = str(node.get('proposition_id', '') or '')
                    duplicate['branch_id'] = str(node.get('branch_id', '') or '')
                    duplicate['confidence'] = float(node.get('confidence', 0.0) or 0.0)
                    recent_snapshot = [duplicate] + recent_snapshot[:7]
                continue

            for existing in list(self.recent_claims)[:8]:
                if self._claims_conflict(claim, existing):
                    self._register_claim_conflict(claim, existing)
                    break

            if not isinstance(self.recent_claims, deque):


                self.recent_claims = deque(list(self.recent_claims or []), maxlen=40)


            self.recent_claims.appendleft(claim)
            if self.proposition_substrate is not None:
                node = self.proposition_substrate.note_claim(claim, recent_claims=recent_snapshot)
                claim['proposition_id'] = str(node.get('proposition_id', '') or '')
                claim['branch_id'] = str(node.get('branch_id', '') or '')
                claim['confidence'] = float(node.get('confidence', 0.0) or 0.0)
                recent_snapshot = [claim] + recent_snapshot[:7]
            self._register_semantic_frame(self._semantic_frame_from_claim(claim))
            self._register_mention(claim['subject'], 'fact', source, 0.82 if source == 'user' else 0.74)
            if claim.get('object') and not self._is_weak_anchor_label(claim['object']):
                self._register_mention(claim['object'], 'fact', source, 0.74 if source == 'user' else 0.66)

        if self.proposition_substrate is not None:
            try:
                self.proposition_substrate.note_claim_bundle(claims, raw_text=text)
            except Exception:
                pass
        self.refresh_claim_conflicts(preferred_claim=claims[0] if claims else None)
        return claims

    def has_claim_anchor(self) -> bool:
        return bool(self.recent_claims)

    def _claim_terms(self, claim: Dict[str, Any]) -> set:
        terms = set()
        for key in ('subject', 'object', 'topic'):
            for part in str(claim.get(key, '')).split():
                if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS:
                    terms.add(part)
        relation = str(claim.get('relation', '')).replace('_', ' ')
        for part in relation.split():
            if len(part) >= 3 and part not in self._WEAK_ANCHOR_LABELS:
                terms.add(part)
        return terms

    def resolve_claims(self, user_text: str, understood: dict | None = None) -> Dict[str, Any]:
        self.refresh_claim_conflicts()
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}

        result = {
            'claims': [],
            'focus_claim': {},
            'confidence': 0.0,
            'source': '',
        }
        if not self.recent_claims:
            self.last_claim_resolution = result
            return result

        native = self._native_turn_payload(user_text, understood)
        text_low = str(native.get("native_low", "") or "")
        topic = self._normalize_mention(native["understood"].get('topic', ''))
        topic_words = {
            self._normalize_mention(word)
            for word in native.get('native_topic_words', [])
            if len(str(word)) >= 3
        }
        entities = {
            self._normalize_mention(entity)
            for entity in native.get('native_entities', [])
            if len(str(entity)) >= 3
        }
        referent_topic = self._normalize_mention(self.last_referent_resolution.get('topic', ''))
        is_callback_request = (
            native["understood"].get('is_callback') or native["understood"].get('is_clarification') or
            any(marker in text_low for marker in self._REFERENT_CALLBACK_MARKERS)
        )
        prefer_source = 'aurora' if is_callback_request else 'user'
        locative_request = (
            'where' in text_low or
            'check first' in text_low or
            'look first' in text_low or
            'check next' in text_low
        )

        candidates: List[Dict[str, Any]] = []
        if is_callback_request and self.last_response_anchor_claim:
            anchor_claim = self._copy_claim(self.last_response_anchor_claim)
            if anchor_claim:
                anchor_claim['score'] = 2.4
                anchor_claim['source'] = str(anchor_claim.get('source', 'user') or 'user')
                candidates.append(anchor_claim)
        for idx, claim in enumerate(self.recent_claims):
            score = max(0.0, 1.05 - idx * 0.05)
            if claim.get('source') == prefer_source:
                score += 0.24
            elif claim.get('source') == 'user':
                score += 0.05
            if locative_request and str(claim.get('relation', '')).startswith('located_'):
                score += 0.48
                if claim.get('source') == 'user':
                    score += 0.12

            claim_terms = self._claim_terms(claim)
            overlap = len(claim_terms & topic_words)
            overlap += len(claim_terms & entities)
            if overlap:
                score += overlap * 0.18
            if topic and topic in claim_terms:
                score += 0.34
            if referent_topic and referent_topic in claim_terms:
                score += 0.30
            if is_callback_request and claim.get('source') == 'aurora':
                score += 0.25
            if self.proposition_substrate is not None:
                pscore = float(self.proposition_substrate.score_claim(claim) or 0.0)
                if pscore > 0.0:
                    score += 0.28 * pscore
                pmeta = self.proposition_substrate.node_for_claim(claim)
                if pmeta:
                    candidate_proposition = dict(pmeta)
                else:
                    candidate_proposition = {}
            else:
                candidate_proposition = {}

            candidate = dict(claim)
            candidate['score'] = round(score, 6)
            if candidate_proposition:
                candidate['proposition'] = candidate_proposition
            candidates.append(candidate)

        candidates.sort(key=lambda rec: rec.get('score', 0.0), reverse=True)
        result['claims'] = candidates[:3]
        if candidates:
            result['focus_claim'] = candidates[0]
            result['confidence'] = float(candidates[0].get('score', 0.0))
            result['source'] = str(candidates[0].get('source', ''))
        self.last_claim_resolution = result
        return result

    def _format_claim_conflict(self, conflict: Dict[str, Any]) -> str:
        pair = list(conflict.get('pair', ()))
        if len(pair) >= 2:
            return f"conflict; competing claims; {pair[0]}; {pair[1]}"
        return ""

    def answer_from_claims(
        self,
        user_text: str,
        understood: dict | None = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not user_text:
            return ""

        self.refresh_claim_conflicts(systems=systems, reason='claim_resolution_audit')
        t_low = str(user_text).lower()
        if any(phrase in t_low for phrase in (
            'uncertain about', 'not sure about', 'wrong about', 'was uncertain',
        )) and self.last_uncertainty_focus:
            return self._render_from_comprehension_intent(
                systems,
                core_claim=f"uncertainty; resolving; {self.last_uncertainty_focus}",
                emotion_tone='precise',
                certainty=0.78,
                supporting_concepts=[self.last_uncertainty_focus],
            )

        conflict_words = ('contradict', 'conflict', 'inconsistent', 'wrong')
        if any(word in t_low for word in conflict_words) and self.claim_conflicts:
            pair = list((self.claim_conflicts[0] or {}).get('pair', ()))
            if len(pair) >= 2:
                return self._render_from_comprehension_intent(
                    systems,
                    core_claim=f"weighing; {pair[0]}; {pair[1]}; no alignment",
                    emotion_tone='firm',
                    certainty=0.9,
                    supporting_concepts=pair[:2],
                    constraints=['conflict'],
                )
            return ""
        if any(word in t_low for word in conflict_words):
            recent_relief = dict(self.last_conflict_relief or {})
            relief_turn = int(recent_relief.get('turn', 0) or 0)
            if (
                recent_relief and
                not self.claim_conflicts and
                relief_turn > 0 and
                (self.turn_count - relief_turn) <= 3
            ):
                active_summary = str(
                    recent_relief.get('preferred_claim', '') or
                    self._claim_to_text(self.last_response_anchor_claim or {})
                ).strip()
                core_claim = (
                    f"that's resolved now — {active_summary}"
                    if active_summary else
                    "that tension resolved itself"
                )
                return self._render_from_comprehension_intent(
                    systems,
                    core_claim=core_claim,
                    emotion_tone='precise',
                    certainty=0.88,
                    supporting_concepts=[active_summary] if active_summary else [],
                    constraints=['conflict_relief'],
                )
            resolved = self.resolve_claims(user_text, understood)
            candidate_claims = list(resolved.get('claims', []) or [])[:2]
            if len(candidate_claims) >= 2:
                left = dict(candidate_claims[0] or {})
                right = dict(candidate_claims[1] or {})
                if (
                    left and right and
                    self._subjects_match(left.get('subject', ''), right.get('subject', '')) and
                    not self._claims_conflict(left, right)
                ):
                    left_summary = self._claim_to_text(left)
                    right_summary = self._claim_to_text(right)
                    return self._render_from_comprehension_intent(
                        systems,
                        core_claim=f"both {left_summary} and {right_summary} can hold at the same time",
                        emotion_tone='precise',
                        certainty=0.82,
                        supporting_concepts=[left_summary, right_summary],
                        constraints=['coexistence'],
                    )

        callback_request = any(phrase in t_low for phrase in (
            'what did you mean', 'what do you mean', 'what you meant',
            'mean by that', 'what was missing', 'when you said',
        ))
        if callback_request and self.last_response_anchor_claim:
            claim = self._copy_claim(self.last_response_anchor_claim)
        else:
            claim = {}

        if ('where' in t_low or 'check first' in t_low or 'look first' in t_low) and not claim:
            locative_candidates = [
                dict(item)
                for item in self.recent_claims
                if str(item.get('relation', '')).startswith('located_')
            ]
            user_locative = [item for item in locative_candidates if item.get('source') == 'user']
            if user_locative:
                claim = user_locative[0]
            elif locative_candidates:
                claim = locative_candidates[0]

        resolved = self.resolve_claims(user_text, understood)
        if not claim:
            _fc = resolved.get('focus_claim', {}) or {}
            # Don't use user-source claims as Aurora's first-person memory.
            if str(_fc.get('source', '')) != 'user':
                claim = _fc
        if not claim and 'where' in t_low:
            for recent in self.recent_claims:
                if str(recent.get('relation', '')).startswith('located_'):
                    claim = dict(recent)
                    break
        if not claim:
            return ""

        summary = self._claim_to_text(claim)
        relation = str(claim.get('relation', ''))
        subject = str(claim.get('subject', ''))
        obj = str(claim.get('object', ''))
        proposition = {}
        if self.proposition_substrate is not None:
            proposition = self.proposition_substrate.node_for_claim(claim)
        edge_summary = dict(proposition.get('edge_summary', {}) or {})
        confidence = float(proposition.get('confidence', claim.get('confidence', 0.0)) or 0.0)
        source = str(proposition.get('source', claim.get('source', '')) or '')
        locative_relation = relation.startswith('located_')
        locative_prep = relation.split('_', 1)[1] if locative_relation and '_' in relation else ''
        copula = 'are' if self._looks_plural_subject(subject) else 'is'
        core_claim = ""
        tone = 'precise'
        certainty_hint = 0.8
        supporting = [subject, relation.replace('_', ' '), obj, summary]
        constraints: List[str] = []

        # Topic-relevance guard for the broad 'how'/'why' branches below.
        # Those branches match any question containing the word, so without this
        # guard they return the LAST stored claim regardless of topic -- causing
        # meaning_momentum lock across unrelated turns.
        # Only suppress when: claim subject/object shares NO words with the
        # current question AND the question is not a callback/clarification.
        _claim_content_words = set(
            re.findall(r'[a-z]{3,}', (subject + ' ' + obj + ' ' + summary).lower())
        ) - {'the', 'and', 'that', 'this', 'with', 'for', 'from', 'are', 'was',
             'can', 'may', 'its', 'also', 'such', 'some', 'any', 'all', 'about'}
        _query_content_words = set(
            re.findall(r'[a-z]{3,}', t_low)
        ) - {'how', 'why', 'what', 'does', 'that', 'this', 'then', 'there',
             'tell', 'now', 'here', 'work', 'works', 'working', 'you', 'your',
             'the', 'and', 'for', 'from', 'with', 'can', 'its', 'about'}
        _claim_topic_relevant = (
            bool(_claim_content_words & _query_content_words) or callback_request
        )

        if any(phrase in t_low for phrase in (
            'what did you mean', 'what do you mean', 'what you meant',
            'mean by that', 'what was missing', 'when you said',
        )):
            core_claim = f"the part I meant is {summary}"
            tone = 'reflective'
            certainty_hint = 0.84

        elif any(phrase in t_low for phrase in (
            'what object', 'what item', 'which object', 'which item',
        )) and subject:
            core_claim = f"{subject} is the object active in that thread"
            tone = 'precise'
            certainty_hint = 0.82

        elif 'remember' in t_low or 'what did i say' in t_low or 'what did you say' in t_low:
            # Only surface a stored claim if it's topically relevant to the query.
            # Without this guard, any recent aurora claim leaks out for any "remember" query.
            if _claim_topic_relevant:
                core_claim = summary
                tone = 'precise'
                certainty_hint = 0.86

        elif ('check first' in t_low or 'look first' in t_low) and locative_relation:
            core_claim = f"the first place to check is {locative_prep} {obj}"
            tone = 'firm'
            certainty_hint = 0.84

        elif 'where' in t_low and locative_relation:
            core_claim = f"{subject} {copula} {locative_prep} {obj}"
            tone = 'precise'
            certainty_hint = 0.84

        elif 'why' in t_low and _claim_topic_relevant:
            if proposition and int(edge_summary.get('causal', 0)) > 0:
                core_claim = (
                    f"{summary} already sits inside {int(edge_summary.get('causal', 0))} causal paths"
                )
            elif relation in {'requires'}:
                core_claim = f"{subject} requires {obj}, and without {obj} the chain stays disconnected"
            elif relation in {'blocks', 'breaks', 'degrades'}:
                core_claim = f"{subject} {relation.replace('_', ' ')} {obj}, so continuity breaks around {obj or subject}"
            elif relation in {'anchors', 'grounds', 'tracks', 'connects_to', 'relates_to', 'wires', 'carries'}:
                core_claim = f"{subject} {relation.replace('_', ' ')} {obj}, which gives later reasoning a stable path"
            elif locative_relation:
                core_claim = f"{subject} {copula} {locative_prep} {obj}, which gives you a concrete place to check first"
            elif relation == 'is':
                core_claim = f"{subject} is {obj}"
            else:
                core_claim = f"that comes down to {summary}"
            tone = 'reflective'
            certainty_hint = 0.82

        elif 'how' in t_low and _claim_topic_relevant:
            if proposition and int(edge_summary.get('revision', 0)) > 0:
                core_claim = (
                    f"{summary} stays revisable as a proposition instead of flattening into one static statement"
                )
            elif relation in {'connects_to', 'relates_to', 'anchors', 'grounds', 'tracks', 'wires', 'carries'}:
                core_claim = f"it works by linking {subject} to {obj} so the next step has a clear anchor"
            elif relation in {'requires'}:
                core_claim = f"it works by making {obj} a dependency for {subject}"
            elif relation in {'blocks', 'breaks', 'degrades'}:
                core_claim = f"it works by making {obj} the failure point for {subject}"
            elif locative_relation:
                core_claim = f"it works by anchoring {subject} to a concrete location at {locative_prep} {obj}"
            else:
                # Only use summary text if it's concise (not a prior turn's full response).
                # Long summaries > 5 words are almost certainly recycled Aurora responses.
                _summary_str = str(summary or '')
                _summary_words = len(_summary_str.split())
                _summary_low = _summary_str.lower()
                _social_starts = ('hey', 'hi ', 'hello', 'how are', 'how is',
                                  'what\'s up', "what is up", 'greet', 'good morning',
                                  'good afternoon', 'good evening')
                _mech_chars = any(c in _summary_str for c in ('=', '{', '}'))
                _is_social = any(_summary_low.startswith(s) for s in _social_starts)
                if (_summary_words <= 5 and not _mech_chars and not _is_social
                        and '?' not in _summary_str):
                    core_claim = f"it works through {summary}"
                # else: leave core_claim="" so the function returns "" instead of echoing
            tone = 'reflective'
            certainty_hint = 0.8

        elif any(phrase in t_low for phrase in (
            'stay connected', 'keep connected', 'stay anchored', 'keep anchored',
        )):
            core_claim = f"{summary} needs to stay connected through the next step"
            tone = 'firm'
            certainty_hint = 0.84

        elif any(word in t_low for word in ('what', 'which')) and (
            'missing' in t_low or 'that' in t_low or 'this' in t_low or 'claim' in t_low
        ):
            core_claim = summary
            tone = 'precise'
            certainty_hint = 0.8

        if not core_claim:
            return ""
        return self._render_from_comprehension_intent(
            systems,
            core_claim=core_claim,
            intent_type='statement',
            emotion_tone=tone,
            relationship_signal='neutral',
            certainty=certainty_hint,
            supporting_concepts=supporting,
            constraints=constraints,
        )

    def _register_understood_mentions(self, understood: dict, source: str):
        topic = self.resolve_topic(understood)
        if topic and not self._is_weak_anchor_label(topic):
            self._register_mention(topic, 'topic', source, 1.0 if source == 'user' else 0.92)

        for idx, entity in enumerate(understood.get('entities', [])[:3]):
            self._register_mention(entity, 'entity', source, max(0.55, 0.95 - idx * 0.10))

        for idx, word in enumerate(understood.get('topic_words', [])[:4]):
            if word == topic or word in self._VAGUE_REFERENTS:
                continue
            self._register_mention(word, 'keyword', source, max(0.35, 0.72 - idx * 0.08))

    def _register_response_mentions(self, aurora_text: str):
        if not aurora_text:
            return
        try:
            understood = UtteranceParser().parse(aurora_text)
        except Exception:
            understood = {
                'topic': '',
                'topic_words': re.findall(r'[a-z]{4,}', aurora_text.lower())[:4],
                'entities': re.findall(r'\b[A-Z][a-z]{1,}\b', aurora_text)[:2],
            }
        self._register_understood_mentions(understood, source='aurora')

    def _aurora_reply_anchor(self) -> Optional[str]:
        if not self.last_aurora_response:
            return None
        try:
            understood = UtteranceParser().parse(self.last_aurora_response)
        except Exception:
            understood = {
                'topic': '',
                'topic_words': re.findall(r'[a-z]{4,}', self.last_aurora_response.lower())[:5],
                'entities': re.findall(r'\b[A-Z][a-z]{1,}\b', self.last_aurora_response)[:3],
            }

        topic = self._normalize_mention(understood.get('topic', ''))
        if topic and not self._is_weak_anchor_label(topic):
            return topic

        entity_labels = [
            self._normalize_mention(entity)
            for entity in understood.get('entities', [])[:2]
        ]
        entity_labels = [
            label for label in entity_labels
            if label and not self._is_weak_anchor_label(label)
        ]
        if entity_labels:
            return entity_labels[0]

        topic_words: List[str] = []
        for word in understood.get('topic_words', [])[:5]:
            normalized = self._normalize_mention(word)
            if (not normalized or normalized in self._VAGUE_REFERENTS or
                    self._is_weak_anchor_label(normalized)):
                continue
            if normalized not in topic_words:
                topic_words.append(normalized)
            if len(topic_words) >= 3:
                break
        if topic_words:
            return " ".join(topic_words)
        return None

    def has_referent_anchor(self) -> bool:
        if self.current_topic:
            return True
        if self.recent_claims:
            return True
        return any(item.get('label') for item in self.recent_mentions)

    def _anchor_candidates(self, prefer_source: str = "") -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for idx, item in enumerate(self.recent_mentions):
            label = str(item.get('label', '')).strip()
            if not label or label in self._VAGUE_REFERENTS:
                continue

            score = float(item.get('salience', 0.0))
            score += max(0.0, 0.40 - idx * 0.03)

            kind = str(item.get('kind', 'keyword'))
            if kind == 'topic':
                score += 0.22
            elif kind == 'entity':
                score += 0.18
            elif kind == 'fact':
                score += 0.14

            if label == self.current_topic:
                score += 0.18
            if prefer_source and item.get('source') == prefer_source:
                score += 0.15
            elif item.get('source') == 'user':
                score += 0.05

            candidate = dict(item)
            candidate['score'] = round(score, 6)
            candidates.append(candidate)

        candidates.sort(key=lambda rec: rec.get('score', 0.0), reverse=True)
        return candidates

    def resolve_referents(self, user_text: str, understood: dict | None = None) -> Dict[str, Any]:
        if understood is None:
            try:
                understood = UtteranceParser().parse(user_text)
            except Exception:
                understood = {}

        native = self._native_turn_payload(user_text, understood)
        text_low = str(native.get("native_low", "") or "")
        refs = re.findall(r'\b(it|this|that|these|those|they|them)\b', text_low)
        result = {
            'topic': native["understood"].get('topic', ''),
            'entities': list(native["understood"].get('entities', [])),
            'search_query': native["understood"].get('search_query', ''),
            'referent_map': {},
            'confidence': 0.0,
            'source': '',
        }
        if not refs:
            self.last_referent_resolution = result
            return result

        is_callback_request = (
            native["understood"].get('is_callback') or native["understood"].get('is_clarification') or
            any(marker in text_low for marker in self._REFERENT_CALLBACK_MARKERS)
        )
        prefer_source = 'aurora' if is_callback_request else 'user'
        candidates = self._anchor_candidates(prefer_source=prefer_source)
        singular = candidates[0] if candidates else None
        if is_callback_request:
            callback_anchor = self._aurora_reply_anchor()
            if callback_anchor:
                singular = {
                    'label': callback_anchor,
                    'score': max(1.85, float((singular or {}).get('score', 0.0))),
                    'source': 'aurora',
                }

        plural: List[Dict[str, Any]] = []
        seen_labels = set()
        for item in candidates:
            label = str(item.get('label', ''))
            if label in seen_labels:
                continue
            plural.append(item)
            seen_labels.add(label)
            if len(plural) >= 2:
                break

        if singular and any(r in {'it', 'this', 'that'} for r in refs):
            for ref in refs:
                if ref in {'it', 'this', 'that'}:
                    result['referent_map'][ref] = singular['label']
            if not result['topic'] or result['topic'] in self._VAGUE_REFERENTS:
                result['topic'] = singular['label']
            result['confidence'] = max(result['confidence'], float(singular.get('score', 0.0)))
            result['source'] = str(singular.get('source', ''))

        if len(plural) >= 2 and any(r in {'they', 'them', 'these', 'those'} for r in refs):
            plural_labels = [str(item['label']) for item in plural]
            for ref in refs:
                if ref in {'they', 'them', 'these', 'those'}:
                    result['referent_map'][ref] = list(plural_labels)
            for label in plural_labels:
                titled = label.title()
                if titled not in result['entities']:
                    result['entities'].append(titled)
            result['confidence'] = max(result['confidence'], sum(float(p.get('score', 0.0)) for p in plural) / len(plural))
            if not result['source']:
                result['source'] = str(plural[0].get('source', ''))

        tail_words: List[str] = []
        topic_words = list(understood.get('topic_words', []))
        anchor_words = set(str(result.get('topic', '')).split())
        for word in topic_words:
            if word in self._VAGUE_REFERENTS or word in anchor_words:
                continue
            if word not in tail_words:
                tail_words.append(word)

        search_parts: List[str] = []
        if result.get('topic'):
            search_parts.extend(str(result['topic']).split())
        for entity in result.get('entities', [])[:2]:
            el = str(entity).lower()
            if el not in search_parts:
                search_parts.append(el)
        for word in tail_words[:4]:
            if word not in search_parts:
                search_parts.append(word)

        if search_parts:
            result['search_query'] = " ".join(search_parts)
        self.last_referent_resolution = result
        return result

    def surface_context(self, topic: str) -> bool:
        """
        Bring a backgrounded context back to the foreground.
        Returns True if a matching active context was found and surfaced.
        """
        if not topic:
            return False
        norm = self._normalize_mention(topic)
        for ctx_label in list(self.active_contexts.keys()):
            if self._normalize_mention(ctx_label) == norm:
                # Promote this context back to full salience
                self.active_contexts[ctx_label]['salience'] = 1.0
                self.active_contexts[ctx_label]['last_turn'] = self.turn_count
                if ctx_label != self.current_topic:
                    # Back-fill current_topic into the active_contexts map
                    if self.current_topic:
                        self.active_contexts.setdefault(self.current_topic, {
                            'salience': 0.6,
                            'opened_turn': self.turn_count,
                            'last_turn': self.turn_count,
                        })
                    if self.current_topic and self.current_topic not in self.topic_stack:
                        self.topic_stack = ([self.current_topic] + self.topic_stack)[:6]
                    self.current_topic = ctx_label
                return True
        return False

    def decay_active_contexts(self) -> None:
        """
        Gently decay salience of contexts that haven't been mentioned recently.
        Call once per turn (inside update_from_turn).
        """
        for label in list(self.active_contexts.keys()):
            if label == self.current_topic:
                self.active_contexts[label]['salience'] = 1.0
                self.active_contexts[label]['last_turn'] = self.turn_count
                continue
            turns_idle = max(0, self.turn_count - self.active_contexts[label].get('last_turn', 0))
            # 6% decay per idle turn — a context stays meaningful for ~15 turns of silence
            self.active_contexts[label]['salience'] = round(
                self.active_contexts[label]['salience'] * (0.94 ** turns_idle), 4
            )
        # Prune anything that has faded below threshold
        self.active_contexts = {
            k: v for k, v in self.active_contexts.items()
            if v['salience'] >= 0.05 or k == self.current_topic
        }

    def update_topic(self, topic: str):
        if topic and topic != self.current_topic:
            if self.current_topic:
                self.topic_stack = ([self.current_topic] + self.topic_stack)[:6]
                # Background the old topic rather than discarding it.
                self.active_contexts[self.current_topic] = {
                    'salience': 0.65,
                    'opened_turn': self.active_contexts.get(self.current_topic, {}).get('opened_turn', self.turn_count),
                    'last_turn': self.turn_count,
                }
            self.current_topic = topic
        # Always record the new current topic at full salience.
        if topic:
            self.active_contexts[topic] = {
                'salience': 1.0,
                'opened_turn': self.active_contexts.get(topic, {}).get('opened_turn', self.turn_count),
                'last_turn': self.turn_count,
            }

    def add_entities(self, entities: list):
        for e in entities:
            el = e.lower()
            if el not in self.recent_entities:
                self.recent_entities = ([el] + self.recent_entities)[:10]

    def note_user_facts(self, user_text: str, understood: dict | None = None):
        """
        Parse user statements and extract asserted facts.
        Supports: "X is Y", "X are Y", "the X is Y", "grass is green", etc.
        """
        import re
        if isinstance(user_text, dict) and understood is None:
            understood = dict(user_text or {})
            user_text = str(understood.get("raw", "") or understood.get("text", "") or "")
        native = self._native_turn_payload(user_text, understood)
        use_native_only = bool(native.get("has_native_projection"))
        if user_text.strip().endswith('?') and not use_native_only:
            return
        if not use_native_only:
            if self.extract_user_identity_assertion(user_text):
                return
            if self.extract_user_owned_fact_assertion(user_text):
                return
            if self.extract_behavior_alignment_request(user_text):
                return
        _skip_subjects = {
            'how', 'what', 'why', 'where', 'when', 'who', 'which', 'it',
            'this', 'that', 'they', 'he', 'she', 'we', 'you', 'i', 'my',
            'well', 'okay', 'ok', 'yes', 'no', 'but', 'and', 'so',
        }
        t = native["native_text"].strip().rstrip('.,!?') if use_native_only else user_text.strip().rstrip('.,!?')

        if use_native_only:
            topic = self.resolve_topic(native["understood"])
            if topic and topic not in _skip_subjects:
                if topic not in self.stated_facts:
                    self.stated_facts[topic] = {}
                if native["understood"].get("constraint"):
                    self.stated_facts[topic]["constraint"] = str(native["understood"].get("constraint", "") or "")
                if native["understood"].get("dimension"):
                    self.stated_facts[topic]["dimension"] = str(native["understood"].get("dimension", "") or "")
                if native["noncomp_state"].get("semantic_translation"):
                    self.stated_facts[topic]["native_translation"] = str(native["noncomp_state"].get("semantic_translation", "") or "")
                if native["noncomp_state"].get("manifold_translation"):
                    self.stated_facts[topic]["native_manifold"] = str(native["noncomp_state"].get("manifold_translation", "") or "")
                if native["understood"].get("summary"):
                    self.stated_facts[topic]["summary"] = str(native["understood"].get("summary", "") or "")
            self._register_understood_mentions(native["understood"], source='user')
            return

        m_uncertain = re.search(
            r'\b(?:might\s+be\s+wrong|may\s+be\s+wrong|not\s+sure|uncertain)\s+about\s+(.+)$',
            t,
            re.IGNORECASE,
        )
        if m_uncertain:
            focus = self._normalize_claim_object(m_uncertain.group(1))
            if focus:
                self.last_uncertainty_focus = focus

        reported_match = re.match(
            r'^(?:my\s+\w+|[A-Za-z][A-Za-z0-9_\-\s]{1,40}?)\s+'
            r'(?:says|said|thinks|thought|believes|believed|claims|claimed|insists|insisted)\s+(.+)$',
            t,
            re.IGNORECASE,
        )
        if reported_match:
            nested = str(reported_match.group(1) or '').strip()
            if nested and nested.lower() != t.lower():
                self.note_user_facts(nested)

        locative_action_match = re.match(
            r'^(?:i|we|he|she|they|someone|my\s+\w+|[A-Za-z][A-Za-z0-9_\-\s]{1,30}?)\s+'
            r'(?:left|leave|put|placed|place|set|kept|keep|stored|store)\s+'
            r'(?:my|the|our|his|her|their|a|an)?\s*([A-Za-z][A-Za-z0-9_\-\s]{1,60}?)\s+'
            r'(in|inside|on|at|under|by|near)\s+(.+)$',
            t,
            re.IGNORECASE,
        )
        if locative_action_match:
            subject, prep, location = locative_action_match.groups()
            subject_key = self._normalize_mention(subject)
            loc_value = f"{prep.lower()} {self._normalize_claim_object(location)}".strip()
            if subject_key and loc_value:
                if subject_key not in self.stated_facts:
                    self.stated_facts[subject_key] = {}
                self.stated_facts[subject_key]['location'] = loc_value

        locative_copula_match = re.match(
            r'^(?:the\s+|a\s+|an\s+)?([A-Za-z][A-Za-z0-9_\-\s]{1,60}?)\s+'
            r'(?:is|are|was|were)\s+(?:not\s+)?(in|inside|on|at|under|by|near)\s+(.+)$',
            t,
            re.IGNORECASE,
        )
        if locative_copula_match:
            subject, prep, location = locative_copula_match.groups()
            subject_key = self._normalize_mention(subject)
            loc_value = f"{prep.lower()} {self._normalize_claim_object(location)}".strip()
            if subject_key and loc_value:
                if subject_key not in self.stated_facts:
                    self.stated_facts[subject_key] = {}
                self.stated_facts[subject_key]['location'] = loc_value

        # "X is Y" / "X are Y" patterns
        m = re.match(
            r'^(?:the\s+|a\s+|an\s+)?([a-zA-Z]+)\s+(?:is|are)\s+(.+)$', t, re.IGNORECASE
        )
        if m and m.group(1).lower() not in _skip_subjects:
            subject = m.group(1).lower()
            predicate = m.group(2).lower().strip()
            if subject not in self.stated_facts:
                self.stated_facts[subject] = {}
            self.stated_facts[subject]['description'] = predicate
            # Extract color property specifically
            for cw in self._COLOR_WORDS:
                if cw in predicate.split():
                    self.stated_facts[subject]['color'] = cw
                    break

        # "X is to A as Y is to B" (analogy)  -- store both sides
        m2 = re.match(
            r'(\w+)\s+is\s+to\s+(\w+)\s+as\s+(\w+)\s+is\s+to\s+(\w+)', t, re.IGNORECASE
        )
        if m2:
            a_word, a_ref = m2.group(1).lower(), m2.group(2).lower()
            b_word, b_ref = m2.group(3).lower(), m2.group(4).lower()
            for word, ref in [(a_word, a_ref), (b_word, b_ref)]:
                if word not in self.stated_facts:
                    self.stated_facts[word] = {}
                self.stated_facts[word]['analogous_to'] = ref

    def get_stated_fact(self, subject: str, prop: str = None):
        facts = self.stated_facts.get(subject.lower(), {})
        if prop:
            return facts.get(prop)
        return facts

    def update_from_turn(self, understood: dict, user_text: str, aurora_text: str = ""):
        self._ensure_runtime_deques()
        self.turn_count += 1
        self.decay_active_contexts()
        skip_ingest = str(user_text or '').strip() == self._context_control_skip_text
        speaker_owned = self.integrate_speaker_owned_utterance(user_text, understood)
        skip_speaker_owned_ingest = bool(speaker_owned.get('handled'))
        topic = understood.get('topic', '')
        captured_claims: List[Dict[str, Any]] = []
        concept_clarification: Dict[str, Any] = {}
        semantic_frames: List[Dict[str, Any]] = []
        if not skip_ingest and not skip_speaker_owned_ingest:
            self.update_topic(topic)
            self.add_entities(understood.get('entities', []))
        prior_control_response = str(self._context_control_response_text or '').strip().lower()
        aurora_low = str(aurora_text or '').strip().lower()
        skip_aurora_claim_ingest = bool(prior_control_response and aurora_low.startswith(prior_control_response))
        if not skip_ingest and not skip_speaker_owned_ingest:
            self.note_user_facts(user_text, understood=understood)
            concept_clarification = self.note_concept_clarification(user_text, source='user', understood=understood)
            semantic_frames = self.note_semantic_principles(user_text, source='user', understood=understood)
            captured_claims = self.note_claims(user_text, source='user', understood=understood)
            self._register_understood_mentions(understood, source='user')
            self._register_user_utterance(
                user_text,
                understood,
                claims=captured_claims,
                semantic_frames=semantic_frames,
                concept_clarification=concept_clarification,
            )
        else:
            self._context_control_skip_text = ""
        try:
            anchor_resolution = self.resolve_claims(user_text, understood) or {}
        except Exception:
            anchor_resolution = {}
        anchor_claim = dict(anchor_resolution.get('focus_claim', {}) or {})
        if anchor_claim:
            self.last_response_anchor_claim = self._copy_claim(anchor_claim)
        else:
            semantic_anchor = str(
                dict(self.last_semantic_frame_resolution or {}).get('anchor', '') or ''
            ).strip()
            if semantic_anchor and not self._is_weak_anchor_label(semantic_anchor):
                self.update_topic(semantic_anchor)
                if self.last_response_anchor_claim:
                    claim_terms = self._claim_terms(self.last_response_anchor_claim)
                    if semantic_anchor not in claim_terms:
                        self.last_response_anchor_claim = {}
        for subject in list(self.stated_facts.keys())[-4:]:
            self._register_mention(subject, 'fact', 'memory', 0.68)
        _aurora_text_clean = str(aurora_text or "").strip()
        _internal_prefixes = ("[AFTERTHOUGHT]", "[CODE]", "[PRESSURE]", "125-layer manifold:")
        if any(_aurora_text_clean.startswith(p) for p in _internal_prefixes):
            _aurora_text_clean = ""
        self.last_aurora_response = _aurora_text_clean or self.last_aurora_response
        if _aurora_text_clean:
            skip_aurora_claim_ingest = bool(
                self._skip_next_aurora_claim_ingest or skip_aurora_claim_ingest
            )
            if not skip_aurora_claim_ingest:
                self.note_claims(_aurora_text_clean, source='aurora')
                self._register_response_mentions(_aurora_text_clean)
        self.refresh_claim_conflicts(preferred_claim=anchor_claim)
        if prior_control_response:
            self._context_control_response_text = ""
        self._skip_next_aurora_claim_ingest = False
        self.last_question_understood = understood

    def resolve_topic(self, understood: dict) -> str:
        """
        Resolve the real topic for vague follow-ups.
        "what about in Ohio?" → 'ohio' is an entity not a topic change → keep current_topic.
        "what about the color?" → 'color' is a genuine new topic.
        Also handles "back to X" / "going back to X" by surfacing matching active contexts.
        """
        topic = understood.get('topic', '')
        entities = understood.get('entities', [])
        vague = {'it', 'this', 'that', 'thing', 'there', 'here'}
        question_helpers = {'matter', 'break', 'breaks', 'missing', 'work', 'works', 'happen', 'happens'}
        # Detect "back to X" — surface a backgrounded context if it matches
        raw_text = str(understood.get('raw_text', '') or '').lower().strip()
        back_to_match = re.search(
            r'\b(?:back\s+to|return(?:ing)?\s+to|going\s+back\s+to|switch(?:ing)?\s+back\s+to)\b\s+(.+)',
            raw_text,
        )
        if back_to_match:
            target = back_to_match.group(1).strip().rstrip('?.!,')
            if self.surface_context(target):
                return self.current_topic
        # empty topic = conversational statement, NOT a vague reference  -- don't substitute
        # If the "topic" is actually a proper noun entity, it's a location modifier
        # not a topic change  -- keep the existing conversation topic
        topic_is_entity = topic and any(topic == e.lower() for e in entities)
        if (topic in vague or topic_is_entity or topic in question_helpers) and self.current_topic:
            return self.current_topic
        return topic

    def get_context_words(self) -> list:
        ctx = []
        if self.current_topic:
            ctx.append(self.current_topic)
        # Include up to 3 background active contexts ordered by salience
        bg_contexts = sorted(
            [(k, v['salience']) for k, v in self.active_contexts.items() if k != self.current_topic],
            key=lambda x: x[1],
            reverse=True,
        )
        for label, _sal in bg_contexts[:3]:
            if label and label not in ctx:
                ctx.append(label)
        ctx.extend(self.recent_entities[:4])
        for claim in list(self.recent_claims)[:3]:
            for label in (claim.get('subject', ''), claim.get('object', '')):
                label = str(label).strip()
                if label and label not in ctx:
                    ctx.append(label)
        for item in list(self.recent_mentions)[:4]:
            label = str(item.get('label', ''))
            if label and label not in ctx:
                ctx.append(label)
        return ctx


