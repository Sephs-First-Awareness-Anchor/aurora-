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
from her systems are closed-class grammar (I, you, the, and, but, so, is).
Nothing is a template; if a clause has no content from a system, it is not
said.  If the result is an echo, a template, or too thin, she stays silent.

When she speaks this way, the clause motif she used is put on the turn's
grammar trace, so the next validation -- or the rehearsal comparison against
Sunni's real reply -- credits or penalizes the structure she actually used.
"""

from __future__ import annotations

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

_DEIXIS_TO_HER = {"you": "I", "your": "my", "yours": "mine", "yourself": "myself",
                  "you're": "I'm", "u": "I", "ur": "my"}
_DEIXIS_TO_THEM = {"i": "you", "i'm": "you're", "im": "you're", "my": "your",
                   "me": "you", "mine": "yours", "myself": "yourself"}
_LEADING_KEEP = frozenset({"to", "about", "with", "on", "in", "at", "for", "from", "of", "into"})
_PRONOUN_AGENTS = frozenset({"i", "you", "we", "they", "he", "she", "it"})
_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*")


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _words(text: str) -> List[str]:
    return _TOKEN.findall(str(text or ""))


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

def _phrase(span: str, *, limit: int, to_her: bool) -> str:
    """The span, re-centred, trimmed after `limit` content words, keeping one
    leading preposition and the function words between kept content words."""
    toks = _words(span)
    out: List[str] = []
    content = 0
    for i, tok in enumerate(toks):
        low = tok.lower()
        if to_her and low in _DEIXIS_TO_HER:
            tok = _DEIXIS_TO_HER[low]
        elif not to_her and low in _DEIXIS_TO_THEM:
            tok = _DEIXIS_TO_THEM[low]
        if not out and not _is_content(tok) and low not in _LEADING_KEEP:
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
    "everything", "someone", "anyone", "everyone", "currently", "later", "soon", "yes", "yeah",
    "okay", "well", "first", "last", "next", "then", "than", "into", "onto", "upon", "without",
    "within", "through", "between", "among", "against", "around", "over", "under", "again",
})
NON_ENTITY_ROLES = frozenset({"verb", "adverb", "preposition", "pronoun", "determiner", "training_gap"})
WEAK_KINDS = {"related_to": 0.5, "context_of": 0.5}
WEAK_SOURCES = {"co-occurrence": 0.6, "co-expression": 0.6, "adjacency": 0.6, "backfill_role_heuristic": 0.7}


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


def _lexicalize(kind: str) -> str:
    """Her web's own relation names, spoken: 'enables' -> 'enables',
    'is_a' -> 'is a', 'part_of' -> 'is part of'.  Discovered kinds (component
    ids) have no words yet and are not spoken."""
    if kind not in RELATION_AXIS:
        return ""
    parts = kind.split("_")
    if parts[0] in ("is", "has"):
        return " ".join(parts)
    if len(parts) == 1:
        return parts[0]
    return "is " + " ".join(parts)


def knowledge(systems: Mapping[str, Any], concepts: Sequence[str], heard: str, *,
              reach: int) -> List[Dict[str, Any]]:
    """What she already knows about the concepts in play: relations from them
    to something the speaker did not say."""
    web = _find_web(systems)
    if web is None:
        return []
    heard_set = {w.lower() for w in _words(heard)}
    acts = _acts_in(heard)
    by_source = getattr(web, "_relations_by_source", {}) or {}
    relations = getattr(web, "relations", {}) or {}
    found: List[Dict[str, Any]] = []
    for concept in concepts:
        for rid in list(by_source.get(str(concept).lower(), ()) or ()):
            rel = relations.get(rid)
            if rel is None:
                continue
            target = str(getattr(rel, "target_word", "") or "")
            kind = str(getattr(getattr(rel, "relation_type", None), "value", "") or "")
            strength = _f(getattr(rel, "strength", 0.0))
            if strength < KNOWLEDGE_STRENGTH or target.lower() in heard_set:
                continue
            if not _speakable(target) or not _is_content(target) or not _lexicalize(kind):
                continue
            # She relates things: an entity on each side.  A verb or function
            # word ("want", "already") is not something she can say a thing about.
            if not _entity(web, concept) or not _entity(web, target) or str(concept).lower() in acts:
                continue
            # Typed, researched knowledge says more than words that merely
            # occurred together; both are hers, the first is ranked higher.
            source = str(getattr(rel, "source_of_knowledge", "") or "")
            score = strength * _f(getattr(rel, "confidence", 1.0), 1.0) \
                * WEAK_KINDS.get(kind, 1.0) * WEAK_SOURCES.get(source, 1.0)
            found.append({"source": str(concept).lower(), "kind": kind, "target": target.lower(),
                          "strength": round(score, 4), "axis": RELATION_AXIS[kind], "learned_from": source})
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


def gather(systems: Mapping[str, Any], heard: str, how: Mapping[str, Any]) -> Dict[str, Any]:
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
            stance = {"agent": agent, "action": relation[0].lower(),
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
    known = knowledge(systems, concepts, heard, reach=int(how.get("reach", 1)))
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


def _knowledge_clause(known: List[Dict[str, Any]], used: set, *, axis: str, prefer_axis: bool) -> Optional[Dict[str, Any]]:
    pool = [k for k in known if (k["source"], k["target"]) not in used]
    voiced = {s for s, _ in used} | {t for _, t in used}
    pool = [k for k in pool if k["source"] not in voiced and k["target"] not in voiced] or pool
    if prefer_axis:
        pool = [k for k in pool if k["axis"] == axis] or pool
    if not pool:
        return None
    k = pool[0]
    used.add((k["source"], k["target"]))
    return {"agent": k["source"], "action": _lexicalize(k["kind"]), "object": k["target"],
            "determiner": "", "contrast": k["kind"] in CONTRASTIVE_RELATIONS,
            "system": "knowledge", "relation": dict(k)}


def plan(contrib: Mapping[str, Any], how: Mapping[str, Any]) -> List[Dict[str, Any]]:
    stance = dict(contrib.get("stance") or {})
    options = list(contrib.get("options") or [])
    known = list(contrib.get("knowledge") or [])
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
            if contrib.get("unknown_role") == "object":
                filled = [k for k in known if k["source"] in {w.lower() for w in _words(obj)}]
                if filled:
                    obj = filled[0]["target"]
                    used.add((filled[0]["source"], filled[0]["target"]))
            clause = {"agent": stance["agent"], "action": stance["action"], "object": obj,
                      "determiner": "the" if obj and obj == chosen and obj != stance.get("object") else "",
                      "contrast": False, "system": "communication"}
            stance_done = True
        elif axis == "B":
            others = [o for o in options if o != (chosen or stance.get("object", ""))]
            if chosen and not stance_done and stance:
                continue                                  # voiced inside the stance clause
            k = _knowledge_clause(known, used, axis="B", prefer_axis=True)
            if k is not None and (k["contrast"] or not others):
                clause = k
            elif others and k is not None:
                clause = k
        elif axis == "X":
            clause = _knowledge_clause(known, used, axis="X", prefer_axis=True)
        elif axis == "N":
            if contrib.get("affect"):
                clause = {"agent": "I", "action": "is", "object": "", "descriptor": contrib["affect"],
                          "determiner": "", "contrast": False, "system": "affect", "carries": "descriptor"}
            else:
                clause = _knowledge_clause(known, used, axis="N", prefer_axis=True)
        elif axis == "T":
            stance_clause = next((c for c in clauses if c.get("system") == "communication"), None)
            if contrib.get("time") and stance_clause is not None and not time_used:
                stance_clause.setdefault("descriptor", contrib["time"])
                time_used = True
                continue                                  # time rides on what she said she'd do
            clause = _knowledge_clause(known, used, axis="T", prefer_axis=True)
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


def compose(systems: Dict[str, Any], heard: str, *, engine: Any = None) -> Tuple[str, Dict[str, Any]]:
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
    contrib = gather(systems, heard, how)
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
        or gate.scripted_reason("confluence", text, dm=True)
    if why:
        record["why"] = why
        record["rejected"] = text[:200]
        return "", record
    record["text"] = text
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
