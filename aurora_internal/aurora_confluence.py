"""
aurora_confluence.py -- every system that touched the turn feeds what she says;
her live abilities decide how.

Authors: Sunni (Sir) Morningstar & Cael Devo

FIX-A113 (2026-11-09).  Until now only one system reached her voice: the
relational form, re-centred into a stance seed ("I; want; start; rig; test")
and handed to a renderer that ignored it.  Everything else that ran on the
turn -- what she perceived as salient, what she already knows about those
concepts, what it meant to her, how it moved her, when it was, what the turn
obliged of her -- stayed internal.  Like a body whose organs all work but
whose nerves only carry signal from one of them.

(FIX-A114, Sunni 2026-11-09: the first version still carried two frames --
"I am <feeling>" and "<x> is related to <y>" from internal relation-type
names.  Both are gone: her affect sets tone, not words, and her knowledge is
voiced only as predicates people actually said -- FIX-A115.)

The confluence gathers what each system contributed this turn (WHAT), and
reads the abilities that are actually live this turn out of her genealogy
(HOW):

  complexity_axes   -> how many clauses she carries
  complexity_slots  -> how long each clause may be (which motifs are eligible)
  operator_action   -> which constraint axis each clause acts on, and so which
                       system's contribution that clause voices
                         A  agency    : her stance -- the relation re-centred on her
                         B  boundary  : distinction -- choosing between options,
                                        or a contrast she knows
                         X  existence : grounding -- what she knows about it
                         T  temporal  : when -- the time the turn carries
                         N  energy    : how it moves her -- her affect
  purpose_lane      -> which of those axes gets priority
  generation_role   -> how clauses join (SHEAR contrasts, BRIDGE carries on,
                       ADJACENT sits beside, PRIMARY keeps to one clause)
  depth_score       -> how far into her own knowledge she reaches

Word order comes from her own motif lineage: promoted motifs first, and only
when none fits, the motifs her lineage has the most success with.  Her filler
places the tokens (with her own verb agreement).  The only words not drawn
from her systems are closed-class grammar (the, and, but, so, not).
Nothing is a template; if a clause has no content from a system, it is not
said.  If the result is an echo, a template, or too thin, she stays silent.

When she speaks this way, the clause motif she used is put on the turn's
grammar trace, so the next validation -- or the rehearsal comparison against
Sunni's real reply -- credits or penalizes the structure she actually used.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

AXES = ("X", "T", "N", "B", "A")

# Purpose lanes point at the axis whose contribution they want voiced.
# "meaning" is carried by nearly every ability, so it carries no preference.
LANE_AXIS = {
    "distinction_branching": "B",
    "admissibility_grounding": "X",
    "intelligence": "X",
    "continuity_memory": "T",
    "load_uncertainty": "N",
    "communication": "A",
    "repair_commitment": "A",
}
LANE_WEIGHT = 0.5

# Generation role: which axis it leans toward, and the connector it joins with.
ROLE_AXIS = {"SHEAR": "B", "BRIDGE": "X", "ADJACENT": "N", "WARP": "T"}
ROLE_CONNECTOR = {"SHEAR": "and", "BRIDGE": "so", "ADJACENT": "and", "WARP": "or", "PRIMARY": ""}
ROLE_WEIGHT = 0.4
CONTRAST_CONNECTOR = "but"

# Seed relation kinds of her ontological web, by the axis they act on.
RELATION_AXIS = {
    "is_a": "X", "instance_of": "X", "has_a": "X", "part_of": "X",
    "precedes": "T", "context_of": "T",
    "causes": "N", "enables": "N", "implies": "N",
    "opposite_of": "B", "contrasts": "B",
    "related_to": "X",
}
CONTRASTIVE_RELATIONS = frozenset({"opposite_of", "contrasts"})
KNOWLEDGE_STRENGTH = 0.25
MAX_CLAUSES = 3
REST_TURNS = 4            # FIX-A114: replies before something she voiced may be voiced again

_DEIXIS_TO_HER = {"you": "I", "your": "my", "yours": "mine", "yourself": "myself",
                  "you're": "I'm", "u": "I", "ur": "my"}
_DEIXIS_TO_THEM = {"i": "you", "i'm": "you're", "im": "you're", "my": "your",
                   "me": "you", "mine": "yours", "myself": "yourself"}
_POSSESSIVES = frozenset({"my", "your", "our", "his", "her", "their", "ur"})
_LEADING_KEEP = frozenset({"to", "about", "with", "on", "in", "at", "for", "from", "of", "into",
                           "what", "how", "why", "where", "who", "when", "which"})
_PRONOUN_AGENTS = frozenset({"i", "you", "we", "they", "he", "she", "it"})
_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*")


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})


def _words(text: str) -> List[str]:
    return _TOKEN.findall(str(text or "").translate(_QUOTES))


def _gate():
    import aurora_voice_gate as gate          # lazy: the gate imports this module
    return gate


def _is_content(word: str) -> bool:
    gate = _gate()
    low = word.lower()
    return len(low) >= 3 and low not in gate._FUNCTION_WORDS and low not in _DEIXIS_TO_HER \
        and low not in _DEIXIS_TO_THEM and "'" not in low


def _speakable(word: str) -> bool:
    gate = _gate()
    low = str(word or "").lower()
    return bool(low) and low.replace("'", "").isalpha() and low not in gate.INTERNAL_LABELS


# -----------------------------------------------------------------------------
# HOW: her live abilities
# -----------------------------------------------------------------------------

def _tag_value(tags: Sequence[str], prefix: str) -> List[str]:
    return [t[len(prefix):] for t in tags if isinstance(t, str) and t.startswith(prefix)]


def _ability_weight(tags: Sequence[str]) -> float:
    for prefix in ("overall_grade:", "purpose_grade:", "operator_grade:"):
        vals = _tag_value(tags, prefix)
        if vals:
            return max(0.05, _f(vals[0], 0.5))
    return 0.5


def _weighted_mode(values: Mapping[Any, float], default: Any) -> Any:
    if not values:
        return default
    return max(values.items(), key=lambda kv: (kv[1], str(kv[0])))[0]


def ability_how(systems: Mapping[str, Any]) -> Dict[str, Any]:
    """How she speaks this turn, read from the abilities that are live this
    turn (systems['_last_active_ability_ids']) in her genealogy."""
    genealogy = systems.get("genealogy") if isinstance(systems, Mapping) else None
    table = getattr(genealogy, "abilities", {}) or {}
    ids = [str(a) for a in list(systems.get("_last_active_ability_ids") or [])] if isinstance(systems, Mapping) else []
    axis_weight: Dict[str, float] = {ax: 0.0 for ax in AXES}
    axes_votes: Dict[int, float] = defaultdict(float)
    slot_votes: Dict[int, float] = defaultdict(float)
    role_votes: Dict[str, float] = defaultdict(float)
    lanes: Dict[str, float] = defaultdict(float)
    depths: List[float] = []
    behaviors: List[str] = []
    used: List[str] = []
    for aid in ids:
        ability = table.get(aid)
        if ability is None:
            continue
        tags = [str(t) for t in (getattr(ability, "effect_tags", ()) or ())]
        w = _ability_weight(tags)
        used.append(aid)
        for op in _tag_value(tags, "operator_action:operator_on_"):
            ax = op.strip().upper()[:1]
            if ax in axis_weight:
                axis_weight[ax] += w
        for lane in _tag_value(tags, "purpose_lane:"):
            lanes[lane] += w
            ax = LANE_AXIS.get(lane)
            if ax:
                axis_weight[ax] += LANE_WEIGHT * w
        for role in _tag_value(tags, "generation_role:"):
            role_votes[role.upper()] += w
            ax = ROLE_AXIS.get(role.upper())
            if ax:
                axis_weight[ax] += ROLE_WEIGHT * w
        for v in _tag_value(tags, "complexity_axes:"):
            axes_votes[int(_f(v, 1))] += w
        for v in _tag_value(tags, "complexity_slots:"):
            slot_votes[int(_f(v, 3))] += w
        for v in _tag_value(tags, "depth_score:"):
            depths.append(_f(v))
        primary = str(getattr(ability, "axis", "") or "").upper()[:1]
        if primary in axis_weight:
            axis_weight[primary] += 0.25 * w
        behaviors.extend(t for t in tags if ":" not in t and "_" in t and t not in behaviors)
    role = _weighted_mode(role_votes, "PRIMARY")
    complexity_axes = int(_weighted_mode(axes_votes, 2))
    clauses = 1 if role == "PRIMARY" else max(1, min(MAX_CLAUSES, complexity_axes - 1))
    slots = max(2, min(5, int(_weighted_mode(slot_votes, 3))))
    depth = sum(depths) / len(depths) if depths else 0.0
    order = [ax for ax, wt in sorted(axis_weight.items(), key=lambda kv: (-kv[1], AXES.index(kv[0]))) if wt > 0]
    for ax in ("A", "N", "X", "B", "T"):          # every axis stays reachable, after hers
        if ax not in order:
            order.append(ax)
    return {
        "abilities": used,
        "axis_order": order,
        "axis_weight": {k: round(v, 4) for k, v in axis_weight.items()},
        "clauses": clauses,
        "complexity_axes": complexity_axes,
        "slots": slots,
        "generation_role": role,
        "connector": ROLE_CONNECTOR.get(role, "and"),
        "lanes": {k: round(v, 4) for k, v in sorted(lanes.items(), key=lambda kv: -kv[1])},
        "depth": round(depth, 4),
        "reach": 1 + int(round(depth * 10)),
        "behaviors": behaviors[:12],
    }


# -----------------------------------------------------------------------------
# WHAT: each system's contribution this turn
# -----------------------------------------------------------------------------

def _agree_after_subject(verb: str, subject: str) -> str:
    """The verb as it agrees with the subject the perspective swap just put in
    front of it.  Only the copula and the verbs her grammar engine already
    knows how to agree with "I"; anything else is left as it was."""
    low = verb.lower()
    if subject == "I":
        from aurora_grammar_engine import SlotFiller
        agreed = SlotFiller()._agree_verb(verb, "I")
        return agreed if agreed.lower() in ("am", "have", "do") or agreed != verb and low in ("are", "is", "has", "does") else verb
    return "are" if low == "am" else verb


def _phrase(span: str, *, limit: int, to_her: bool) -> str:
    """The span, re-centred, trimmed after `limit` content words, keeping one
    leading preposition and the function words between kept content words."""
    toks = _words(span)
    out: List[str] = []
    content = 0
    for i, tok in enumerate(toks):
        low = tok.lower()
        # Perspective turns over: the speaker's "you" is her, their "I" is them
        # ("you know what I mean" -> "I know what you mean").
        if low in _DEIXIS_TO_HER:
            tok = _DEIXIS_TO_HER[low]
            if tok == "I" and i + 1 < len(toks):      # FIX-A129: "you are" -> "I am", not "I are"
                toks[i + 1] = _agree_after_subject(toks[i + 1], "I")
        elif low in _DEIXIS_TO_THEM:
            tok = _DEIXIS_TO_THEM[low]
            if tok == "you" and i + 1 < len(toks):    # "I am" -> "you are"
                toks[i + 1] = _agree_after_subject(toks[i + 1], "you")
        if not out and not _is_content(tok) and low not in _LEADING_KEEP and low not in _POSSESSIVES:
            continue
        if out and low in _LEADING_KEEP and content >= 2:
            break                                  # the phrase is whole; the next one starts here
        out.append(tok)
        if _is_content(tok):
            content += 1
            if content >= limit:
                break
    while out and not _is_content(out[-1]):
        out.pop()
    return " ".join(out)


def _find_web(systems: Mapping[str, Any]) -> Any:
    oets = systems.get("oets")
    if oets is None:
        perception = systems.get("perception")
        oets = perception.get("oets") if isinstance(perception, dict) else getattr(perception, "oets", None)
    return getattr(oets, "web", None)


# Closed-class English: grammar, not content.  Her tagger's own closed sets
# and the gate's function words are joined by the common adverbs and
# quantifiers they do not list, so that "already", "both" or "ago" are never
# taken for things she can say something about.
CLOSED_CLASS = frozenset({
    "already", "ago", "before", "after", "both", "one", "like", "better", "kind", "more",
    "most", "much", "many", "few", "still", "yet", "also", "too", "even", "ever", "never",
    "always", "often", "again", "maybe", "perhaps", "quite", "rather", "enough", "though",
    "although", "because", "since", "while", "until", "unless", "whether", "either",
    "neither", "each", "every", "other", "another", "same", "such", "own", "only", "else",
    "thing", "things", "stuff", "way", "lot", "bit", "something", "anything", "nothing",
    "everything", "someone", "anyone", "everyone", "whatever", "whoever", "whenever", "wherever", "currently", "later", "soon", "yes", "yeah",
    "okay", "well", "first", "last", "next", "then", "than", "into", "onto", "upon", "without",
    "within", "through", "between", "among", "against", "around", "over", "under", "again",
})
NON_ENTITY_ROLES = frozenset({"verb", "adverb", "preposition", "pronoun", "determiner", "training_gap"})


def _closed_class() -> frozenset:
    global _CLOSED
    try:
        return _CLOSED
    except NameError:
        pass
    from aurora_grammar_engine import RoleTagger as T
    sets = [getattr(T, n, frozenset()) for n in (
        "_CONTEXT_UNIGRAMS", "_CONNECTORS", "_AGENT_PRONOUNS", "_REFERENCE_PRONOUNS", "_DETERMINERS",
        "_PREPOSITIONS", "_SKIP_TOKENS", "_POSSESSIVES", "_AUXILIARIES", "_VERB_FORMS")]
    _CLOSED = frozenset(w.lower() for w in set().union(*sets)) | CLOSED_CLASS | _gate()._FUNCTION_WORDS
    return _CLOSED


def _node_role(web: Any, word: str) -> str:
    node = (getattr(web, "nodes", {}) or {}).get(str(word).lower())
    return str(getattr(node, "role", "") or "") if node is not None else ""


def _entity(web: Any, word: str) -> bool:
    low = str(word or "").lower()
    return _is_content(low) and low not in _closed_class() and _node_role(web, low) not in NON_ENTITY_ROLES


def _ing_bases(word: str) -> List[str]:
    """Base-form candidates for a progressive: feeling -> feel; making -> make;
    running -> run.  Candidates only: they are matched against predicates she
    actually holds, so a wrong guess matches nothing."""
    w = str(word or "").lower()
    if not w.endswith("ing") or len(w) < 6:
        return []
    stem = w[:-3]
    out = [stem, stem + "e"]
    if len(stem) > 2 and stem[-1] == stem[-2]:
        out.append(stem[:-1])
    return out


def _same_feeling(a: str, b: str) -> bool:
    """Her emotion's word and a word she was taught name one feeling when they
    are the same word or share a stem ("curiosity" / "curious")."""
    a, b = str(a or "").lower(), str(b or "").lower()
    return bool(a and b) and (a == b or (min(len(a), len(b)) >= 5 and a[:5] == b[:5]))


def moved_by(pipeline: Mapping[str, Any]) -> List[str]:
    """FIX-A131: the emotions that are moving her now -- her surface reaction
    and the deeper one carrying under it -- as the words her own state holds."""
    out: List[str] = []
    for key in ("surface_reactive_emotion", "deep_emotional_state"):
        word = str(dict(pipeline.get(key) or {}).get("dominant") or "").lower()
        if word and word != "neutral" and word not in out:
            out.append(word)
    return out


def knowledge(systems: Mapping[str, Any], concepts: Sequence[str], heard: str, *,
              reach: int, session_id: str = "", feeling: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """What was ASSERTED about the concepts in play (FIX-A115): who said which
    predicate of what, recalled from either end, voiced as it was said.  Where
    a concept has a place in her constraint space, what she knows is ranked by
    how well it fits what this moment means.  Links nobody asserted are not
    voiced (FIX-A114): their type names are internal labels."""
    web = _find_web(systems)
    if web is None:
        return []
    from aurora_internal.aurora_propositional_understanding import (
        _lemma, cosine, lexicalize_assertion, meaning_profile, participants, predicate_order)
    heard_set = {w.lower() for w in _words(heard)}
    # FIX-A129: the words of the question, and their base forms, say which of
    # the predicates held along a relation the moment is about.
    heard_forms = set(heard_set)
    for _w in heard_set:
        try:
            heard_forms.add(_lemma(_w))
        except Exception:
            pass
        heard_forms.update(_ing_bases(_w))      # FIX-A131: "feeling" is "feel" being asked about
    acts = _acts_in(heard)
    by_source = getattr(web, "_relations_by_source", {}) or {}
    by_target = getattr(web, "_relations_by_target", {}) or {}
    relations = getattr(web, "relations", {}) or {}
    pipeline = dict(systems.get("_last_pipeline_state") or {}) if isinstance(systems, Mapping) else {}
    moment = meaning_profile(pipeline)
    speaker_now, self_now = participants(session_id, systems)
    nodes = getattr(web, "nodes", {}) or {}

    def fit(word: str) -> float:
        prof = dict(getattr(nodes.get(word), "axis_profile", {}) or {})
        return 0.75 + 0.5 * cosine(moment, prof) if moment and prof else 1.0

    found: List[Dict[str, Any]] = []
    seen: set = set()
    for concept in concepts:
        concept = str(concept).lower()
        rids = [(rid, "out") for rid in list(by_source.get(concept, ()) or ())] + \
               [(rid, "in") for rid in list(by_target.get(concept, ()) or ())]
        for rid, side in rids:
            rel = relations.get(rid)
            if rel is None or rid in seen:
                continue
            if getattr(rel, "assertion", None):
                seen.add(rid)          # FIX-A129: all its predicates are taken below
            source_w = str(getattr(rel, "source_word", "") or "").lower()
            target = str(getattr(rel, "target_word", "") or "").lower()
            kind = str(getattr(getattr(rel, "relation_type", None), "value", "") or "")
            strength = _f(getattr(rel, "strength", 0.0))
            asserted = bool(getattr(rel, "assertion", None))
            if asserted:
                # Something was said along it: who, and which predicate.  The
                # thing may be what the speaker just named -- what she adds is
                # who holds it and how.
                if not _speakable(target) or source_w in heard_set and target in heard_set:
                    continue
                n = int(dict(rel.assertion).get("n", 1) or 1)
                base = strength * _f(getattr(rel, "confidence", 1.0), 1.0) * (1.0 + 0.3 * math.log1p(n)) \
                    * fit(target)
                said = dict(dict(rel.assertion).get("predicates") or {})
                for pred in predicate_order(rel):
                    lex = lexicalize_assertion(rel, speaker_now=speaker_now, self_now=self_now, predicate=pred)
                    if lex is None:
                        continue
                    surface = str(dict(said.get(pred) or {}).get("surface") or pred).lower()
                    asked_pred = pred.lower() in heard_forms or surface in heard_forms
                    # FIX-A131: the thing itself was named ("are you ever
                    # curious?") -- what she holds about that thing is what was
                    # asked, whichever predicate holds it.
                    asked_thing = target in heard_forms
                    asked = asked_pred or asked_thing
                    # what she holds that is what is moving her now speaks first
                    felt = any(_same_feeling(target, f) for f in feeling)
                    found.append({"source": source_w, "kind": kind, "target": target,
                                  "strength": round(base * (1.5 if asked_pred else 1.0)
                                                    * (1.5 if asked_thing else 1.0)
                                                    * (1.3 if felt else 1.0), 4),
                                  "axis": RELATION_AXIS.get(kind, "X"), "learned_from": "assertion", "lex": lex,
                                  "asked": bool(asked)})
                continue
            # FIX-A114: a link nobody asserted (co-occurrence, the role-pair
            # type, a seed) is hers to reason with, but its type name ("is
            # related to", "is instance of") is an internal label, not language.
            # Only what was actually said is voiced.
            continue
    # FIX-A133: what she can work out from what she was told (order, chained).
    try:
        from aurora_internal.aurora_learned_rules import derive
        found = derive(web, heard, speaker_now=speaker_now, self_now=self_now) + found
    except Exception:
        pass
    found.sort(key=lambda r: (-r["strength"], r["source"], r["target"]))
    return found[: max(1, int(reach)) * 4]


def _acts_in(heard: str) -> set:
    """The words her tagger reads as the action where they were just said:
    "know" in "I know what I mean" is something done, not a thing."""
    from aurora_grammar_engine import RoleTagger, TokenRole
    try:
        return {tok.lower() for tok, role in RoleTagger().tag(heard) if role is TokenRole.ACTION}
    except Exception:
        return set()


def _is_verb(systems: Mapping[str, Any], word: str, heard: str) -> bool:
    """Is this a verb to her: one of her tagger's verb forms, a verb node in
    her web, or what her tagger reads as the action where it was said."""
    from aurora_grammar_engine import RoleTagger, TokenRole
    low = str(word or "").lower()
    if low in {w.lower() for w in RoleTagger._VERB_FORMS} or _node_role(_find_web(systems), low) == "verb":
        return True
    try:
        return any(tok.lower() == low and role is TokenRole.ACTION for tok, role in RoleTagger().tag(heard))
    except Exception:
        return False


def _named_in(systems: Mapping[str, Any], heard: str, session_id: str) -> List[str]:
    """The participants the words refer to ("you" -> her, "I" -> the speaker)
    and the entities named in what was heard."""
    from aurora_internal.aurora_propositional_understanding import _FIRST, _SECOND, participants
    speaker, self_now = participants(session_id, systems)
    found: List[str] = []
    web = _find_web(systems)
    for w in _words(heard):
        low = w.lower()
        if low in _SECOND and self_now:
            found.append(self_now)
        elif low in _FIRST and speaker:
            found.append(speaker)
        elif web is not None and _entity(web, low) and low in (getattr(web, "nodes", {}) or {}):
            found.append(low)
    return list(dict.fromkeys(found))


def gather(systems: Mapping[str, Any], heard: str, how: Mapping[str, Any], *,
           session_id: str = "") -> Dict[str, Any]:
    gate = _gate()
    pipeline = dict(systems.get("_last_pipeline_state") or {}) if isinstance(systems, Mapping) else {}
    form = gate._relational_form(systems)
    slots = int(how.get("slots", 3))
    obj_limit = max(1, slots - 1)
    subject_words = [w.lower() for w in _words(form.get("subject"))]
    obj_words = [w.lower() for w in _words(" ".join(str(form.get(k) or "") for k in ("obj", "complement")))]
    addressed = bool(set(_DEIXIS_TO_HER) & set(subject_words + obj_words))

    # communication: the relation she was addressed with, re-centred on her
    relation = [w for w in _words(form.get("relation")) if _is_content(w)]
    relation = [w for w in relation if _is_verb(systems, w, heard)]
    stance: Dict[str, Any] = {}
    if relation:
        agent = "I" if addressed else _phrase(str(form.get("subject") or ""), limit=2, to_her=False)
        if agent.lower() in _PRONOUN_AGENTS or (agent and all(_is_content(w) for w in agent.split())):
            act = relation[0].lower()
            if act.endswith("ing") and len(act) > 4:     # "introducing" is not finite: the copula carries it
                act = ("am" if agent == "I" else "are" if agent.lower() in ("you", "we", "they") else "is") + " " + act
            stance = {"agent": agent, "action": act,
                      "object": _phrase(" ".join(str(form.get(k) or "") for k in ("obj", "complement")),
                                        limit=obj_limit, to_her=True)}
    options = []
    if stance.get("object"):
        options.append(stance["object"])
    for alt in list(form.get("alternatives") or []):
        alt = dict(alt or {})
        text = _phrase(" ".join(str(alt.get(k) or "") for k in ("subject", "object", "complement")),
                       limit=obj_limit, to_her=True)
        if text and text not in options:
            options.append(text)

    # perception: what stood out
    salient = [str(c).lower() for c in list(pipeline.get("salient_concepts") or []) if _speakable(c)]
    # knowledge: what she already knows about it
    concepts = list(dict.fromkeys(salient + [w.lower() for o in options for w in _words(o) if _is_content(w)]))
    # FIX-A129: "who built you?" and "how are you feeling?" are about the
    # participants the words name.  Who "you" and "I" are comes from her own
    # participant resolution, whatever else stood out.  When nothing stood out
    # at all, the other entities named are looked up too.
    from aurora_internal.aurora_propositional_understanding import PARTICIPANTS
    named = _named_in(systems, heard, session_id)
    if salient:
        named = [n for n in named if n in PARTICIPANTS]
    concepts = list(dict.fromkeys(concepts + named))
    known = knowledge(systems, concepts, heard, reach=int(how.get("reach", 1)), session_id=session_id,
                      feeling=moved_by(pipeline))
    # affect: how it moved her
    surface = dict(pipeline.get("surface_reactive_emotion") or {})
    tone = str(surface.get("tone_bias") or "").lower()
    affect = tone if tone and tone != "neutral" and _speakable(tone) else ""
    # time: when it is
    meta = dict(pipeline.get("utterance_meta") or {})
    when = str(meta.get("time_ref") or "").lower()
    when = when if _speakable(when) else ""
    # obligation and consciousness
    obligation = dict(pipeline.get("response_obligation") or {})
    crest = dict(dict(pipeline.get("pre_generation_conscious_frame") or {}).get("conscious_crest") or {})
    return {
        "stance": stance,
        "options": options,
        "addressed": addressed,
        "salient": salient,
        "knowledge": known,
        "affect": affect,
        "time": when,
        "obligation": str(obligation.get("operation") or ""),
        "unknown_role": str(obligation.get("unknown_role") or ""),
        "crest_axis": str(crest.get("axis") or "").upper()[:1],
        "meaning": str(pipeline.get("meaning_label") or ""),
    }


# -----------------------------------------------------------------------------
# Clause planning: each clause voices one axis's contribution
# -----------------------------------------------------------------------------

def _option_knowledge(option: str, known: Sequence[Mapping[str, Any]]) -> float:
    words = {w.lower() for w in _words(option)}
    return sum(_f(k.get("strength")) for k in known if k.get("source") in words)


_SAID = "\x00said"


def _said_key(lex: Mapping[str, Any]) -> str:
    """A statement as it is voiced: the same words twice are one statement."""
    return "|".join(str(lex.get(f) or "").lower() for f in ("agent", "action", "object"))


def _knowledge_clause(known: List[Dict[str, Any]], used: set, *, axis: str, prefer_axis: bool,
                      resting: Optional[set] = None) -> Optional[Dict[str, Any]]:
    # FIX-A129: what rests is a statement -- who, to what, which predicate --
    # not the whole pair; and what the speaker just asked about is not made to
    # rest at all, so a direct question can be answered again.
    said = {t for s_, t in used if s_ == _SAID}
    # FIX-A133: when she has worked out the answer to what was asked, the answer
    # is what she says -- not whatever else she happens to hold about the words.
    if any(k.get("derived") for k in known):
        known = [k for k in known if k.get("derived")]

    def _voiced(k: Mapping[str, Any]) -> bool:
        key = _said_key(dict(k.get("lex") or {}))
        return any(key == t or t.startswith(key + " ") for t in said)   # "feel calm right now" says "feel calm"
    pool = [k for k in known if (k["source"], k["target"]) not in used
            and not _voiced(k)
            and (k.get("asked") or (k["source"], k["target"], str(dict(k.get("lex") or {}).get("predicate") or ""))
                 not in (resting or set()))]
    voiced = {s for s, _ in used if s != _SAID} | {t for s, t in used if s != _SAID}
    pool = [k for k in pool if k["source"] not in voiced and k["target"] not in voiced] or pool
    # FIX-A129: what the speaker's own words asked about is answered before
    # what her axes would rather say.
    pool = [k for k in pool if k.get("asked")] or pool
    if prefer_axis:
        pool = [k for k in pool if k["axis"] == axis] or pool
    if not pool:
        return None
    k = pool[0]
    used.add((k["source"], k["target"]))
    lex = dict(k.get("lex") or {})
    if not lex:
        return None
    used.add((_SAID, _said_key(lex)))
    # FIX-A115: what was said, as it was said -- who, the predicate, to what.
    return {"agent": lex["agent"], "action": lex["action"], "object": lex["object"],
            "determiner": "", "contrast": lex.get("denied") == "True",
            "system": "knowledge", "relation": dict(k)}


def plan(contrib: Mapping[str, Any], how: Mapping[str, Any]) -> List[Dict[str, Any]]:
    stance = dict(contrib.get("stance") or {})
    options = list(contrib.get("options") or [])
    known = list(contrib.get("knowledge") or [])
    resting = set(contrib.get("resting") or ())
    used: set = set()
    clauses: List[Dict[str, Any]] = []
    budget = int(how.get("clauses", 1))
    stance_done = False
    chosen = ""
    time_used = False

    # B before A when both are wanted: the choice shapes the stance clause.
    order = list(how.get("axis_order") or AXES)
    if "B" in order and len(options) >= 2:
        scored = sorted(options, key=lambda o: (-_option_knowledge(o, known), options.index(o)))
        chosen = scored[0]

    for axis in order:
        if len(clauses) >= budget:
            break
        clause: Optional[Dict[str, Any]] = None
        if axis == "A" and stance and not stance_done:
            obj = chosen or stance.get("object", "")
            clause = {"agent": stance["agent"], "action": stance["action"], "object": obj,
                      "determiner": "the" if obj and obj == chosen and obj != stance.get("object") else "",
                      "contrast": False, "system": "communication"}
            stance_done = True
            skey = _said_key(clause)
            # a knowledge clause that said the same statement is carried by the stance clause
            clauses[:] = [c for c in clauses
                          if not (c.get("system") == "knowledge"
                                  and (skey == _said_key(c) or skey.startswith(_said_key(c) + " ")))]
            used.add((_SAID, skey))
        elif axis == "B":
            others = [o for o in options if o != (chosen or stance.get("object", ""))]
            if chosen and not stance_done and stance:
                continue                                  # voiced inside the stance clause
            k = _knowledge_clause(known, used, axis="B", prefer_axis=True, resting=resting)
            if k is not None and (k["contrast"] or not others):
                clause = k
            elif others and k is not None:
                clause = k
        elif axis == "X":
            clause = _knowledge_clause(known, used, axis="X", prefer_axis=True, resting=resting)
        elif axis == "N":
            # FIX-A114: no "I am <feeling>" frame -- that was my wording with one
            # blank.  Her affect sets the tone of what she says; it is not a clause.
            clause = _knowledge_clause(known, used, axis="N", prefer_axis=True, resting=resting)
        elif axis == "T":
            stance_clause = next((c for c in clauses if c.get("system") == "communication"), None)
            if contrib.get("time") and stance_clause is not None and not time_used:
                stance_clause.setdefault("descriptor", contrib["time"])
                time_used = True
                continue                                  # time rides on what she said she'd do
            clause = _knowledge_clause(known, used, axis="T", prefer_axis=True, resting=resting)
        if clause is not None:
            clause["axis"] = axis
            clauses.append(clause)

    # The stance clause leads whenever she was addressed and has one.
    for i, c in enumerate(clauses):
        if c.get("system") == "communication" and i:
            clauses.insert(0, clauses.pop(i))
            break
    if contrib.get("time") and clauses and not time_used and clauses[0].get("system") == "communication" \
            and not clauses[0].get("descriptor"):
        clauses[0]["descriptor"] = contrib["time"]
    return clauses


# -----------------------------------------------------------------------------
# Composition: her motifs order, her filler places
# -----------------------------------------------------------------------------

def _pool(clause: Mapping[str, Any]):
    from aurora_grammar_engine import TokenRole
    pool: Dict[Any, List[str]] = {}
    for key, role in (("agent", TokenRole.AGENT), ("action", TokenRole.ACTION),
                      ("object", TokenRole.OBJECT), ("descriptor", TokenRole.DESCRIPTOR),
                      ("determiner", TokenRole.DETERMINER)):
        val = str(clause.get(key) or "").strip()
        if val:
            pool[role] = [val]
    return pool


def _core(clause: Mapping[str, Any], pool: Mapping[Any, List[str]]) -> set:
    """The roles a shape may not drop: who, the act, what it is about, and
    whatever this clause exists to carry (her affect clause carries a quality)."""
    from aurora_grammar_engine import TokenRole
    core = {r for r in pool if r in (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT)}
    carries = str(clause.get("carries") or "")
    if carries:
        core |= {r for r in pool if r.value == carries}
    return core


def choose_motif(engine: Any, pool: Mapping[Any, List[str]], *, slots: int,
                 crest_axis: str = "", core: Optional[set] = None) -> Tuple[Any, bool]:
    """(motif, promoted).  Among her valid clause shapes that fit the slots
    her abilities allow and that this clause can fill: promoted first; else
    the ones her lineage has had success with."""
    from aurora_grammar_engine import TokenRole, is_valid_clause_shape, _clamp
    lineage = getattr(engine, "_lineage", None)
    motifs = list(getattr(lineage, "_motifs", {}).values()) if lineage is not None else []
    if core is None:
        core = {r for r in pool if r in (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT)}
    fits = [m for m in motifs
            if is_valid_clause_shape(m.role_sequence)
            and len(m.role_sequence) <= slots
            and all(r in pool for r in m.role_sequence)
            and core <= set(m.role_sequence)]           # a shape may not drop what the clause is about
    promoted = [m for m in fits if m.promoted]
    candidates = promoted or [m for m in fits if m.success_count > 0]
    if not candidates:
        return None, False
    try:
        orientation, outlet = engine._pressure_state()
    except Exception:
        orientation, outlet = ({ax: 1.0 for ax in AXES}, 0.0)
    orientation = dict(orientation)
    if crest_axis in orientation:
        orientation[crest_axis] = orientation[crest_axis] * 1.2

    def score(m: Any) -> Tuple[float, int, str]:
        axis_fit = sum(m.constraint_scores.get(ax, 0.5) * _clamp(v, 0.5, 2.0)
                       for ax, v in orientation.items()) / max(1, len(orientation))
        agent = outlet * 0.25 if m.role_sequence and m.role_sequence[0] is TokenRole.AGENT else 0.0
        coverage = len(m.role_sequence) / max(1, len(pool))
        return (m.composability_score() * 0.45 + axis_fit * 0.30 + agent + 0.2 * coverage,
                m.success_count, m.pattern_id)

    return max(candidates, key=score), bool(promoted)


def compose(systems: Dict[str, Any], heard: str, *, engine: Any = None,
            session_id: str = "") -> Tuple[str, Dict[str, Any]]:
    """(text, record).  text is '' when no system gave her anything to say
    that would survive the gate."""
    gate = _gate()
    record: Dict[str, Any] = {"heard": str(heard or "")[:200]}
    if engine is None:
        engine = systems.get("grammar_engine") if isinstance(systems, Mapping) else None
    if engine is None:
        record["why"] = "no_grammar_engine"
        return "", record
    how = ability_how(systems)
    contrib = gather(systems, heard, how, session_id=session_id)
    # FIX-A114: what she voiced in the last REST_TURNS replies rests -- the same
    # remembered statement does not answer turn after turn.
    turn = int(systems.get("_confluence_turn", 0) or 0) + 1 if isinstance(systems, dict) else 0
    voiced_log = list(systems.get("_confluence_voiced") or []) if isinstance(systems, dict) else []
    voiced_log = [v for v in voiced_log if turn - int(v[0]) <= REST_TURNS]
    contrib["resting"] = {tuple(v[1]) for v in voiced_log if v[1]}
    recent_texts = {str(v[2]) for v in voiced_log if len(v) > 2}
    if isinstance(systems, dict):
        systems["_confluence_turn"] = turn
        systems["_confluence_voiced"] = voiced_log
    clauses = plan(contrib, how)
    record.update({"how": how, "contributions": {k: v for k, v in contrib.items() if v}})
    if not clauses:
        record["why"] = "nothing_contributed"
        return "", record
    from aurora_grammar_engine import SlotFiller
    filler = SlotFiller()
    said: List[Dict[str, Any]] = []
    for clause in clauses:
        pool = _pool(clause)
        core = _core(clause, pool)
        motif, promoted = choose_motif(engine, pool, slots=int(how.get("slots", 3)),
                                       crest_axis=str(contrib.get("crest_axis") or ""), core=core)
        if motif is None and clause.get("descriptor") and clause.get("carries") != "descriptor":
            # the qualifier may not fit any shape she has; the clause still can
            pool.pop(next(r for r in pool if r.value == "descriptor"), None)
            motif, promoted = choose_motif(engine, pool, slots=int(how.get("slots", 3)),
                                           crest_axis=str(contrib.get("crest_axis") or ""),
                                           core=_core(clause, pool))
        if motif is None:
            continue
        text = filler.fill(motif, pool).strip()
        if len(text.split()) < 2:
            continue
        said.append({"text": text, "motif_id": motif.pattern_id, "promoted": promoted,
                     "role_sequence": [r.value for r in motif.role_sequence],
                     "axis": clause.get("axis"), "system": clause.get("system"),
                     "contrast": bool(clause.get("contrast"))})
    record["clauses"] = said
    if not said:
        record["why"] = "no_motif_fits"
        return "", record
    parts = [said[0]["text"]]
    for c in said[1:]:
        body = c["text"]
        if not body.startswith("I ") and not body.startswith("I'"):
            body = body[0].lower() + body[1:]
        joint = CONTRAST_CONNECTOR if c["contrast"] else str(how.get("connector") or "")
        parts.append((", " + joint + " " if joint else ". ") + body)
    text = "".join(parts).strip()
    if text and text[-1] not in ".!?":
        text += "."
    why = gate.articulation_rejection(text, heard) or gate.parrot_reason(text, heard) \
        or gate.scripted_reason("confluence", text, dm=True) \
        or ("repeat" if text.lower() in {t.lower() for t in recent_texts} else "")
    # FIX-A133: a statement she worked out from what she was told ("d is after a"
    # to "is d after a?") restates the question's words because that is what an
    # answer to it is; it is not a parrot.
    if why == "echo" and any(dict(c.get("relation") or {}).get("derived") for c in clauses):
        why = ("repeat" if text.lower() in {t.lower() for t in recent_texts} else "")
    if why:
        record["why"] = why
        record["rejected"] = text[:200]
        return "", record
    record["text"] = text
    if isinstance(systems, dict):
        for c in clauses:
            rel = dict(c.get("relation") or {})
            if rel:
                systems["_confluence_voiced"].append(
                    (turn, (rel.get("source"), rel.get("target"),
                            str(dict(rel.get("lex") or {}).get("predicate") or "")), text))
        systems["_confluence_voiced"].append((turn, None, text))
    return text, record


def put_on_grammar_trace(systems: Dict[str, Any], record: Mapping[str, Any], engine: Any = None) -> bool:
    """The motif she used is the one the next validation should judge."""
    said = list(record.get("clauses") or [])
    if not said or not isinstance(systems, dict):
        return False
    lead = said[0]
    trace = {"motif_id": lead["motif_id"], "role_sequence": list(lead["role_sequence"]),
             "constraint_fit": 0.0, "source": "confluence"}
    systems["_last_grammar_trace"] = trace
    pipeline = systems.get("_last_pipeline_state")
    if isinstance(pipeline, dict):
        pipeline["grammar_motif_id"] = trace["motif_id"]
        pipeline["grammar_role_sequence"] = trace["role_sequence"]
        pipeline["grammar_constraint_fit"] = 0.0
    if engine is None:
        engine = systems.get("grammar_engine")
    lineage = getattr(engine, "_lineage", None)
    try:
        if lineage is not None:
            from aurora_grammar_engine import TokenRole
            seq = tuple(TokenRole(r) for r in lead["role_sequence"])
            orientation, _ = engine._pressure_state()
            lineage.record_trace(seq, engine._context_hash(str(record.get("heard") or "")),
                                 len(str(lead["text"]).split()), orientation)
    except Exception:
        pass
    return True
