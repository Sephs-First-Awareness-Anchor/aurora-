"""
aurora_utterance_parser.py
===========================
Replaces QueryUnderstanding with a binding-based utterance comprehension system.

THE CORE PRINCIPLE:
    No word is noise. Every word carries meaning.
    The job is not to remove words — it's to bind them together.

    "ok so what if" is not just "what".
    It is: [acknowledgment:ok] + [reasoning:so] + [hypothesis:what if]
    = a speculative pivot off prior context.

    "like i said" is not empty.
    It is: [similarity:like] + [speaker:i] + [past-statement:said]
    = a callback to a prior statement the speaker wants recognized.

    "just wondering" is not noise.
    It is: [minimization:just] + [inquiry:wondering]
    = a tentative, low-stakes question.

ARCHITECTURE:
    PragmaticRole       — what communicative function does a word/phrase serve?
    PragmaticSignal     — a detected signal in the utterance
    UtteranceFrame      — the overall communicative frame of the utterance
    UtteranceIntent     — the full parsed meaning, bound together
    UtteranceParser     — replaces QueryUnderstanding, produces UtteranceIntent

BACKWARD COMPATIBILITY:
    UtteranceParser.parse() returns a dict that is a superset of what
    QueryUnderstanding.parse() returned, so existing code using
    understood['topic'], understood['query_type'] etc. still works.
    The new fields are additive.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum


# ============================================================================
# PRAGMATIC ROLES — what every word class communicates
# ============================================================================

class PragmaticRole(Enum):
    # Stance signals
    ACKNOWLEDGMENT   = "acknowledgment"    # ok, alright, yeah, sure, right
    CONTRAST         = "contrast"          # but, however, though, yet, still
    CONSEQUENCE      = "consequence"       # so, therefore, then, thus, hence
    HYPOTHESIS       = "hypothesis"        # if, suppose, imagine, what if
    CONCESSION       = "concession"        # even though, although, despite
    SIMILARITY       = "similarity"        # like, as, similar, same
    ADDITION         = "addition"          # and, also, too, even, plus
    EMPHASIS         = "emphasis"          # really, very, even, just, literally
    MINIMIZATION     = "minimization"      # just, only, simply, merely
    UNCERTAINTY      = "uncertainty"       # maybe, perhaps, possibly, might
    CERTAINTY        = "certainty"         # definitely, certainly, absolutely
    RECENCY          = "recency"           # now, currently, today, just
    OPPOSITION       = "opposition"        # not, no, never, nothing
    CLARIFICATION    = "clarification"     # mean, i.e., that is, namely
    CALLBACK         = "callback"          # said, mentioned, as i said, again
    INQUIRY          = "inquiry"           # what, how, why, where, who, when
    REQUEST          = "request"           # please, can you, could you
    OPINION          = "opinion"           # think, believe, feel, seems
    EXPERIENCE       = "experience"        # feel, sense, experience, notice
    TOPIC_WORD       = "topic_word"        # genuine content/subject word
    ENTITY           = "entity"            # proper noun / named thing
    TIME_REF         = "time_ref"          # time-reference word
    FILLER           = "filler"            # um, uh, hmm — true noise


# ============================================================================
# PRAGMATIC SIGNAL MAPS — every "small" word gets its role
# ============================================================================

# Single-word pragmatic signals
_WORD_ROLES: Dict[str, PragmaticRole] = {
    # Acknowledgment — the speaker is accepting/pivoting
    'ok': PragmaticRole.ACKNOWLEDGMENT,
    'okay': PragmaticRole.ACKNOWLEDGMENT,
    'alright': PragmaticRole.ACKNOWLEDGMENT,
    'right': PragmaticRole.ACKNOWLEDGMENT,
    'yeah': PragmaticRole.ACKNOWLEDGMENT,
    'yep': PragmaticRole.ACKNOWLEDGMENT,
    'sure': PragmaticRole.ACKNOWLEDGMENT,
    'yes': PragmaticRole.ACKNOWLEDGMENT,
    'fine': PragmaticRole.ACKNOWLEDGMENT,
    'gotcha': PragmaticRole.ACKNOWLEDGMENT,
    'understood': PragmaticRole.ACKNOWLEDGMENT,

    # Contrast — the speaker is pushing back or introducing opposition
    'but': PragmaticRole.CONTRAST,
    'however': PragmaticRole.CONTRAST,
    'though': PragmaticRole.CONTRAST,
    'although': PragmaticRole.CONTRAST,
    'yet': PragmaticRole.CONTRAST,
    'still': PragmaticRole.CONTRAST,
    'whereas': PragmaticRole.CONTRAST,
    'while': PragmaticRole.CONTRAST,
    'otherwise': PragmaticRole.CONTRAST,

    # Consequence — the speaker is reasoning forward
    'so': PragmaticRole.CONSEQUENCE,
    'therefore': PragmaticRole.CONSEQUENCE,
    'thus': PragmaticRole.CONSEQUENCE,
    'hence': PragmaticRole.CONSEQUENCE,
    'then': PragmaticRole.CONSEQUENCE,
    'consequently': PragmaticRole.CONSEQUENCE,
    'because': PragmaticRole.CONSEQUENCE,
    'since': PragmaticRole.CONSEQUENCE,

    # Hypothesis — the speaker is proposing something speculatively
    'if': PragmaticRole.HYPOTHESIS,
    'suppose': PragmaticRole.HYPOTHESIS,
    'assuming': PragmaticRole.HYPOTHESIS,
    'imagine': PragmaticRole.HYPOTHESIS,
    'hypothetically': PragmaticRole.HYPOTHESIS,
    'pretend': PragmaticRole.HYPOTHESIS,
    'unless': PragmaticRole.HYPOTHESIS,

    # Similarity / example
    'like': PragmaticRole.SIMILARITY,
    'as': PragmaticRole.SIMILARITY,
    'similar': PragmaticRole.SIMILARITY,
    'same': PragmaticRole.SIMILARITY,
    'such': PragmaticRole.SIMILARITY,
    'example': PragmaticRole.SIMILARITY,
    'instance': PragmaticRole.SIMILARITY,
    'namely': PragmaticRole.SIMILARITY,

    # Addition
    'and': PragmaticRole.ADDITION,
    'also': PragmaticRole.ADDITION,
    'too': PragmaticRole.ADDITION,
    'plus': PragmaticRole.ADDITION,
    'additionally': PragmaticRole.ADDITION,
    'furthermore': PragmaticRole.ADDITION,
    'moreover': PragmaticRole.ADDITION,

    # Minimization — "just wondering", "only asking"
    'just': PragmaticRole.MINIMIZATION,
    'only': PragmaticRole.MINIMIZATION,
    'simply': PragmaticRole.MINIMIZATION,
    'merely': PragmaticRole.MINIMIZATION,
    'barely': PragmaticRole.MINIMIZATION,

    # Emphasis
    'really': PragmaticRole.EMPHASIS,
    'very': PragmaticRole.EMPHASIS,
    'even': PragmaticRole.EMPHASIS,
    'literally': PragmaticRole.EMPHASIS,
    'honestly': PragmaticRole.EMPHASIS,
    'actually': PragmaticRole.EMPHASIS,
    'basically': PragmaticRole.EMPHASIS,
    'seriously': PragmaticRole.EMPHASIS,
    'truly': PragmaticRole.EMPHASIS,

    # Uncertainty — the speaker is tentative
    'maybe': PragmaticRole.UNCERTAINTY,
    'perhaps': PragmaticRole.UNCERTAINTY,
    'possibly': PragmaticRole.UNCERTAINTY,
    'probably': PragmaticRole.UNCERTAINTY,
    'might': PragmaticRole.UNCERTAINTY,
    'could': PragmaticRole.UNCERTAINTY,
    'guess': PragmaticRole.UNCERTAINTY,
    'wonder': PragmaticRole.UNCERTAINTY,

    # Certainty
    'definitely': PragmaticRole.CERTAINTY,
    'certainly': PragmaticRole.CERTAINTY,
    'absolutely': PragmaticRole.CERTAINTY,
    'clearly': PragmaticRole.CERTAINTY,
    'obviously': PragmaticRole.CERTAINTY,

    # Recency / immediacy
    'now': PragmaticRole.RECENCY,
    'currently': PragmaticRole.RECENCY,
    'today': PragmaticRole.TIME_REF,
    'yesterday': PragmaticRole.TIME_REF,
    'tomorrow': PragmaticRole.TIME_REF,
    'recently': PragmaticRole.TIME_REF,
    'tonight': PragmaticRole.TIME_REF,
    'latest': PragmaticRole.RECENCY,

    # Opposition
    'not': PragmaticRole.OPPOSITION,
    'no': PragmaticRole.OPPOSITION,
    'never': PragmaticRole.OPPOSITION,
    'nothing': PragmaticRole.OPPOSITION,
    'neither': PragmaticRole.OPPOSITION,
    'nor': PragmaticRole.OPPOSITION,

    # Clarification intent
    'mean': PragmaticRole.CLARIFICATION,
    'means': PragmaticRole.CLARIFICATION,
    'meant': PragmaticRole.CLARIFICATION,

    # Opinion / subjective
    'think': PragmaticRole.OPINION,
    'thought': PragmaticRole.OPINION,
    'believe': PragmaticRole.OPINION,
    'seem': PragmaticRole.OPINION,
    'seems': PragmaticRole.OPINION,

    # Experience / sensory
    'feel': PragmaticRole.EXPERIENCE,
    'feels': PragmaticRole.EXPERIENCE,
    'sense': PragmaticRole.EXPERIENCE,
    'experience': PragmaticRole.EXPERIENCE,
    'notice': PragmaticRole.EXPERIENCE,

    # Inquiry
    'what': PragmaticRole.INQUIRY,
    'how': PragmaticRole.INQUIRY,
    'why': PragmaticRole.INQUIRY,
    'where': PragmaticRole.INQUIRY,
    'who': PragmaticRole.INQUIRY,
    'when': PragmaticRole.INQUIRY,
    'which': PragmaticRole.INQUIRY,

    # True filler — actual noise, carries no meaning
    'um': PragmaticRole.FILLER,
    'uh': PragmaticRole.FILLER,
    'hmm': PragmaticRole.FILLER,
    'hm': PragmaticRole.FILLER,
    'err': PragmaticRole.FILLER,
    'er': PragmaticRole.FILLER,
    'ah': PragmaticRole.FILLER,
    'oh': PragmaticRole.FILLER,
}

# Multi-word phrases that bind into a single pragmatic unit
_PHRASE_ROLES: List[Tuple[str, PragmaticRole]] = [
    # Hypothesis phrases
    ("what if",           PragmaticRole.HYPOTHESIS),
    ("what would happen", PragmaticRole.HYPOTHESIS),
    ("what could",        PragmaticRole.HYPOTHESIS),
    ("suppose that",      PragmaticRole.HYPOTHESIS),
    ("let's say",         PragmaticRole.HYPOTHESIS),
    ("lets say",          PragmaticRole.HYPOTHESIS),
    ("say that",          PragmaticRole.HYPOTHESIS),
    ("in case",           PragmaticRole.HYPOTHESIS),
    ("even if",           PragmaticRole.HYPOTHESIS),

    # Acknowledgment + pivot phrases
    ("ok so",             PragmaticRole.ACKNOWLEDGMENT),
    ("okay so",           PragmaticRole.ACKNOWLEDGMENT),
    ("alright so",        PragmaticRole.ACKNOWLEDGMENT),
    ("right so",          PragmaticRole.ACKNOWLEDGMENT),
    ("yeah so",           PragmaticRole.ACKNOWLEDGMENT),
    ("sure so",           PragmaticRole.ACKNOWLEDGMENT),
    # Note: "ok but", "yeah but" etc. are intentionally NOT listed as phrases.
    # Each word tags individually (ok→ACKNOWLEDGMENT, but→CONTRAST),
    # and the frame logic combines them into CHALLENGING.

    # Clarification phrases
    ("i mean",            PragmaticRole.CLARIFICATION),
    ("by that i mean",    PragmaticRole.CLARIFICATION),
    ("in other words",    PragmaticRole.CLARIFICATION),
    ("that is",           PragmaticRole.CLARIFICATION),
    ("to be clear",       PragmaticRole.CLARIFICATION),
    ("to clarify",        PragmaticRole.CLARIFICATION),
    ("in terms of",       PragmaticRole.CLARIFICATION),
    ("as in",             PragmaticRole.CLARIFICATION),
    ("meaning",           PragmaticRole.CLARIFICATION),

    # Callback phrases
    ("like i said",       PragmaticRole.CALLBACK),
    ("as i said",         PragmaticRole.CALLBACK),
    ("as i mentioned",    PragmaticRole.CALLBACK),
    ("as i was saying",   PragmaticRole.CALLBACK),
    ("going back to",     PragmaticRole.CALLBACK),
    ("coming back to",    PragmaticRole.CALLBACK),
    ("was asking",        PragmaticRole.CALLBACK),
    ("was saying",        PragmaticRole.CALLBACK),
    ("was meaning",       PragmaticRole.CALLBACK),
    ("what i asked",      PragmaticRole.CALLBACK),
    ("what i said",       PragmaticRole.CALLBACK),
    ("what i meant",      PragmaticRole.CALLBACK),
    ("not what i",        PragmaticRole.CLARIFICATION),

    # Experience phrases
    ("feel like",         PragmaticRole.EXPERIENCE),
    ("feels like",        PragmaticRole.EXPERIENCE),
    ("how does it feel",  PragmaticRole.EXPERIENCE),
    ("what is it like",   PragmaticRole.EXPERIENCE),
    ("what's it like",    PragmaticRole.EXPERIENCE),

    # Uncertainty phrases
    ("i'm not sure",      PragmaticRole.UNCERTAINTY),
    ("im not sure",       PragmaticRole.UNCERTAINTY),
    ("not sure if",       PragmaticRole.UNCERTAINTY),
    ("i wonder",          PragmaticRole.UNCERTAINTY),
    ("not certain",       PragmaticRole.UNCERTAINTY),

    # Opinion phrases — first-person statements
    ("i think",           PragmaticRole.OPINION),
    ("i believe",         PragmaticRole.OPINION),
    ("in my opinion",     PragmaticRole.OPINION),
    ("it seems",          PragmaticRole.OPINION),
    ("seems like",        PragmaticRole.OPINION),
    ("i feel like",       PragmaticRole.OPINION),
    # Soliciting Aurora's opinion/perspective ("your take", "your view", "what do you think")
    ("your take",         PragmaticRole.OPINION),
    ("your view",         PragmaticRole.OPINION),
    ("your views",        PragmaticRole.OPINION),
    ("your thoughts",     PragmaticRole.OPINION),
    ("your opinion",      PragmaticRole.OPINION),
    ("your perspective",  PragmaticRole.OPINION),
    ("your position",     PragmaticRole.OPINION),
    ("your stance",       PragmaticRole.OPINION),
    ("what do you think", PragmaticRole.OPINION),
    ("how do you see",    PragmaticRole.OPINION),
    ("do you agree",      PragmaticRole.OPINION),
    ("do you think",      PragmaticRole.OPINION),
    ("do you believe",    PragmaticRole.OPINION),
    ("do you consider",   PragmaticRole.OPINION),
    # Soliciting Aurora's experience/feelings
    ("do you feel",       PragmaticRole.EXPERIENCE),
    ("have you ever",     PragmaticRole.EXPERIENCE),
    ("have you felt",     PragmaticRole.EXPERIENCE),
    ("how do you feel",   PragmaticRole.EXPERIENCE),
    ("do you experience", PragmaticRole.EXPERIENCE),
    ("do you ever",       PragmaticRole.EXPERIENCE),

    # Concession phrases
    ("even though",       PragmaticRole.CONCESSION),
    ("despite that",      PragmaticRole.CONCESSION),
    ("regardless of",     PragmaticRole.CONCESSION),
    ("having said that",  PragmaticRole.CONCESSION),
]


# ============================================================================
# UTTERANCE FRAME — the overall communicative shape
# ============================================================================

class UtteranceFrame(Enum):
    """The high-level communicative frame of the whole utterance."""
    HYPOTHETICAL    = "hypothetical"    # "what if X", "suppose Y"
    CONTRASTIVE     = "contrastive"     # "but X", "however Y"
    EXPLORATORY     = "exploratory"     # curious, open-ended
    CLARIFYING      = "clarifying"      # "i mean X", "by X i mean Y"
    ASSERTING       = "asserting"       # stating a fact or opinion
    REQUESTING      = "requesting"      # asking for something specific
    ACKNOWLEDGING   = "acknowledging"   # "ok", "yeah", "gotcha"
    CHALLENGING     = "challenging"     # "yeah but", "ok but"
    SPECULATING     = "speculating"     # tentative, uncertain
    CALLBACK        = "callback"        # referencing something prior
    EXPERIENTIAL    = "experiential"    # asking about subjective experience
    UNKNOWN         = "unknown"


# ============================================================================
# PRAGMATIC SIGNAL dataclass
# ============================================================================

@dataclass
class PragmaticSignal:
    """A detected pragmatic signal in the utterance."""
    role: PragmaticRole
    span: str           # The text that triggered this signal
    position: int       # Character position in the utterance
    is_phrase: bool = False  # True if this is a multi-word phrase signal


# ============================================================================
# UTTERANCE INTENT — the full parsed meaning
# ============================================================================

@dataclass
class UtteranceIntent:
    """
    The complete parsed intent of an utterance, with all words bound
    to their communicative roles.
    """
    # Original text
    raw_text: str

    # Backward-compatible fields (same as QueryUnderstanding output)
    topic: str = ""
    topic_words: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    time_ref: Optional[str] = None
    query_type: str = "factual_general"
    search_query: str = ""

    # New binding-based fields
    pragmatic_signals: List[PragmaticSignal] = field(default_factory=list)
    frame: UtteranceFrame = UtteranceFrame.UNKNOWN
    stance: str = "neutral"       # curious / challenging / tentative / accepting / clarifying
    utterance_type: str = "unknown"  # question / statement / correction / hypothesis / callback
    full_phrase: str = ""         # The key phrase, all words bound together
    negated: bool = False         # Does the utterance contain negation?
    is_hypothetical: bool = False
    is_clarification: bool = False
    is_callback: bool = False
    is_experiential: bool = False
    is_opinion: bool = False
    is_imperative: bool = False   # directive frame: base-verb + entity target, no question mark

    def to_dict(self) -> Dict[str, Any]:
        """Convert to backward-compatible dict (superset of QueryUnderstanding output)."""
        return {
            # Backward compatible
            'topic':              self.topic,
            'topic_words':        self.topic_words,
            'entities':           self.entities,
            'time_ref':           self.time_ref,
            'query_type':         self.query_type,
            'search_query':       self.search_query,
            # New
            'pragmatic_signals':  [(s.role.value, s.span) for s in self.pragmatic_signals],
            'frame':              self.frame.value,
            'stance':             self.stance,
            'utterance_type':     self.utterance_type,
            'full_phrase':        self.full_phrase,
            'negated':            self.negated,
            'is_hypothetical':    self.is_hypothetical,
            'is_clarification':   self.is_clarification,
            'is_callback':        self.is_callback,
            'is_experiential':    self.is_experiential,
            'is_opinion':         self.is_opinion,
            'is_imperative':      self.is_imperative,
            'raw_text':           self.raw_text,
        }


# ============================================================================
# UTTERANCE PARSER — the binding engine
# ============================================================================

class UtteranceParser:
    """
    Parses utterances by binding every word to its communicative role,
    then composing those roles into a full understanding of what's being said.

    Replaces QueryUnderstanding.
    Drop-in compatible: parse() returns a dict superset of the old output.

    The key difference:
        OLD: remove words → find topic
        NEW: classify ALL words → bind them → read intent from the binding

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    # Words with NO communicative role — true filler only
    _TRUE_FILLER = {'um', 'uh', 'hmm', 'hm', 'er', 'err', 'ah', 'oh'}

    # Structural words — grammatically necessary but not topic content.
    # Includes contractions because "thats/wasnt/cant/wont" are never topics.
    _STRUCTURAL = {
        # Articles, prepositions, conjunctions
        'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
        'by', 'from', 'into', 'through', 'about', 'up', 'down', 'out',
        'off', 'over', 'under', 'after', 'before', 'between', 'among',
        # Verb auxiliaries
        'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'shall',
        'am', 'get', 'got', 'go', 'went',
        # Pronouns + determiners
        'this', 'that', 'these', 'those', 'it', 'its',
        'i', 'you', 'we', 'they', 'he', 'she', 'me', 'him', 'her',
        'my', 'your', 'our', 'their', 'his', 'them',
        # Contractions — "thats", "wasnt", "cant", "wont", "ive" are never topics
        'thats', 'whats', 'hows', 'whos', 'wheres', 'theres',
        'isnt', 'arent', 'wasnt', 'werent', 'hasnt', 'havent', 'hadnt',
        'cant', 'cannot', 'wont', 'wouldnt', 'shouldnt', 'couldnt',
        'didnt', 'doesnt', 'dont', 'wont', 'aint',
        'ive', 'id', 'ill', 'im', 'youre', 'were', 'theyre',
        'youve', 'weve', 'theyve', 'youll', 'well', 'theyll',
        'wouldve', 'couldve', 'shouldve',
        # Common function words
        'can', 'could', 'would', 'should', 'may', 'might', 'must',
        'shall', 'will', 'let', 'make', 'made',
        # Filler starts
        'oh', 'ah', 'hey', 'hi', 'hello',
        # Request / imperative verbs — directives to Aurora, not topic content
        'tell', 'show', 'give', 'explain', 'describe', 'define', 'find',
        'look', 'search', 'check', 'list', 'name', 'say', 'share', 'pick',
        'ask', 'help', 'provide', 'suggest', 'recommend', 'compare',
        # Idiomatic discourse markers — never genuine topic content
        # e.g. "it sounds like", "seems like", "looks like", "feels like"
        'sounds', 'seems', 'appears', 'looks', 'feels',
        # Stance/hedge openers
        'think', 'thought', 'guess', 'suppose', 'reckon', 'imagine',
        # Connective openers
        'mean', 'means', 'meant',
        # Opinion-request markers — "your take on X" / "your view on X"
        # These are stance-request frames, not topic content
        'take', 'view', 'stance', 'position',
    }

    # Words that are clearly topic words (nouns, verbs, adjectives)
    # that should never be misclassified as pragmatic markers
    _TOPIC_OVERRIDES = {
        'feeling', 'feelings', 'feeling', 'thought', 'thoughts',
        'thinking', 'believes', 'belief', 'opinion', 'notion',
        'idea', 'concept', 'meaning', 'purpose', 'point',
    }

    # Proper noun skip list — capitalized words that are NOT proper nouns
    _SKIP_CAPS = {
        'what', 'where', 'how', 'why', 'who', 'when', 'which',
        'the', 'a', 'is', 'are', 'can', 'could', 'would', 'should',
        'i', 'you', 'we', 'they', 'he', 'she', 'it', 'my', 'your',
        'im', 'ive', 'id', 'ill', 'its', 'isnt', 'arent', 'wasnt',
        'dont', 'doesnt', 'didnt', 'cant', 'wont', 'wouldnt',
        'so', 'but', 'and', 'or', 'if', 'then', 'also', 'just',
        'yeah', 'yes', 'no', 'ok', 'okay', 'well', 'now', 'right',
        'happy', 'glad', 'great', 'good', 'nice', 'fine', 'sure',
        'thanks', 'thank', 'please', 'sorry', 'wow',
        # Imperative/modal verb starters — appear capitalized at sentence start
        # but are NEVER proper nouns. e.g. "Be specific", "Do tell", "Now try"
        'be', 'do', 'go', 'get', 'let', 'put', 'set', 'try', 'use',
        'tell', 'show', 'give', 'say', 'make', 'take', 'keep', 'help',
        'look', 'find', 'ask', 'run', 'add', 'list', 'note', 'see',
        'describe', 'explain', 'define', 'compare', 'summarize', 'answer',
        'now', 'not', 'there', 'here', 'this', 'that', 'these', 'those',
        'some', 'any', 'more', 'most', 'less', 'then', 'nor', 'yet',
        'in', 'on', 'at', 'of', 'to', 'for', 'with', 'by', 'from', 'as',
    }

    # Time reference words
    _TIME_WORDS = {
        'today', 'tomorrow', 'yesterday', 'now', 'currently', 'tonight',
        'week', 'month', 'year', 'recently', 'latest', 'current',
        'soon', 'later', 'earlier', 'before', 'after', 'ago',
    }

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse an utterance. Returns a dict compatible with the old
        QueryUnderstanding.parse() output, plus new binding fields.
        """
        intent = self._parse_full(text)
        return intent.to_dict()

    def _parse_full(self, text: str) -> UtteranceIntent:
        t = text.strip()
        t_low = t.lower()
        intent = UtteranceIntent(raw_text=t)

        # ---- Step 1: Detect phrase-level signals first (longest match) ----
        phrase_signals, phrase_spans = self._detect_phrase_signals(t_low)
        intent.pragmatic_signals.extend(phrase_signals)

        # ---- Step 2: Tag every remaining word ----
        word_signals = self._tag_words(t_low, phrase_spans)
        intent.pragmatic_signals.extend(word_signals)

        # ---- Step 3: Extract entities (proper nouns) ----
        intent.entities = self._extract_entities(t)

        # ---- Step 4: Extract topic words (genuine content words) ----
        topic_words, time_ref = self._extract_topic_words(t_low, phrase_spans)
        intent.topic_words = topic_words[:6]
        # Topic selection: if the first content word is a relational/causal verb
        # (e.g. "causes", "makes", "something", "there"), it is NOT the subject —
        # pair it with the next content word and promote that as the primary topic.
        # Relational heads: words that sit at the front of a question but are
        # never the actual subject — they pair with the following noun to name it.
        # "What causes RAINBOW..." → skip "causes", take "rainbow"
        # "Now tell me something completely different: how does COMPASS work?"
        #   → skip "something" + "completely" + "different", take "compass"
        _RELATIONAL_HEADS = {
            'cause', 'causes', 'caused', 'causing',
            'make', 'makes', 'made', 'making',
            'produce', 'produces', 'produced', 'producing',
            'create', 'creates', 'created', 'creating',
            'trigger', 'triggers', 'triggered',
            'result', 'results', 'resulted',
            'form', 'forms', 'formed', 'forming',
            'work', 'works', 'worked', 'working',
            'function', 'functions',
            'something', 'anything', 'everything', 'nothing',
            'there', 'here', 'tell',
            'completely', 'entirely', 'totally', 'utterly',
            'different', 'various', 'separate', 'another', 'other',
            'new', 'next', 'same', 'similar',
            'kind', 'kinds', 'type', 'types', 'sort', 'sorts',
            'way', 'ways', 'aspect', 'aspects', 'part', 'parts',
            # Cardinal numbers as relational quantifiers — never the subject
            # e.g. "in ONE sentence" → topic is the content, not the count
            'one', 'two', 'three', 'four', 'five', 'six', 'seven',
            'eight', 'nine', 'ten', 'few', 'several', 'many', 'most',
        }
        _primary = ""
        for _tw in topic_words:
            if _tw not in _RELATIONAL_HEADS:
                _primary = _tw
                break
        intent.topic = _primary if _primary else (
            intent.entities[0].lower() if intent.entities else ""
        )
        intent.time_ref = time_ref

        # ---- Step 5: Build the full_phrase (key content, bound together) ----
        intent.full_phrase = self._build_full_phrase(t_low, topic_words, intent.entities)

        # ---- Step 6: Detect negation ----
        intent.negated = bool(re.search(
            r"\b(not|no|never|nothing|neither|nor|don't|doesn't|didn't|"
            r"can't|won't|wouldn't|couldn't|isn't|aren't|wasn't|weren't)\b",
            t_low
        ))

        # ---- Step 7: Classify boolean flags from signals ----
        signal_roles = {s.role for s in intent.pragmatic_signals}
        intent.is_hypothetical  = PragmaticRole.HYPOTHESIS in signal_roles
        intent.is_clarification = PragmaticRole.CLARIFICATION in signal_roles
        intent.is_callback      = PragmaticRole.CALLBACK in signal_roles
        intent.is_experiential  = PragmaticRole.EXPERIENCE in signal_roles
        intent.is_opinion       = PragmaticRole.OPINION in signal_roles

        # Imperative / directive frame: grammatically, an imperative begins with a
        # bare base-form verb (or modal REQUEST) directed at a named entity, with
        # no question marker.  This is a syntactic property of the utterance, not
        # a keyword rule in the pipeline — the pipeline reads is_imperative as a
        # grammatical signal and routes accordingly.
        _ACTION_BASE_FORMS = {
            'open', 'start', 'launch', 'run', 'load', 'play', 'resume',
            'close', 'stop', 'quit', 'exit', 'kill',
            'send', 'call', 'dial', 'text', 'message',
            'turn', 'toggle', 'enable', 'disable', 'set',
            'take', 'capture', 'record', 'show', 'display',
        }
        _first_word = t_low.split()[0] if t_low.split() else ""
        _is_q = '?' in t
        _has_request = PragmaticRole.REQUEST in signal_roles
        intent.is_imperative = (
            (_first_word in _ACTION_BASE_FORMS or _has_request)
            and not _is_q
            and bool(intent.entities)
        )

        # ---- Step 8: Determine utterance frame ----
        intent.frame = self._infer_frame(intent, t_low)

        # ---- Step 9: Determine stance ----
        intent.stance = self._infer_stance(intent, t_low)

        # ---- Step 10: Determine utterance type ----
        intent.utterance_type = self._infer_utterance_type(t, t_low, signal_roles)

        # ---- Step 11: Classify query type (backward compat) ----
        intent.query_type = self._classify_query_type(
            t_low, intent.topic, intent.entities, intent.topic_words, intent
        )

        # ---- Step 12: Build search query ----
        intent.search_query = self._build_search_query(intent)

        return intent

    # ------------------------------------------------------------------
    # STEP 1: Phrase-level signal detection
    # ------------------------------------------------------------------

    def _detect_phrase_signals(self, t_low: str) -> Tuple[List[PragmaticSignal], set]:
        """
        Find multi-word pragmatic phrases. Returns signals and the set of
        character positions covered (so single-word tagging skips them).
        """
        signals = []
        covered_positions = set()

        # Sort by length descending — longest match wins
        sorted_phrases = sorted(_PHRASE_ROLES, key=lambda p: len(p[0]), reverse=True)

        for phrase, role in sorted_phrases:
            pos = 0
            while True:
                idx = t_low.find(phrase, pos)
                if idx == -1:
                    break
                # Make sure it's a word boundary
                before_ok = (idx == 0 or not t_low[idx-1].isalpha())
                end_idx = idx + len(phrase)
                after_ok = (end_idx >= len(t_low) or not t_low[end_idx].isalpha())
                if before_ok and after_ok:
                    # Check positions aren't already covered
                    positions = set(range(idx, end_idx))
                    if not positions & covered_positions:
                        signals.append(PragmaticSignal(
                            role=role,
                            span=phrase,
                            position=idx,
                            is_phrase=True
                        ))
                        covered_positions.update(positions)
                pos = idx + 1

        return signals, covered_positions

    # ------------------------------------------------------------------
    # STEP 2: Single-word tagging
    # ------------------------------------------------------------------

    def _tag_words(self, t_low: str, covered: set) -> List[PragmaticSignal]:
        """Tag individual words that aren't covered by phrase signals."""
        signals = []
        for match in re.finditer(r'\b([a-z]+)\b', t_low):
            word = match.group(1)
            pos = match.start()
            # Skip if covered by a phrase signal
            if pos in covered:
                continue
            role = _WORD_ROLES.get(word)
            if role and role != PragmaticRole.FILLER:
                signals.append(PragmaticSignal(
                    role=role,
                    span=word,
                    position=pos,
                    is_phrase=False
                ))
        return signals

    # ------------------------------------------------------------------
    # STEP 4: Topic word extraction
    # ------------------------------------------------------------------

    def _extract_topic_words(self, t_low: str,
                              covered: set) -> Tuple[List[str], Optional[str]]:
        """
        Extract content words — the words that name things, actions, qualities.
        These are NOT removed if they have pragmatic role — they get BOTH
        their role AND topic status when context warrants.
        """
        time_ref = None
        topic_words = []

        words = re.findall(r'[a-z]{2,}', t_low)
        for word in words:
            # True filler — skip
            if word in self._TRUE_FILLER:
                continue
            # Structural grammar words — skip for topics
            if word in self._STRUCTURAL:
                continue
            # Time words
            if word in self._TIME_WORDS:
                if not time_ref:
                    time_ref = word
                continue
            # Words with explicit pragmatic role — they signal intent,
            # NOT necessarily a topic. But keep them if they're also
            # in TOPIC_OVERRIDES (e.g., "thoughts", "feelings")
            role = _WORD_ROLES.get(word)
            if role and role not in (PragmaticRole.FILLER,) and word not in self._TOPIC_OVERRIDES:
                # These carry pragmatic meaning, not topic content
                # Exception: inquiry words like "what", "how" — keep them
                # if they're part of the main phrase
                continue
            # Short words that aren't meaningful content
            if len(word) < 3 and word not in {'ai', 'is', 'do'}:
                continue
            topic_words.append(word)

        return topic_words, time_ref

    # ------------------------------------------------------------------
    # STEP 3: Entity extraction
    # ------------------------------------------------------------------

    def _extract_entities(self, t: str) -> List[str]:
        """Extract proper nouns."""
        return [w for w in re.findall(r'\b[A-Z][a-z]{1,}\b', t)
                if w.lower() not in self._SKIP_CAPS]

    # ------------------------------------------------------------------
    # STEP 5: Full phrase construction
    # ------------------------------------------------------------------

    def _build_full_phrase(self, t_low: str, topic_words: List[str],
                            entities: List[str]) -> str:
        """
        Build the key phrase that captures the subject of the utterance.
        Binds topic words and entities in their original order.
        """
        all_content = []
        for w in topic_words[:5]:
            all_content.append(w)
        for e in entities[:2]:
            if e.lower() not in all_content:
                all_content.append(e.lower())

        if not all_content:
            # Fallback: use the stripped text with only filler removed
            stripped = re.sub(r'\b(' + '|'.join(self._TRUE_FILLER) + r')\b', '', t_low)
            return ' '.join(stripped.split())

        return ' '.join(all_content)

    # ------------------------------------------------------------------
    # STEP 8: Frame inference
    # ------------------------------------------------------------------

    def _infer_frame(self, intent: UtteranceIntent, t_low: str) -> UtteranceFrame:
        """Infer the high-level communicative frame from signal combination."""
        roles = {s.role for s in intent.pragmatic_signals}

        if intent.is_hypothetical:
            return UtteranceFrame.HYPOTHETICAL
        if intent.is_experiential:
            return UtteranceFrame.EXPERIENTIAL
        # CHALLENGING: "yeah but", "ok but" — must check before is_clarification
        # because "yeah but what i meant" has BOTH clarification AND contrast+ack
        if PragmaticRole.CONTRAST in roles and PragmaticRole.ACKNOWLEDGMENT in roles:
            return UtteranceFrame.CHALLENGING
        if intent.is_clarification:
            return UtteranceFrame.CLARIFYING
        if intent.is_callback:
            return UtteranceFrame.CALLBACK
        if PragmaticRole.CONTRAST in roles:
            return UtteranceFrame.CONTRASTIVE
        if PragmaticRole.ACKNOWLEDGMENT in roles and not t_low.strip().endswith('?'):
            return UtteranceFrame.ACKNOWLEDGING
        if intent.is_opinion or PragmaticRole.UNCERTAINTY in roles:
            return UtteranceFrame.SPECULATING
        if PragmaticRole.INQUIRY in roles or t_low.strip().endswith('?'):
            return UtteranceFrame.EXPLORATORY
        if PragmaticRole.OPPOSITION in roles:
            return UtteranceFrame.CONTRASTIVE

        return UtteranceFrame.ASSERTING

    # ------------------------------------------------------------------
    # STEP 9: Stance inference
    # ------------------------------------------------------------------

    def _infer_stance(self, intent: UtteranceIntent, t_low: str) -> str:
        """Infer the speaker's stance."""
        roles = {s.role for s in intent.pragmatic_signals}

        if PragmaticRole.ACKNOWLEDGMENT in roles and PragmaticRole.CONTRAST in roles:
            return "challenging"
        if PragmaticRole.HYPOTHESIS in roles:
            return "speculative"
        if PragmaticRole.CLARIFICATION in roles:
            return "clarifying"
        if PragmaticRole.UNCERTAINTY in roles:
            return "tentative"
        if PragmaticRole.ACKNOWLEDGMENT in roles:
            return "accepting"
        if PragmaticRole.CONTRAST in roles:
            return "contrastive"
        if PragmaticRole.OPINION in roles:
            return "subjective"
        if PragmaticRole.EMPHASIS in roles:
            return "emphatic"
        if PragmaticRole.INQUIRY in roles or t_low.strip().endswith('?'):
            return "curious"

        return "neutral"

    # ------------------------------------------------------------------
    # STEP 10: Utterance type inference
    # ------------------------------------------------------------------

    def _infer_utterance_type(self, t: str, t_low: str,
                               signal_roles: set) -> str:
        """Classify the utterance type."""
        if PragmaticRole.HYPOTHESIS in signal_roles:
            return "hypothesis"
        if PragmaticRole.CLARIFICATION in signal_roles:
            return "clarification"
        if PragmaticRole.CALLBACK in signal_roles:
            return "callback"
        if PragmaticRole.EXPERIENCE in signal_roles and PragmaticRole.INQUIRY in signal_roles:
            return "experience_question"
        if t.strip().endswith('?') or PragmaticRole.INQUIRY in signal_roles:
            return "question"
        if PragmaticRole.CONTRAST in signal_roles:
            return "correction"
        if PragmaticRole.OPPOSITION in signal_roles:
            return "negation"

        return "statement"

    # ------------------------------------------------------------------
    # STEP 11: Query type classification (backward compat)
    # ------------------------------------------------------------------

    def _classify_query_type(self, t_low: str, topic: str, entities: list,
                              topic_words: list, intent: UtteranceIntent) -> str:
        """
        Classify the query type for routing/search purposes.
        Takes the full intent into account, not just stripped words.
        """
        # Statements — the speaker is asserting, not asking.
        # NEVER search for a statement. Let L5 respond conversationally.
        t_stripped = t_low.rstrip(' .')
        ends_with_q = t_low.strip().endswith('?')
        starts_with_q_word = any(t_low.strip().startswith(w + ' ') or t_low.strip() == w
                                  for w in ('what', 'how', 'why', 'where', 'who', 'when',
                                            'which', 'define', 'explain', 'tell me',
                                            'look up', 'search', 'can you', 'could you',
                                            'do you', 'does', 'is there', 'are there'))
        _is_question = ends_with_q or starts_with_q_word
        if not _is_question:
            # Check for question words buried mid-sentence as well
            _has_question_word = bool(re.search(
                r'\b(what|how|why|where|who|when|which)\b', t_low
            ))
            if not _has_question_word:
                return 'statement'

        # Experience questions about Aurora → never a definition search
        if intent.is_experiential:
            return "experience"

        # Hypothetical → treat as open-ended exploration, not definition
        if intent.is_hypothetical:
            return "hypothetical"

        # Clarification → route back to conversational, no search
        if intent.is_clarification:
            return "clarification"

        # Weather
        weather_words = {'weather', 'forecast', 'temperature', 'rain', 'snow',
                         'humidity', 'wind', 'climate', 'sunny', 'cloudy'}
        if topic in weather_words or any(w in weather_words for w in t_low.split()):
            if entities:
                return 'weather_location'
            return 'definition'

        # "look up X" is a search request, not a single-word definition
        if re.search(r'\b(look\s+up|search\s+for|search)\b', t_low):
            if len(topic_words) <= 1:
                return 'definition'
            return 'factual_general'

        # "define X" or "what does X mean" → definition
        if re.search(r'\b(define|definition\s+of|meaning\s+of)\b', t_low):
            return 'definition'

        # "what is X" where X is single concept
        if re.search(r'\bwhat\s+(is|are|does)\b', t_low):
            if len(topic_words) <= 2:
                return 'definition'
            return 'factual_general'

        # How-to
        if re.search(r'\bhow\s+(do|does|can|to|would|might)\b', t_low):
            return 'how_to'

        # Entity queries
        if entities:
            return 'factual_entity'

        return 'factual_general'

    # ------------------------------------------------------------------
    # STEP 12: Search query construction
    # ------------------------------------------------------------------

    def _build_search_query(self, intent: UtteranceIntent) -> str:
        """
        Build the search string.
        Uses full topic phrase — never collapses to single word.
        Accounts for intent frame.
        """
        topic_words = intent.topic_words
        entities = intent.entities
        time_ref = intent.time_ref
        query_type = intent.query_type

        # Experience, hypothetical, clarification → shouldn't search
        if query_type in ('experience', 'clarification', 'hypothetical'):
            return ' '.join(topic_words[:3]) if topic_words else ""

        parts = []
        if query_type == 'weather_location' and entities:
            parts.extend(entities[:2])
            parts.append('weather')
        elif query_type == 'definition':
            # Single concept
            parts = [intent.topic] if intent.topic else list(topic_words[:2])
        elif query_type in ('how_to', 'factual_general'):
            # Full phrase — never single word
            parts.extend(topic_words[:5])
            if entities:
                parts.extend(entities[:2])
        elif entities and intent.topic:
            parts.append(intent.topic)
            parts.extend(entities[:2])
        elif topic_words:
            parts.extend(topic_words[:4])

        if time_ref and time_ref not in parts:
            parts.append(time_ref)

        return " ".join(p for p in parts if p)


