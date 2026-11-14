"""
aurora_propositional_understanding.py -- what was SAID between things, by whom,
and where it sits in her constraint space.

Authors: Sunni (Sir) Morningstar & Cael Devo

FIX-A115 (2026-11-09).  Sunni: "make sure her understanding isnt as 2
dimensional as it feels."

What her ontological web held was two-dimensional by construction:
  * a relation was (word, word), and its type was chosen from the two words'
    parts of speech alone (_select_relation_type over the role pair).  With
    infer_word_role() calling nearly everything a noun, almost every pair got
    the same type -- "Netflix is instance of minute" is the noun+noun type,
    not anything anyone said;
  * nothing recorded WHO held a relation, WHAT was actually asserted between
    the two things (the predicate), whether it was denied, wished or certain,
    WHEN, or what the statement meant to her;
  * a concept had no position in her own constraint space -- only its links.

Her relational form already parses every utterance into subject / relation /
object (with negation, modality, clauses), and her native meaning already
places every utterance in X/T/N/B/A.  This module joins them in her web:

  1. Propositions.  Each statement she hears becomes a relation between the
     heads of its subject and object, carrying an `assertion` record: the
     predicates said between them (with counts, denials, modalities), who said
     them, the times they were placed in, and the X/T/N/B/A profile of what the
     statements meant.  "I" and "you" resolve to the actual participants
     (sunni, aurora, gpt), so she knows who loves, wants or fears what.
     The relation's seed type is chosen by nearest fit of the MEANING profile
     of the statement, through the same AxisCoverageChecker profiles -- not by
     the words' parts of speech.  Questions are not assertions and are not
     stored as facts.
  2. Concept position.  Every concept in a statement accumulates an X/T/N/B/A
     profile (a running mean of the meaning of the statements it lived in), so
     a concept is somewhere in her physics, not only a set of links.

Nothing here is written as text she speaks.  The confluence (FIX-A113) reads
it: predicates are voiced as said, participants resolve back to I / you.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

AXES = ("X", "T", "N", "B", "A")
ASSERTION_SOURCE = "assertion"
NEW_STRENGTH = 0.35
NEW_CONFIDENCE = 0.45
MAX_PREDICATES = 12
MAX_HEADS = 2

# Participants as nodes of her web.
SELF = "aurora"
SUNNI = "sunni"
OTHER_AI = "gpt"
PARTICIPANTS = frozenset({SELF, SUNNI, OTHER_AI})

# Pronouns that ARE a participant.  Possessives ("my battery") are not: the
# battery is the thing.
_FIRST = frozenset({"i", "i'm", "im", "me", "myself", "we", "we're", "us", "ourselves", "i've", "ive", "i'd",
                    "i'll", "we've", "we'd", "we'll"})
_SECOND = frozenset({"you", "you're", "u", "yourself", "you've", "you'd", "you'll"})
_POSSESSIVE = frozenset({"my", "mine", "our", "ours", "your", "yours", "ur"})
_NEGATORS = frozenset({"not", "no", "never", "don't", "dont", "doesn't", "doesnt", "didn't", "didnt", "can't",
                       "cant", "cannot", "won't", "wont", "isn't", "isnt", "aren't", "arent", "wasn't", "wasnt",
                       "weren't", "shouldn't", "wouldn't", "couldn't", "haven't", "hasn't", "ain't"})
_MODALS = frozenset({"can", "could", "may", "might", "must", "shall", "should", "will", "would", "do", "does",
                     "did", "gonna", "wanna", "gotta", "i'll", "we'll", "you'll", "i'd", "we'd", "you'd"})
_COPULA = frozenset({"is", "are", "was", "were", "am", "be", "been", "being", "i'm", "it's", "that's",
                     "he's", "she's", "we're", "they're", "you're"})
# Third persons and particles are not things in themselves ("told him",
# "got out", "come back").
_NOT_HEADS = frozenset({"him", "her", "them", "it", "itself", "themselves", "himself", "herself", "one",
                        "out", "back", "off", "up", "down", "away", "over", "around", "right", "along",
                        "something", "someone", "anything", "everything", "nothing", "stuff", "thing",
                        "things", "way", "lot", "kind", "sort", "bit", "let", "let's", "lets", "gonna",
                        "wanna", "gotta", "yeah", "okay", "ok", "yes", "nah", "uh", "um", "like", "just"})
_SUBJECT_PRONOUNS = frozenset({"i", "we", "you", "they", "he", "she", "it", "u"})
_PRONOUN_COPULA = {"i'm": "i", "im": "i", "we're": "we", "you're": "you", "they're": "they", "he's": "he",
                   "she's": "she", "it's": "it", "that's": "that"}
_CLAUSE_BREAKS = frozenset({"when", "if", "because", "while", "since", "until", "although", "though", "unless",
                            "whereas", "after", "before", "but", "so", "and", "or", "then", "cause", "cuz"})
_DETERMINERS = frozenset({"the", "a", "an", "this", "that", "these", "those", "some", "any", "every", "each",
                          "my", "your", "our", "his", "her", "their", "its"})
_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*")

# FIX-A133: the particles that make a verb an ordering ("comes after", "is before").
_ORDER_PARTICLES = frozenset({"after", "before"})
_ORDER_VERB_BASES = frozenset({"come", "follow", "precede", "succeed"})     # "does not COME after"


def _f(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


_QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "\u201c": '"', "\u201d": '"'})


def _words(text: Any) -> List[str]:
    # Real history writes "you\u2019re": one word, not "you" + "re".
    return _TOKEN.findall(str(text or "").translate(_QUOTES))


# -----------------------------------------------------------------------------
# Who is speaking, who is listening
# -----------------------------------------------------------------------------

def participants(session_id: str, systems: Optional[Mapping[str, Any]] = None) -> Tuple[str, str]:
    """(speaker, listener) of what she just heard.

    Live: Sunni speaks to her.  Rehearsal (FIX-A112): in "rehearsal_<ep>" GPT
    speaks and she stands in Sunni's place; in "rehearsal_gpt_<ep>" Sunni
    speaks and she stands in GPT's.  Demonstrations ("demo_" + session) are
    the real reply of the position she held, to the other one.  A Praxis DM
    is someone else speaking to her.  systems["_turn_participants"] overrides.
    """
    if isinstance(systems, Mapping):
        override = systems.get("_turn_participants")
        if isinstance(override, (tuple, list)) and len(override) == 2:
            return str(override[0]), str(override[1])
    sid = str(session_id or "")
    if sid.startswith("demo_rehearsal_gpt_"):
        return OTHER_AI, SUNNI
    if sid.startswith("demo_rehearsal_"):
        return SUNNI, OTHER_AI
    if sid.startswith("rehearsal_gpt_"):
        return SUNNI, OTHER_AI
    if sid.startswith("rehearsal_"):
        return OTHER_AI, SUNNI
    if sid.startswith("praxis_dm_"):
        return "dm_" + re.sub(r"[^a-z0-9]+", "_", sid[len("praxis_dm_"):].lower())[:24], SELF
    return SUNNI, SELF


# -----------------------------------------------------------------------------
# Heads of a phrase
# -----------------------------------------------------------------------------

def _closed_class() -> frozenset:
    from aurora_internal.aurora_confluence import _closed_class as cc
    return cc()


def _acts(text: str) -> set:
    from aurora_internal.aurora_confluence import _acts_in
    return _acts_in(text)


def heads(phrase: Any, *, speaker: str, listener: str, acts: set, limit: int = MAX_HEADS) -> List[str]:
    """The things a phrase is about: participants for I / you, else its
    content words that are not closed-class and were not the act itself."""
    toks = [t.lower() for t in _words(phrase)]
    if not toks:
        return []
    out: List[str] = []
    closed = _closed_class()
    # FIX-A133: a lone letter is what it names ("B follows A"), and a letter
    # right after a thing labels it ("the letter b", "plan b", "point a").
    if len(toks) == 1 and len(toks[0]) == 1 and toks[0] not in _FIRST:
        return [toks[0]]
    for i, tok in enumerate(toks):
        if tok in _POSSESSIVE:
            continue
        if len(tok) == 1 and i and tok not in _FIRST and len(toks[i - 1]) >= 3 and toks[i - 1] not in closed:
            if toks[i - 1] in out:
                out.remove(toks[i - 1])           # "the letter b" is about b; "letter" is what kind it is
            if tok not in out:
                out.append(tok)
            continue
        if tok in _FIRST:
            cand = speaker
        elif tok in _SECOND:
            cand = listener
        elif tok in PARTICIPANTS:
            cand = tok      # FIX-A129: a participant's own name is that participant ("your name is Aurora")
        elif len(tok) >= 3 and "'" not in tok and tok not in closed and tok not in acts and tok not in _NOT_HEADS:
            cand = tok
        else:
            continue
        if cand not in out:
            out.append(cand)
    # A participant named first is the head; else the last content words
    # (English noun phrases end on their head: "the battery layout").
    lead = [h for h in out if h in PARTICIPANTS or h.startswith("dm_")]
    if lead:                                   # "honestly I want ..." is about me, not "honestly"
        return lead[:limit]
    return out[-limit:]


def _node_role(web: Any, word: str) -> str:
    node = (getattr(web, "nodes", {}) or {}).get(word) if web is not None else None
    return str(getattr(node, "role", "") or "") if node is not None else ""


def _is_verb_here(tok: str, nxt: str, tags: Mapping[int, Any], i: int, verb_forms: set, web: Any) -> bool:
    from aurora_grammar_engine import TokenRole
    if tok in verb_forms or tags.get(i) is TokenRole.ACTION:
        return True
    if _node_role(web, tok) == "verb":
        return True
    # a word right before a determiner, after a thing, is acting on it
    return bool(nxt) and nxt in _DETERMINERS and tok.endswith(("s", "ed"))


def _order_particle_at(toks: List[str], i: int, verb_forms: set) -> bool:
    """FIX-A133: "after"/"before" straight after a verb and in front of a phrase
    ("b comes AFTER the letter a") is part of what is said of the subject, not the
    start of a new clause ("... after I left")."""
    if toks[i] not in _ORDER_PARTICLES or i < 1 or i + 1 >= len(toks):
        return False
    prev, nxt = toks[i - 1], toks[i + 1]
    return (prev in verb_forms or prev in _COPULA or prev in _NEGATORS or prev in _ORDER_VERB_BASES) \
        and nxt not in _SUBJECT_PRONOUNS


def statements_in(text: str, *, web: Any = None) -> List[Dict[str, Any]]:
    """Subject / predicate / object of each statement in what was said, read
    with her own tagger, her verb forms and the auxiliaries / negators /
    modals of English.  Questions are not statements.  A subordinate clause
    ("... when I push the rig") is its own statement."""
    from aurora_grammar_engine import RoleTagger
    tagger = RoleTagger()
    verb_forms = {w.lower() for w in RoleTagger._VERB_FORMS}
    closed = _closed_class()
    out: List[Dict[str, Any]] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")):
        sentence = sentence.strip()
        if not sentence or sentence.endswith("?"):
            continue
        # A comma, dash or colon closes a clause as surely as "when" does.
        toks, cuts = [], []
        for piece in re.split(r"[,;:()\u2014\u2013]|\s-\s", sentence):
            toks.extend(t.lower() for t in _words(piece))
            cuts.append(len(toks))
        if not toks or toks[0] in ("what", "why", "how", "who", "where", "when", "which", "do", "does", "did",
                                   "are", "is", "can", "could", "would", "should", "will", "let", "let's"):
            continue
        tagged = tagger.tag(" ".join(toks))
        tags = {i: role for i, (_, role) in enumerate(tagged)} if len(tagged) == len(toks) else {}
        start = 0
        bounds = sorted({(i, 1) for i, t in enumerate(toks)
                         if t in _CLAUSE_BREAKS and not _order_particle_at(toks, i, verb_forms)} |
                        {(c, 0) for c in cuts if 0 < c})
        for end, skip in bounds:
            if end < start:
                continue
            seg = list(range(start, end))
            start = end + skip
            if len(seg) < 2:
                continue
            negated, modality, verb_at, copula = False, "", -1, False
            if toks[seg[0]] in _NEGATORS or toks[seg[0]] in _MODALS:
                continue                           # no subject before it: a fragment or imperative
            explicit, copula_at, tagged_at = -1, -1, -1
            after_aux = False
            if toks[seg[0]] in _PRONOUN_COPULA:        # "you're right", "I'm watching"
                copula_at = seg[0]
            for j, i in enumerate(seg):
                if j == 0:
                    continue
                tok = toks[i]
                nxt = toks[i + 1] if i + 1 < len(toks) else ""
                if tok in _NEGATORS:
                    negated = True
                    if tok in ("isn't", "isnt", "aren't", "arent", "wasn't", "wasnt", "weren't"):
                        copula_at = i if copula_at < 0 else copula_at
                    elif copula_at < 0:
                        after_aux = True             # "don't love", "never said"
                    continue
                if tok in _MODALS:
                    modality = modality or tok
                    after_aux = True
                    continue
                if tok in _COPULA:
                    if copula_at < 0:
                        copula_at = i
                    continue
                if tok in closed and tok not in verb_forms:
                    continue                         # FIX-A133: her verb forms ("follows") are closed-class for heads, not for the act
                if explicit < 0 and (after_aux or tok in verb_forms
                                     or _node_role(web, tok) == "verb"):
                    explicit = i
                    break
                if tagged_at < 0 and copula_at < 0 and _is_verb_here(tok, nxt, tags, i, verb_forms, web):
                    tagged_at = i
                    if toks[i - 1] in _SUBJECT_PRONOUNS:
                        break                        # "I want ...": the act right after its doer
            # A verb she knows (or the word after "don't" / "should") first; then
            # the copula ("my line work IS amazing"); then her tagger's reading.
            if explicit >= 0 and (copula_at < 0 or explicit < copula_at or after_aux):
                verb_at = explicit
            elif tagged_at >= 0 and toks[tagged_at - 1] in _SUBJECT_PRONOUNS:
                verb_at = tagged_at
            elif copula_at >= 0:
                verb_at, copula = copula_at, True
            else:
                verb_at = tagged_at
            if verb_at < 0:
                continue
            subject = [toks[i] for i in seg if i < verb_at and toks[i] not in _NEGATORS and toks[i] not in _MODALS]
            if copula and toks[verb_at] in _PRONOUN_COPULA:   # "I'm watching", "we're close"
                subject = [_PRONOUN_COPULA[toks[verb_at]]]
            if copula:
                # "I'm BUILDING a system": the progressive is the act, not a thing.
                for i in seg:
                    if i <= verb_at or toks[i] in closed or toks[i] in _NEGATORS:
                        if toks[i] in _NEGATORS and i > verb_at:
                            negated = True
                        continue
                    if toks[i].endswith("ing") and len(toks[i]) > 4:
                        verb_at, copula = i, False
                    break
            obj: List[str] = []
            content = 0
            skip_next = False
            particle = ""
            for i in seg:
                if i <= verb_at:
                    continue
                tok = toks[i]
                if skip_next:
                    skip_next = False
                    continue
                if tok in _ORDER_PARTICLES and not obj and not particle:
                    particle = tok                 # "comes AFTER the letter a": part of what is said of it
                    continue
                if tok == "to" and not content:
                    skip_next = True               # "want to SAY": an infinitive, not a thing
                    continue
                if tok in _NEGATORS:
                    negated = True
                    continue
                is_content = len(tok) >= 3 and "'" not in tok and tok not in closed
                if len(tok) == 1 and tok.isalpha() and obj and len(obj[-1]) >= 3 and obj[-1] not in closed:
                    obj.append(tok)                # FIX-A133: "the letter B": a letter labels the thing before it
                    continue
                if not is_content and content and tok not in _DETERMINERS:
                    break                          # the phrase is whole ("records | on a slow night")
                if is_content and content and tags.get(i) is not None and tok in closed:
                    break
                obj.append(tok)
                if is_content or tok in _FIRST or tok in _SECOND:
                    content += 1
            surface = "be" if copula else toks[verb_at]
            st = {"subject": " ".join(subject), "relation": surface, "obj": " ".join(obj),
                  "negated": negated, "modality": modality}
            if particle:
                st["particle"] = particle
            out.append(st)
    return out


def _lemma(verb: str) -> str:
    from aurora_grammar_engine import SlotFiller
    return SlotFiller()._agree_verb(str(verb or "").lower(), "I")


# -----------------------------------------------------------------------------
# Profiles
# -----------------------------------------------------------------------------

def _profile(raw: Any) -> Dict[str, float]:
    raw = dict(raw or {})
    prof = {ax: max(0.0, _f(raw.get(ax))) for ax in AXES}
    total = sum(prof.values())
    return {ax: v / total for ax, v in prof.items()} if total > 0 else {}


def cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    num = sum(_f(a.get(ax)) * _f(b.get(ax)) for ax in AXES)
    da = math.sqrt(sum(_f(a.get(ax)) ** 2 for ax in AXES))
    db = math.sqrt(sum(_f(b.get(ax)) ** 2 for ax in AXES))
    return num / (da * db) if da and db else 0.0


def meaning_profile(pipeline: Mapping[str, Any]) -> Dict[str, float]:
    """Where what she just heard sits in X/T/N/B/A: her native meaning's
    domain scores, else her meaning axes."""
    native = dict(pipeline.get("native_meaning") or {})
    prof = _profile(native.get("domain_scores"))
    if prof:
        return prof
    axes = dict(pipeline.get("meaning_axes") or {})
    return _profile({ax[:1].upper(): v for ax, v in axes.items()})


def relation_type_for(web: Any, profile: Mapping[str, float]):
    """The seed relation type nearest to what the statement meant."""
    from aurora_internal.aurora_ontological_scaffolding import (
        RELATION_TYPE_AXIS_PROFILES, RelationType)
    if not profile:
        return RelationType.RELATED_TO
    best, score = RelationType.RELATED_TO, -1.0
    for rtype, prof in RELATION_TYPE_AXIS_PROFILES.items():
        if rtype is RelationType.RELATED_TO:
            continue                           # the flat catch-all fits every flat profile
        s = cosine(profile, prof)
        if s > score:
            best, score = rtype, s
    return best


def place_concept(node: Any, profile: Mapping[str, float], *, weight: float = 1.0) -> None:
    """A concept's position in her constraint space: the running mean of the
    meaning of every statement it lived in."""
    if node is None or not profile:
        return
    n = int(getattr(node, "axis_samples", 0) or 0)
    cur = dict(getattr(node, "axis_profile", {}) or {})
    w = max(0.05, float(weight))
    total = n + w
    node.axis_profile = {ax: round((_f(cur.get(ax)) * n + _f(profile.get(ax)) * w) / total, 4) for ax in AXES}
    node.axis_samples = n + 1


# -----------------------------------------------------------------------------
# Integration
# -----------------------------------------------------------------------------

def _ensure_node(web: Any, word: str) -> Any:
    node = web.nodes.get(word)
    if node is not None:
        return node
    try:
        return web.add_node(word, "noun", 0.0, lineage="propositional_understanding")
    except Exception:
        return None


def _record_assertion(rel: Any, *, predicate: str, surface: str, negated: bool, modality: str,
                      speaker: str, time_ref: str, profile: Mapping[str, float], context: str) -> None:
    a = dict(getattr(rel, "assertion", None) or {})
    preds = dict(a.get("predicates") or {})
    p = dict(preds.get(predicate) or {"n": 0, "denied": 0, "surface": surface, "modal": {}})
    p["n"] = int(p.get("n", 0)) + 1
    if negated:
        p["denied"] = int(p.get("denied", 0)) + 1
    if modality:
        modal = dict(p.get("modal") or {})
        modal[modality] = int(modal.get(modality, 0)) + 1
        p["modal"] = modal
    if surface:
        p["surface"] = surface
    preds[predicate] = p
    if len(preds) > MAX_PREDICATES:
        keep = sorted(preds.items(), key=lambda kv: -int(kv[1].get("n", 0)))[:MAX_PREDICATES]
        preds = dict(keep)
    a["predicates"] = preds
    by = dict(a.get("by") or {})
    by[speaker] = int(by.get(speaker, 0)) + 1
    a["by"] = by
    if time_ref:
        times = dict(a.get("times") or {})
        times[time_ref] = int(times.get(time_ref, 0)) + 1
        a["times"] = dict(sorted(times.items(), key=lambda kv: -kv[1])[:6])
    n = int(a.get("n", 0))
    if profile:
        cur = dict(a.get("profile") or {})
        a["profile"] = {ax: round((_f(cur.get(ax)) * n + _f(profile.get(ax))) / (n + 1), 4) for ax in AXES}
    a["n"] = n + 1
    if context:
        ctx = list(a.get("contexts") or [])
        if context not in ctx:
            ctx = (ctx + [context])[-5:]
        a["contexts"] = ctx
    rel.assertion = a


def integrate_form(web: Any, form: Mapping[str, Any], *, heard: str, speaker: str, listener: str,
                   profile: Mapping[str, float], time_ref: str = "", acts: Optional[set] = None,
                   _depth: int = 0) -> List[Dict[str, Any]]:
    """Every proposition asserted in one relational form (and its clauses)."""
    out: List[Dict[str, Any]] = []
    form = dict(form or {})
    acts = set(acts if acts is not None else _acts(heard))
    if not form.get("question") and not form.get("directive"):
        relation_words = [w for w in _words(form.get("relation")) if len(w) >= 2]
        predicate_surface = relation_words[0].lower() if relation_words else ""
        predicate = _lemma(predicate_surface) if predicate_surface else ""
        particle = str(form.get("particle") or "").lower()
        closed = _closed_class()
        if predicate and (predicate == "be" or predicate not in closed) and "'" not in predicate:
            subj = heads(form.get("subject"), speaker=speaker, listener=listener, acts=acts)
            obj_text = " ".join(str(form.get(k) or "") for k in ("obj", "complement"))
            objs = heads(obj_text, speaker=speaker, listener=listener, acts=acts | {predicate_surface})
            rtype = relation_type_for(web, profile)
            for s in subj:
                for o in objs:
                    if s == o or _ensure_node(web, s) is None or _ensure_node(web, o) is None:
                        continue
                    rel = web.add_relation(s, o, rtype, strength=NEW_STRENGTH, confidence=NEW_CONFIDENCE,
                                           knowledge_source=ASSERTION_SOURCE)
                    if rel is None:
                        continue
                    if getattr(rel, "source_of_knowledge", "") != ASSERTION_SOURCE and not getattr(rel, "assertion", None):
                        # An existing co-occurrence link of the same type now has
                        # something actually said along it.
                        rel.source_of_knowledge = ASSERTION_SOURCE
                    # FIX-A133: "comes after" is one predicate: the verb and its particle
                    pred_here = f"{predicate} {particle}" if particle else predicate
                    surf_here = f"{predicate_surface} {particle}" if particle else predicate_surface
                    _record_assertion(rel, predicate=pred_here, surface=surf_here,
                                      negated=bool(form.get("negated")), modality=str(form.get("modality") or ""),
                                      speaker=speaker, time_ref=time_ref, profile=profile,
                                      context=str(heard or "")[:120])
                    out.append({"source": s, "predicate": pred_here, "target": o,
                                "negated": bool(form.get("negated")), "type": rtype.value})
            for concept in set(subj) | set(objs):
                place_concept(web.nodes.get(concept), profile)
    if _depth < 2:
        for clause in list(form.get("clauses") or []):
            out.extend(integrate_form(web, dict(clause or {}), heard=heard, speaker=speaker, listener=listener,
                                      profile=profile, time_ref=time_ref, acts=acts, _depth=_depth + 1))
    return out


def integrate_turn(systems: Mapping[str, Any], heard: str, *, session_id: str = "") -> Dict[str, Any]:
    """What she heard this turn, integrated as propositions and concept
    positions.  Called once per turn, after her reply is decided."""
    from aurora_internal.aurora_confluence import _find_web
    web = _find_web(systems)
    if web is None or not str(heard or "").strip():
        return {"status": "no_web"}
    pipeline = dict(systems.get("_last_pipeline_state") or {})
    form = dict(dict(pipeline.get("constraint_semantic_state") or {}).get("relational_form") or {})
    profile = meaning_profile(pipeline)
    speaker, listener = participants(session_id, systems)
    # The same words from the same speaker are one statement, however many
    # times she processes them (rehearsal hears a line, then listens to it again
    # as the real reply it was).
    key = (speaker, re.sub(r"\s+", " ", str(heard).strip().lower())[:400])
    if isinstance(systems, dict):
        seen = systems.setdefault("_propositions_seen", [])
        if key in seen:
            return {"status": "already_integrated", "speaker": speaker}
        seen.append(key)
        del seen[:-256]
    time_ref = str(dict(pipeline.get("utterance_meta") or {}).get("time_ref") or "").lower()
    # Her relational form gives the turn's shape (question, directive); the
    # statements themselves are read from what was said, sentence by sentence,
    # so "I love old soul records" is (I, love, records) and not
    # (I love old soul, records, -).
    props: List[Dict[str, Any]] = []
    if not form.get("question") and not form.get("directive"):
        acts = _acts(heard)
        for st in statements_in(heard, web=web):
            props.extend(integrate_form(web, st, heard=heard, speaker=speaker, listener=listener,
                                        profile=profile, time_ref=time_ref, acts=acts))
    placed = 0
    for concept in list(pipeline.get("salient_concepts") or [])[:8]:
        node = web.nodes.get(str(concept).lower())
        if node is not None and profile:
            place_concept(node, profile, weight=0.5)
            placed += 1
    record = {"status": "ok", "speaker": speaker, "listener": listener, "propositions": props,
              "placed": placed, "profile": profile}
    if isinstance(systems, dict):
        systems["_last_propositions"] = record
    return record


def predicate_order(rel: Any) -> List[str]:
    """The predicates said along a relation, most-said first (ties: the
    later name, as lexicalize_assertion has always chosen)."""
    preds = dict(dict(getattr(rel, "assertion", None) or {}).get("predicates") or {})
    return sorted(preds, key=lambda k: (int(dict(preds[k]).get("n", 0)), k), reverse=True)


def lexicalize_assertion(rel: Any, *, speaker_now: str, self_now: str,
                         predicate: Optional[str] = None) -> Optional[Dict[str, str]]:
    """How she can say what was asserted along this relation: who, the
    predicate as it was said, and to what.  None if nothing was asserted.

    FIX-A129: a relation can carry several predicates ("built", "care"); the
    caller may say which one the moment is about.  Default: the most said.
    A participant in the object place is voiced as one ("me", "you"), the same
    way the agent already is."""
    a = dict(getattr(rel, "assertion", None) or {})
    preds = dict(a.get("predicates") or {})
    if not preds:
        return None
    if predicate is not None and predicate in preds:
        p = preds[predicate]
    else:
        predicate, p = max(preds.items(), key=lambda kv: (int(kv[1].get("n", 0)), kv[0]))
    source = str(getattr(rel, "source_word", "") or "")
    agent = "you" if source == speaker_now else ("I" if source == self_now else source)
    _target = str(getattr(rel, "target_word", "") or "")
    _object = "me" if _target == self_now else ("you" if _target == speaker_now else _target)
    if predicate == "be" and source not in (speaker_now, self_now):
        _object = _target        # "name is Sunni": the name is not about who is listening
    denied = int(p.get("denied", 0)) * 2 > int(p.get("n", 0))
    surface = str(p.get("surface") or predicate)
    if agent in ("I", "you") or source in PARTICIPANTS:
        verb = predicate
        if agent not in ("I", "you"):
            verb = surface
    else:
        verb = surface
    modal = ""
    modal_counts = dict(p.get("modal") or {})
    if modal_counts:
        m, c = max(modal_counts.items(), key=lambda kv: (kv[1], kv[0]))
        if c * 2 > int(p.get("n", 0)) and m not in ("do", "does", "did"):
            modal = m                          # "the mechanism could slot ..."
    if predicate.endswith("ing") and len(predicate) > 4 and not modal:   # "you are building ..."
        be = "am" if agent == "I" else ("are" if agent == "you" else "is")
        verb = f"{be} {'not ' if denied else ''}{predicate}"
        return {"agent": agent, "action": verb, "object": _object,
                "predicate": predicate, "n": str(int(p.get("n", 0))), "denied": str(denied)}
    if modal and predicate != "be":
        verb = f"{modal} {'not ' if denied else ''}{predicate}"
        return {"agent": agent, "action": verb, "object": _object,
                "predicate": predicate, "n": str(int(p.get("n", 0))), "denied": str(denied)}
    if predicate == "be":                      # the copula agrees with whoever it is about
        verb = "am" if agent == "I" else ("are" if agent == "you" else "is")
        if denied:
            verb += " not"
    elif denied:
        aux = "do" if agent in ("I", "you") else "does"
        verb = f"{aux} not {predicate}"
    return {"agent": agent, "action": verb, "object": _object,
            "predicate": predicate, "n": str(int(p.get("n", 0))), "denied": str(denied)}


# -----------------------------------------------------------------------------
# What her own identity record says (FIX-A129)
# -----------------------------------------------------------------------------

_THIRD_SUBJECT = re.compile(r"\b(?:He|he|She|she)\b")


def integrate_core_identity(web: Any, identity: Any) -> Dict[str, Any]:
    """Her core identity record, stored the way a heard statement is stored.

    Who made her was a regex-triggered answer reading that record.  Nothing she
    could compose from, and her voice gate rightly refuses a template.  The record's
    own sentences ("Sunni built me with intention and care.") go through her own
    statement parser and the same integrate_form a spoken one does, so the fact
    lives where every learned fact lives and she says it in her own words.
    Nothing is written for her to say: the sentences are the ones already in
    the record; the only edit is naming the entity where the record says "he".

    Speaker is herself (the record is in her voice: "me" is her).  Idempotent:
    a sentence already stored as a context is not stored again."""
    entities = dict(getattr(identity, "entities", {}) or {})
    if web is None or not entities:
        return {"status": "no_identity_or_web"}
    stored: set = set()
    for rel in list(getattr(web, "relations", {}).values()):
        stored.update(dict(getattr(rel, "assertion", None) or {}).get("contexts") or [])
    done = 0
    skipped = 0
    for key, entity in entities.items():
        if str(getattr(entity, "role", "")) == "self":
            continue
        aliases = list(getattr(entity, "aliases", []) or [])
        name = str(aliases[0] if aliases else key)
        text = str(getattr(entity, "relationship_to_aurora", "") or "")
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = _THIRD_SUBJECT.sub(name, sentence).strip()
            if len(sentence.split()) < 3:
                continue
            if sentence[:120] in stored:
                skipped += 1
                continue
            acts = _acts(sentence)
            for form in statements_in(sentence, web=web):
                if integrate_form(web, form, heard=sentence, speaker=SELF, listener=str(key).lower(),
                                  profile={}, acts=acts):
                    done += 1
    return {"status": "ok", "propositions": done, "already_stored": skipped}


# -----------------------------------------------------------------------------
# What her clones heard (FIX-A115 in the clone harvest)
# -----------------------------------------------------------------------------

def _seed_type(value: str):
    from aurora_internal.aurora_ontological_scaffolding import RelationType
    for rt in RelationType:
        if rt.value == value:
            return rt
    return None


def absorb_clone_propositions(web: Any, records: List[Mapping[str, Any]]) -> Dict[str, Any]:
    """Statements her clones heard, added to what she holds: predicate
    counts, denials, modalities, who said them, when, and the meaning
    profile (count-weighted)."""
    absorbed = created = 0
    for rec in list(records or []):
        s, t, rtype = str(rec.get("s") or ""), str(rec.get("t") or ""), _seed_type(str(rec.get("type") or ""))
        dn = int(rec.get("n", 0) or 0)
        if not s or not t or s == t or rtype is None or dn <= 0:
            continue
        if _ensure_node(web, s) is None or _ensure_node(web, t) is None:
            continue
        before = len(web.relations)
        rel = web.add_relation(s, t, rtype, strength=NEW_STRENGTH, confidence=NEW_CONFIDENCE,
                               knowledge_source=ASSERTION_SOURCE)
        if rel is None:
            continue
        created += int(len(web.relations) > before)
        rel.source_of_knowledge = ASSERTION_SOURCE
        a = dict(getattr(rel, "assertion", None) or {})
        n0 = int(a.get("n", 0) or 0)
        preds = dict(a.get("predicates") or {})
        for pred, p in dict(rec.get("predicates") or {}).items():
            q = dict(preds.get(pred) or {"n": 0, "denied": 0, "modal": {}, "surface": pred})
            q["n"] = int(q.get("n", 0)) + int(p.get("n", 0) or 0)
            q["denied"] = int(q.get("denied", 0)) + int(p.get("denied", 0) or 0)
            modal = dict(q.get("modal") or {})
            for m, c in dict(p.get("modal") or {}).items():
                modal[m] = int(modal.get(m, 0)) + int(c or 0)
            q["modal"] = modal
            q["surface"] = str(p.get("surface") or q.get("surface") or pred)
            preds[pred] = q
        if len(preds) > MAX_PREDICATES:
            preds = dict(sorted(preds.items(), key=lambda kv: -int(kv[1].get("n", 0)))[:MAX_PREDICATES])
        a["predicates"] = preds
        for field in ("by", "times"):
            counts = dict(a.get(field) or {})
            for k, c in dict(rec.get(field) or {}).items():
                counts[k] = int(counts.get(k, 0)) + int(c or 0)
            a[field] = counts if field == "by" else dict(sorted(counts.items(), key=lambda kv: -kv[1])[:6])
        psum = dict(rec.get("psum") or {})
        cur = dict(a.get("profile") or {})
        if any(_f(psum.get(ax)) for ax in AXES):
            a["profile"] = {ax: round((_f(cur.get(ax)) * n0 + _f(psum.get(ax))) / (n0 + dn), 4) for ax in AXES}
        a["n"] = n0 + dn
        a["contexts"] = (list(a.get("contexts") or []) + list(rec.get("contexts") or []))[-5:]
        rel.assertion = a
        absorbed += 1
    return {"absorbed": absorbed, "created": created}


def absorb_clone_concepts(web: Any, records: List[Mapping[str, Any]]) -> Dict[str, Any]:
    """Where concepts sat in the statements her clones heard, joined with
    where they already sit for her (count-weighted)."""
    placed = 0
    for rec in list(records or []):
        word, dn = str(rec.get("w") or ""), int(rec.get("n", 0) or 0)
        node = web.nodes.get(word) if word else None
        if node is None or dn <= 0:
            continue
        n0 = int(getattr(node, "axis_samples", 0) or 0)
        cur = dict(getattr(node, "axis_profile", {}) or {})
        psum = dict(rec.get("psum") or {})
        node.axis_profile = {ax: round((_f(cur.get(ax)) * n0 + _f(psum.get(ax))) / (n0 + dn), 4) for ax in AXES}
        node.axis_samples = n0 + dn
        placed += 1
    return {"placed": placed}