# ============================================================================
# CONVENIENCE — drop-in replacement function
# ============================================================================

_PARSER_INSTANCE = UtteranceParser()

def parse_utterance(text: str) -> Dict[str, Any]:
    """
    Parse an utterance. Drop-in replacement for QueryUnderstanding().parse(text).
    Returns a superset of the old output dict.
    """
    return _PARSER_INSTANCE.parse(text)


# ============================================================================
# TESTS
# ============================================================================

def run_tests():
    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name}  {detail}")

    parser = UtteranceParser()

    print("\n=== UtteranceParser Tests ===\n")

    # ---- Binding: "ok so what if" ----
    print("Phrase binding:")
    r = parser.parse("ok so what if we tried something different")
    signals = [s[0] for s in r['pragmatic_signals']]
    # Should detect acknowledgment (ok so), consequence (so), hypothesis (what if)
    check("'ok so' → acknowledgment signal", 'acknowledgment' in signals, str(signals))
    check("'what if' → hypothesis signal", 'hypothesis' in signals, str(signals))
    check("is_hypothetical=True", r['is_hypothetical'])
    check("frame=hypothetical", r['frame'] == 'hypothetical')
    check("'different' kept as topic word", 'different' in r['topic_words'], r['topic_words'])

    # ---- Binding: "but like i mean" ----
    print("\nClarification binding:")
    r2 = parser.parse("but like i mean running in terms of operating")
    signals2 = [s[0] for s in r2['pragmatic_signals']]
    check("'but' → contrast", 'contrast' in signals2)
    check("'i mean' → clarification", 'clarification' in signals2)
    check("is_clarification=True", r2['is_clarification'])
    check("'running' kept as topic word", 'running' in r2['topic_words'], r2['topic_words'])
    check("'operating' kept as topic word", 'operating' in r2['topic_words'], r2['topic_words'])
    check("query_type=clarification", r2['query_type'] == 'clarification')

    # ---- Binding: "just wondering" ----
    print("\nMinimization binding:")
    r3 = parser.parse("just wondering how it all works")
    signals3 = [s[0] for s in r3['pragmatic_signals']]
    check("'just' → minimization", 'minimization' in signals3)
    check("stance=tentative or curious", r3['stance'] in ('tentative', 'curious', 'speculative'))

    # ---- Experience question ----
    print("\nExperience question:")
    r4 = parser.parse("how does it feel running off my phone")
    check("is_experiential=True", r4['is_experiential'])
    check("frame=experiential", r4['frame'] == 'experiential')
    check("query_type=experience", r4['query_type'] == 'experience')
    check("no search needed for experience", r4['search_query'] in ('', 'running phone', 'running'))

    # ---- "yeah but" — challenging ----
    print("\nChallenging frame:")
    r5 = parser.parse("yeah but that's not what i meant")
    signals5 = [s[0] for s in r5['pragmatic_signals']]
    check("'yeah' → acknowledgment", 'acknowledgment' in signals5)
    check("'but' → contrast", 'contrast' in signals5)
    check("frame=challenging", r5['frame'] == 'challenging')
    check("stance=challenging", r5['stance'] == 'challenging')

    # ---- Hypothesis detection ----
    print("\nHypothesis detection:")
    r6 = parser.parse("what if she could learn from every conversation")
    check("is_hypothetical=True for 'what if'", r6['is_hypothetical'])
    check("topic words include 'learn' and 'conversation'",
          'learn' in r6['topic_words'] or 'conversation' in r6['topic_words'], r6['topic_words'])

    # ---- Topic preservation ----
    print("\nTopic word preservation:")
    r7 = parser.parse("ok so what exactly is machine learning anyway")
    check("'machine' kept", 'machine' in r7['topic_words'], r7['topic_words'])
    check("'learning' kept", 'learning' in r7['topic_words'], r7['topic_words'])
    # Old system would strip ok, so, what, exactly, is, anyway = "machine learning"
    # New system keeps ok→acknowledgment, so→consequence, what→inquiry, exactly→emphasis
    # and keeps machine+learning as topic words

    # ---- Backward compatibility ----
    print("\nBackward compatibility:")
    r8 = parser.parse("what is the capital of France")
    check("topic present", bool(r8['topic']))
    check("query_type present", bool(r8['query_type']))
    check("search_query present", bool(r8['search_query']))
    check("entities contains 'France'", 'France' in r8['entities'], r8['entities'])

    # ---- Full phrase construction ----
    print("\nFull phrase:")
    r9 = parser.parse("like i said the weather in Ohio is really unpredictable")
    check("is_callback detected", r9['is_callback'])
    check("'weather' in topic_words", 'weather' in r9['topic_words'], r9['topic_words'])
    check("'Ohio' in entities", 'Ohio' in r9['entities'], r9['entities'])

    # ---- Negation detection ----
    print("\nNegation:")
    r10 = parser.parse("that's not what i was asking")
    check("negated=True", r10['negated'])
    check("is_clarification=True (i was asking...)", r10['is_clarification'] or
          r10['frame'] in ('clarifying', 'contrastive'))

    print(f"\n=== Results: {passed} passed, {failed} failed ===\n")
    return failed == 0


if __name__ == "__main__":
    run_tests()
