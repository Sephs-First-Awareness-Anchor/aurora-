# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_learned_rules.py -- what a learned statement can DO (FIX-A133).

A statement she learned ("The letter c comes after the letter b.") is stored as
a relation with the predicate said along it.  Until now only speech read it back.
This module lets her REASON from what she was told:

    ORDER      later / earlier, chained:  b after a, c after b  =>  c after a
               answers "what comes after b?", "is c after a?"
    RULES      "I feel calm when you are settled"  =>  when what holds the condition
               comes up, she states what she holds under it
    MARKS      'The mark "?" ends a question.'  =>  answers 'what does "?" end?',
               "what ends a question?" (a mark mentioned in quotes is a word she can learn about)
    KIND       "b is a letter", "a letter is a symbol"  =>  b is a symbol;
               answers "what is b?", "is b a letter?"; and a word told to be a
               noun / verb / adjective ... becomes one in her web (its role), so
               her own statement reader finds it as the act of a sentence

Everything it reads is her own learned relations (the ones carrying an
``assertion`` record, so only what someone actually said).  Nothing is placed:
no order, no letter, no word is written into her.  The closed-class words that
make a predicate an ordering ("follow", "precede", "come after", "come before",
"be after", "be before") are grammar -- the same kind of closed list as her
copulas, modals and negators -- not content.

The derived statements come back in the shape the confluence already speaks
from (agent / action / object), flagged ``derived``, so what she says is still
composed by her own composer, in her own voice.

Placed on the information map: reads OntologicalWeb relations (``assertion``);
feeds aurora_confluence.knowledge().  Constraint axis: T (temporal order).
"""
from __future__ import annotations

import re
from collections import deque
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# The roles her web already gives words (OETS node.role): a word told it is one is one.
ROLE_NAMES = frozenset({"noun", "verb", "adjective", "adverb", "preposition", "pronoun", "determiner"})
KIND_PREDICATE = "be a"

# The subject is LATER than the object / EARLIER than the object.
LATER_PREDICATES = frozenset({"follow", "come after", "be after", "succeed"})
EARLIER_PREDICATES = frozenset({"precede", "come before", "be before"})

_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*|(?<=\")[.?!,;:](?=\")")
_QUESTION_WORDS = frozenset({"what", "which", "who"})
_AUX = frozenset({"is", "are", "does", "do", "did", "was", "were", "will"})
_FILLER = frozenset({"the", "a", "an", "letter", "letters", "word", "one", "thing", "that", "this",
                     "right", "directly", "just", "immediately", "ever", "also", "really"})


def _f(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


# -----------------------------------------------------------------------------
# What she was told about order
# -----------------------------------------------------------------------------

def _order_edges_scan(web: Any) -> Dict[Tuple[str, str], int]:
    """{(earlier, later): times said} from the statements along her relations.
    A predicate said and denied about equally is not held."""
    edges: Dict[Tuple[str, str], int] = {}
    for rel in list(getattr(web, "relations", {}).values()):
        a = getattr(rel, "assertion", None)
        if not a:
            continue
        src = str(getattr(rel, "source_word", "") or "").lower()
        tgt = str(getattr(rel, "target_word", "") or "").lower()
        if not src or not tgt or src == tgt:
            continue
        for pred, p in dict(dict(a).get("predicates") or {}).items():
            n = int(dict(p).get("n", 0) or 0)
            denied = int(dict(p).get("denied", 0) or 0)
            if _verdict(p) != "held":
                continue
            if pred in LATER_PREDICATES:
                key = (tgt, src)
            elif pred in EARLIER_PREDICATES:
                key = (src, tgt)
            else:
                continue
            edges[key] = edges.get(key, 0) + n - denied
    return edges


from aurora_internal.aurora_learned_index import memo as _memo
from aurora_internal.aurora_propositional_understanding import verdict as _verdict   # FIX-A135: one resolution, many consumers


def order_edges(web: Any) -> Dict[Tuple[str, str], int]:
    return _memo(web, "order", lambda: _order_edges_scan(web))


def kind_edges(web: Any) -> Dict[Tuple[str, str], int]:
    return _memo(web, "kinds", lambda: _kind_edges_scan(web))


def end_edges(web: Any) -> Dict[Tuple[str, str], int]:
    return _memo(web, "ends", lambda: _end_edges_scan(web))


def _order_verdicts_scan(web: Any) -> Dict[Tuple[str, str], str]:
    """{(earlier, later): "held" | "denied" | "contested"} for every order she was told, including
    the ones told NOT to be so (which are not edges, but are not nothing)."""
    out: Dict[Tuple[str, str], str] = {}
    rank = {"held": 3, "contested": 2, "denied": 1}
    for rel in list(getattr(web, "relations", {}).values()):
        a = getattr(rel, "assertion", None)
        if not a:
            continue
        src = str(getattr(rel, "source_word", "") or "").lower()
        tgt = str(getattr(rel, "target_word", "") or "").lower()
        if not src or not tgt or src == tgt:
            continue
        for pred, p in dict(dict(a).get("predicates") or {}).items():
            v = _verdict(p)
            if v == "unsaid":
                continue
            if pred in LATER_PREDICATES:
                key = (tgt, src)
            elif pred in EARLIER_PREDICATES:
                key = (src, tgt)
            else:
                continue
            if rank[v] > rank.get(out.get(key, ""), 0):
                out[key] = v
    return out


def order_verdicts(web: Any) -> Dict[Tuple[str, str], str]:
    return _memo(web, "order_verdicts", lambda: _order_verdicts_scan(web))


def _contradictions_scan(web: Any) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for rel in list(getattr(web, "relations", {}).values()):
        a = getattr(rel, "assertion", None)
        if not a:
            continue
        for pred, p in dict(dict(a).get("predicates") or {}).items():
            if _verdict(p) == "contested":
                found.append({"kind": "said both ways", "source": rel.source_word, "predicate": pred,
                              "target": rel.target_word})
    edges = order_edges(web)
    for (x, y) in sorted(edges):
        if x < y and (y, x) in edges:
            found.append({"kind": "order both ways", "source": x, "predicate": "come before", "target": y})
    return found


def contradictions(web: Any) -> List[Dict[str, Any]]:
    """What she holds that cannot all be so: a statement said and denied about equally (no correction
    having settled it), or two words each told to come after the other.  Resolved once, shared."""
    return _memo(web, "contradictions", lambda: _contradictions_scan(web), fresh=True)


def _not_sure(subject: str, rel: str, obj: str) -> Dict[str, Any]:
    return {"source": "aurora", "kind": "related_to", "target": subject, "strength": 1.3, "axis": "X",
            "learned_from": "inference", "asked": True, "derived": ["contradicted"], "basis": "contested",
            "lex": {"agent": "I", "action": "am not sure", "object": f"if {subject} is {rel} {obj}",
                    "predicate": "know", "n": "1", "denied": "False"}}


def _graph(edges: Mapping[Tuple[str, str], int]) -> Dict[str, List[str]]:
    g: Dict[str, List[str]] = {}
    for earlier, later in edges:
        g.setdefault(earlier, []).append(later)
        g.setdefault(later, [])
    return g


def later_than(edges: Mapping[Tuple[str, str], int], word: str) -> Dict[str, List[str]]:
    """Every word that comes after ``word``, nearest first, each with the chain
    from ``word`` to it (breadth-first, so a chain is the shortest one held)."""
    g = _graph(edges)
    word = str(word).lower()
    if word not in g:
        return {}
    seen: Dict[str, List[str]] = {}
    queue = deque([(word, [word])])
    while queue:
        cur, path = queue.popleft()
        for nxt in sorted(g.get(cur, ())):
            if nxt in seen or nxt == word:
                continue
            seen[nxt] = path + [nxt]
            queue.append((nxt, path + [nxt]))
    return seen


def earlier_than(edges: Mapping[Tuple[str, str], int], word: str) -> Dict[str, List[str]]:
    rev = {(later, earlier): n for (earlier, later), n in edges.items()}
    return later_than(rev, word)


# -----------------------------------------------------------------------------
# What she was told about kinds
# -----------------------------------------------------------------------------

def _kind_edges_scan(web: Any) -> Dict[Tuple[str, str], int]:
    """{(thing, kind): times said} from "<thing> is a <kind>"; denied is not held."""
    edges: Dict[Tuple[str, str], int] = {}
    for rel in list(getattr(web, "relations", {}).values()):
        a = getattr(rel, "assertion", None)
        if not a:
            continue
        p = dict(dict(a).get("predicates") or {}).get(KIND_PREDICATE)
        if not p:
            continue
        n, denied = int(dict(p).get("n", 0) or 0), int(dict(p).get("denied", 0) or 0)
        src = str(getattr(rel, "source_word", "") or "").lower()
        tgt = str(getattr(rel, "target_word", "") or "").lower()
        if _verdict(p) == "held" and src and tgt and src != tgt:
            edges[(src, tgt)] = max(1, n - denied)
    return edges


def kinds_of(edges: Mapping[Tuple[str, str], int], word: str) -> Dict[str, List[str]]:
    """Every kind ``word`` is (told directly or through what its kind is), nearest first."""
    g: Dict[str, List[str]] = {}
    for thing, kind in edges:
        g.setdefault(thing, []).append(kind)
    word = str(word).lower()
    seen: Dict[str, List[str]] = {}
    queue = deque([(word, [word])])
    while queue:
        cur, path = queue.popleft()
        for k in sorted(g.get(cur, ())):
            if k in seen or k == word:
                continue
            seen[k] = path + [k]
            queue.append((k, path + [k]))
    return seen


def set_role(web: Any, word: str, role: str) -> bool:
    """Give a word a role in her web, keeping the web's role index in step."""
    node = (getattr(web, "nodes", {}) or {}).get(str(word).lower())
    if node is None or role not in ROLE_NAMES or getattr(node, "role", "") == role:
        return False
    index = getattr(web, "_nodes_by_role", None)
    if index is not None:
        index[getattr(node, "role", "")].discard(node.word)
        index[role].add(node.word)
    node.role = role
    return True


def apply_kind(web: Any, thing: str, kind: str) -> bool:
    """She was told ``thing`` is a ``kind``.  When the kind is one of the roles a
    word can have, the word has that role: "run is a verb" makes run a verb."""
    return set_role(web, thing, str(kind).lower()) if str(kind).lower() in ROLE_NAMES else False


# -----------------------------------------------------------------------------
# What she was told about what things end (punctuation)
# -----------------------------------------------------------------------------

END_PREDICATES = frozenset({"end"})


def _end_edges_scan(web: Any) -> Dict[Tuple[str, str], int]:
    """{(ender, ended): times said} from "<ender> ends <ended>"."""
    edges: Dict[Tuple[str, str], int] = {}
    for rel in list(getattr(web, "relations", {}).values()):
        a = getattr(rel, "assertion", None)
        if not a:
            continue
        src = str(getattr(rel, "source_word", "") or "").lower()
        tgt = str(getattr(rel, "target_word", "") or "").lower()
        for pred, p in dict(dict(a).get("predicates") or {}).items():
            n, denied = int(dict(p).get("n", 0) or 0), int(dict(p).get("denied", 0) or 0)
            if pred in END_PREDICATES and _verdict(p) == "held" and src and tgt and src != tgt:
                edges[(src, tgt)] = max(1, n - denied)
    return edges


def _end_shape(toks: Sequence[str]) -> Dict[str, str]:
    """'what does "?" end?' -> {"ask": "ends", "of": "?"}; "what ends a question?" -> {"ask": "ended_by", "of": "question"}."""
    if not toks or toks[0] not in _QUESTION_WORDS:
        return {}
    if len(toks) >= 4 and toks[1] in ("does", "do") and toks[-1] in ("end", "close", "finish"):
        thing = _tail_word(toks[2:-1], _KIND_SKIP | {"mark"})
        return {"ask": "ends", "of": thing} if thing else {}
    if len(toks) >= 3 and toks[1] in ("ends", "end", "closes", "finishes"):
        thing = _tail_word(toks[2:], _KIND_SKIP)
        return {"ask": "ended_by", "of": thing} if thing else {}
    return {}


def _end_item(ender: str, ended: str) -> Dict[str, Any]:
    return {"source": ender, "kind": "related_to", "target": ended, "strength": 1.5, "axis": "B",
            "learned_from": "inference", "asked": True, "derived": [ender, ended],
            "lex": {"agent": ender, "action": "ends", "object": ended, "predicate": "end",
                    "n": "1", "denied": "False"}}


def _derive_end(web: Any, shape: Mapping[str, str]) -> List[Dict[str, Any]]:
    edges = end_edges(web)
    thing = shape["of"]
    if shape["ask"] == "ends":
        return [_end_item(e, d) for (e, d) in sorted(edges) if e == thing][:2]
    return [_end_item(e, d) for (e, d) in sorted(edges) if d == thing][:2]


# -----------------------------------------------------------------------------
# Reading an order question
# -----------------------------------------------------------------------------

_KIND_SKIP = frozenset({"the", "a", "an", "that", "this", "one", "thing", "ever", "also", "really"})


def _tail_word(tokens: Sequence[str], skip: frozenset = _FILLER) -> str:
    """The word a phrase is about: its last content word.  A lone letter is
    that letter ("after a"), as is one that labels the word before it ("the
    letter a"); "a" in front of a word is the article."""
    toks = list(tokens)
    if len(toks) == 1 and toks[0] not in _AUX and toks[0] not in ("a", "an", "the"):
        return toks[0]                       # "after one": a lone word is what it names, filler or not
    for i in range(len(toks) - 1, -1, -1):
        tok = toks[i]
        if len(tok) == 1 and tok.isalpha():
            if len(toks) == 1 or (i and toks[i - 1] not in ("a", "an", "the")):
                return tok
            continue
        if tok not in skip and tok not in _AUX:
            return tok
    return ""


def ask_shape(heard: str) -> Dict[str, str]:
    """What an order question asks, or {}:
        {"ask": "after",  "of": X}            what comes after X
        {"ask": "before", "of": X}            what comes before X
        {"ask": "test", "rel": "after"|"before", "subject": X, "object": Y}   is X after Y
    """
    text = str(heard or "")
    if "?" not in text and not re.match(r"\s*(what|which|who|is|are|does|do)\b", text, re.I):
        return {}
    toks = [t.lower() for t in _TOKEN.findall(text)]
    if len(toks) < 3:
        return {}
    # where the ordering word sits: "after"/"before", or the verbs "follow(s)"/"precede(s)"
    key, rel = -1, ""
    for i, t in enumerate(toks):
        if t in ("after", "before"):
            key, rel = i, t
            break
        if t in ("follow", "follows", "precede", "precedes"):
            key, rel = i, "after" if t.startswith("follow") else "before"
            # "what follows b" asks for what is AFTER b; the key verb names the asked direction
            break
    if key < 0:
        return _kind_shape(toks) or _end_shape(toks) or _fact_shape(toks)
    first = toks[0]
    verb_key = toks[key] in ("follow", "follows", "precede", "precedes")
    if first in _QUESTION_WORDS:
        subj_side = _tail_word(toks[1:key]) if not verb_key else ""
        obj = _tail_word(toks[key + 1:])
        if verb_key:
            # "what follows b": the asked thing follows b -> ask what is after b
            return {"ask": rel, "of": obj} if obj else {}
        # "what comes after b" / "what is after b"
        return {"ask": rel, "of": obj} if obj else {}
    if first in _AUX or first == "can" or first == "could":
        mid = [t for t in toks[1:key] if t not in ("come", "comes", "came")]
        subject = _tail_word(mid) if not verb_key else _tail_word(toks[1:key])
        obj = _tail_word(toks[key + 1:])
        if subject and obj and subject != obj:
            if verb_key:
                # "does b follow a": b is after a ; "does a precede b": a is before b
                return {"ask": "test", "rel": rel, "subject": subject, "object": obj}
            return {"ask": "test", "rel": rel, "subject": subject, "object": obj}
    return {}


def _fact_shape(toks: Sequence[str]) -> Dict[str, str]:
    """"does devlin like rain?" -> {"ask": "fact", "subject": devlin, "verb": like, "object": rain}.
    A third party and one thing; "do you ..." / "does it ..." are other questions (her senses, her state)."""
    if toks[0] not in ("does", "do", "did") or len(toks) < 4:
        return {}
    closed = _closed_words()
    subject, verb, rest = toks[1], toks[2], toks[3:]
    if subject in closed or verb in ("not", "n't") or subject in ("you", "i", "we", "it", "he", "she", "they"):
        return {}
    obj = _tail_word(rest)
    if not obj or obj in closed or obj == subject:
        return {}
    return {"ask": "fact", "subject": subject, "verb": verb, "object": obj}


def _closed_words() -> frozenset:
    from aurora_internal.aurora_confluence import _closed_class
    return _closed_class()


def _kind_shape(toks: Sequence[str]) -> Dict[str, str]:
    """"what is b?" -> {"ask": "kind", "of": b}; "is b a letter?" -> {"ask": "kind_test", ...}."""
    if toks[0] in _QUESTION_WORDS and len(toks) >= 3 and toks[1] in ("is", "are"):
        thing = _tail_word(toks[2:], _KIND_SKIP)
        return {"ask": "kind", "of": thing} if thing and thing not in ("that", "this", "it") else {}
    if toks[0] in ("is", "are") and len(toks) >= 4:
        for idx in range(len(toks) - 2, 1, -1):
            if toks[idx] in ("a", "an"):
                subject, kind = _tail_word(toks[1:idx], _KIND_SKIP), _tail_word(toks[idx + 1:], _KIND_SKIP)
                if subject and kind and subject != kind:
                    return {"ask": "kind_test", "subject": subject, "kind": kind}
    return {}


# -----------------------------------------------------------------------------
# What she was told holds WHEN something is so
# -----------------------------------------------------------------------------

def _content_forms(words: Iterable[str]) -> set:
    """Content words, with their base forms; what a statement is about."""
    from aurora_internal.aurora_propositional_understanding import _lemma
    from aurora_internal.aurora_confluence import _closed_class, _ing_bases
    closed = _closed_class()
    forms: set = set()
    for w in words:
        w = str(w).lower()
        if len(w) < 3 or w in closed or "'" in w:
            continue
        forms.add(w)
        try:
            forms.add(_lemma(w))
        except Exception:
            pass
        forms.update(_ing_bases(w))
    return forms


def _rules_scan(web: Any) -> List[Dict[str, Any]]:
    """Every "when" she was told: the relation (what she holds), its predicate,
    and the condition it was said to hold under."""
    out: List[Dict[str, Any]] = []
    for rel in list(getattr(web, "relations", {}).values()):
        a = getattr(rel, "assertion", None)
        if not a:
            continue
        for pred, p in dict(dict(a).get("predicates") or {}).items():
            n, denied = int(dict(p).get("n", 0) or 0), int(dict(p).get("denied", 0) or 0)
            if _verdict(p) != "held":
                continue
            for cond in list(dict(p).get("when") or []):
                out.append({"rel": rel, "predicate": pred, "when": dict(cond)})
    return out


def rules(web: Any) -> List[Dict[str, Any]]:
    return _memo(web, "rules", lambda: _rules_scan(web))


def _words_of(*parts: Any) -> List[str]:
    return [t.lower() for part in parts for t in _TOKEN.findall(str(part or ""))]


def _confirms(st: Mapping[str, Any], cond: Mapping[str, Any], speaker_now: str, self_now: str) -> bool:
    """Is this heard statement the condition actually being so?  Same act, same thing said of
    the same person, neither denied when the other is not -- and not a wish or a maybe."""
    from aurora_internal.aurora_propositional_understanding import _lemma, heads
    if bool(st.get("negated")) != bool(cond.get("negated")):
        return False
    act = lambda r: _lemma(str(r or "").split()[0].lower()) if str(r or "").split() else ""
    if not act(cond.get("relation")) or act(st.get("relation")) != act(cond.get("relation")):
        return False
    need = _content_forms(_words_of(cond.get("obj")))
    if need and not need <= _content_forms(_words_of(st.get("obj"))):
        return False
    who = [str(w) for w in (cond.get("who") or [])]
    if who:
        return bool(set(who) & set(heads(st.get("subject"), speaker=speaker_now, listener=self_now, acts=set())))
    return _content_forms(_words_of(cond.get("subject"))) == _content_forms(_words_of(st.get("subject")))


def fire(web: Any, heard: str, *, speaker_now: str = "", self_now: str = "") -> List[Dict[str, Any]]:
    """What she holds under a condition that has just been CONFIRMED in what was heard.
    A condition mentioned, asked about ("are you settled?"), supposed ("if you are settled"),
    wished or denied does not hold; only a plain statement of it by someone who can say so does
    (testimony: she was told, she did not observe it)."""
    from aurora_internal.aurora_propositional_understanding import lexicalize_assertion, statements_in
    held_rules = rules(web)
    if not held_rules:
        return []
    stated = [st for st in statements_in(heard, web=web)
              if not st.get("conditional") and not st.get("when") and not st.get("modality")]
    if not stated:
        return []
    out: List[Dict[str, Any]] = []
    for rule in held_rules:
        cond = rule["when"]
        if not any(_confirms(st, cond, speaker_now, self_now) for st in stated):
            continue
        rel, pred = rule["rel"], rule["predicate"]
        lex = lexicalize_assertion(rel, speaker_now=speaker_now, self_now=self_now, predicate=pred)
        if lex is None:
            continue
        out.append({"source": str(rel.source_word).lower(), "kind": "related_to",
                    "target": str(rel.target_word).lower(), "strength": 1.4, "axis": "A",
                    "learned_from": "rule", "asked": True, "basis": "told",
                    "derived": [str(cond.get("relation") or ""), str(cond.get("obj") or "")],
                    "lex": lex})
    return out


def _item(source: str, target: str, *, action: str, predicate: str, denied: bool, chain: Sequence[str]) -> Dict[str, Any]:
    return {"source": source, "kind": "precedes", "target": target, "strength": 1.5, "axis": "T",
            "learned_from": "inference", "asked": True, "derived": list(chain),
            "lex": {"agent": source, "action": action, "object": target, "predicate": predicate,
                    "n": "1", "denied": str(bool(denied))}}


def _derive(web: Any, heard: str, *, speaker_now: str = "", self_now: str = "") -> List[Dict[str, Any]]:
    """Statements she can state from what she was told about order, for the
    question just asked.  Empty when the question is not about order or she
    holds nothing that answers it."""
    if web is None:
        return []
    shape = ask_shape(heard)
    if not shape:
        return fire(web, heard, speaker_now=speaker_now, self_now=self_now)
    return _answer(web, shape) or _not_known(web, shape)


def _answer(web: Any, shape: Mapping[str, str]) -> List[Dict[str, Any]]:
    """What she can state from what she was told, for a question of a shape she can read."""
    ask = shape["ask"]
    if ask in ("kind", "kind_test"):
        return _derive_kind(web, shape)
    if ask in ("ends", "ended_by"):
        return _derive_end(web, shape)
    if ask == "fact":
        return _derive_fact(web, shape)
    edges = order_edges(web)
    if not edges and not order_verdicts(web):        # (told-and-denied is something she holds, though it is no edge)
        return []
    if ask == "after":
        x = shape["of"]
        nearest = _nearest(later_than(edges, x))
        return [_item(y, x, action="comes after", predicate="come after", denied=False, chain=[x] + path[1:])
                for y, path in nearest]
    if ask == "before":
        x = shape["of"]
        nearest = _nearest(earlier_than(edges, x))
        return [_item(y, x, action="comes before", predicate="come before", denied=False, chain=path)
                for y, path in nearest]
    if ask == "test":
        s, o, rel = shape["subject"], shape["object"], shape["rel"]
        a, b = (o, s) if rel == "after" else (s, o)          # a is earlier than b
        action = "is after" if rel == "after" else "is before"
        pred = "be after" if rel == "after" else "be before"
        direct = order_verdicts(web).get((a, b), "")
        forward, backward = b in later_than(edges, a), a in later_than(edges, b)
        # told both ways, or told one thing and its opposite is also in what she holds: not settled
        if direct == "contested" or (forward and backward) or (direct == "denied" and forward):
            return [_not_sure(s, shape["rel"], o)]
        if forward:
            return [_item(s, o, action=action, predicate=pred, denied=False, chain=later_than(edges, a)[b])]
        if direct == "denied" and not backward:
            return [_item(s, o, action=action.replace("is ", "is not ", 1), predicate=pred, denied=True,
                          chain=["told"])]
        if backward:
            # the other way round is what she was told: "a is not after d"
            return [_item(s, o, action=action.replace("is ", "is not ", 1), predicate=pred, denied=True,
                          chain=later_than(edges, b)[a])]
    return []


def _held_words(web: Any, domain: str) -> set:
    """The words she holds in a domain (order, kinds, marks): the things she was told about."""
    edges = {"order": order_edges, "kinds": kind_edges, "ends": end_edges}[domain](web)
    return {w for pair in edges for w in pair}


def _not_known(web: Any, shape: Mapping[str, str]) -> List[Dict[str, Any]]:
    """A question about something she holds, whose answer she was never told and cannot work
    out, is answered that she does not know: not left to a fallback seed, and never guessed
    (FIX-A136).  A word she holds nothing about is left alone: that is not this domain's question."""
    ask = shape["ask"]
    if ask in ("after", "before"):
        domain, words, what = "order", [shape["of"]], f"what comes {ask} {shape['of']}"
    elif ask == "test":
        domain, words = "order", [shape["subject"], shape["object"]]
        what = f"if {shape['subject']} is {shape['rel']} {shape['object']}"
    elif ask == "kind":
        domain, words, what = "kinds", [shape["of"]], f"what {shape['of']} is"
    elif ask == "kind_test":
        domain, words = "kinds", [shape["subject"]]
        what = f"if {shape['subject']} is a {shape['kind']}"
    elif ask == "ends":
        domain, words, what = "ends", [shape["of"]], f"what {shape['of']} ends"
    elif ask == "ended_by":
        domain, words, what = "ends", [shape["of"]], f"what ends {shape['of']}"
    else:
        return []
    held = _held_words(web, domain)
    if not held:
        return []
    # An order question needs only that she holds some order: what is told about "tuesday" in
    # no order she holds is not known (not a fallback seed).  Kinds and marks are claimed only
    # for words she holds, since other knowledge may answer "what is love?".
    if domain != "order" and not all(w in held for w in words):
        return []
    return [{"source": "aurora", "kind": "related_to", "target": words[0], "strength": 1.2, "axis": "X",
             "learned_from": "inference", "asked": True, "derived": ["not told"], "basis": "unknown",
             "lex": {"agent": "I", "action": "do not know", "object": what, "predicate": "know",
                     "n": "1", "denied": "True"}}]


def derive(web: Any, heard: str, *, speaker_now: str = "", self_now: str = "") -> List[Dict[str, Any]]:
    """Resolved once per (what was heard, who is speaking) for each state of what she knows;
    the gate and the confluence read the same resolution."""
    return _memo(web, ("derive", str(heard or ""), speaker_now, self_now),
                 lambda: _derive(web, heard, speaker_now=speaker_now, self_now=self_now), fresh=True)


def _derive_kind(web: Any, shape: Mapping[str, str]) -> List[Dict[str, Any]]:
    edges = kind_edges(web)
    if not edges:
        return []
    if shape["ask"] == "kind":
        thing = shape["of"]
        reach = kinds_of(edges, thing)
        return [_kind_item(thing, k, path) for k, path in sorted(reach.items(), key=lambda kp: (len(kp[1]), kp[0]))[:2]]
    thing, kind = shape["subject"], shape["kind"]
    reach = kinds_of(edges, thing)
    return [_kind_item(thing, kind, reach[kind])] if kind in reach else []


def _derive_fact(web: Any, shape: Mapping[str, str]) -> List[Dict[str, Any]]:
    """"Does devlin like rain?" from what she was told along devlin -> rain: yes (as it was said), no (it was
    denied), not sure (told and denied), and "I do not know" when she holds things about devlin but not that.
    Nothing is claimed about a word she holds nothing about: other knowledge may answer it."""
    from aurora_internal.aurora_propositional_understanding import (
        _lemma, lexicalize_assertion, standing)
    subject, obj = shape["subject"], shape["object"]
    lemma = _lemma(shape["verb"])
    about_subject = False
    for rel in list(getattr(web, "relations", {}).values()):
        if rel.source_word != subject or not getattr(rel, "assertion", None):
            continue
        about_subject = True
        if rel.target_word != obj:
            continue
        preds = dict(dict(rel.assertion).get("predicates") or {})
        if lemma not in preds:
            continue
        st = standing(rel, lemma)
        item_base = {"source": subject, "kind": "related_to", "target": obj, "strength": 1.5, "axis": "X",
                     "learned_from": "inference", "asked": True, "derived": ["told"]}
        if st["verdict"] == "contested":
            return [dict(item_base, derived=["contradicted"], basis="contested",
                         lex={"agent": "I", "action": "am not sure", "object": f"if {subject} {lemma}s {obj}",
                              "predicate": "know", "n": "1", "denied": "False"})]
        lex = lexicalize_assertion(rel, speaker_now="", self_now="", predicate=lemma)
        if lex:
            return [dict(item_base, lex=lex)]
    if not about_subject:
        return []
    return [{"source": "aurora", "kind": "related_to", "target": subject, "strength": 1.2, "axis": "X",
             "learned_from": "inference", "asked": True, "derived": ["not told"], "basis": "unknown",
             "lex": {"agent": "I", "action": "do not know", "object": f"if {subject} {lemma}s {obj}",
                     "predicate": "know", "n": "1", "denied": "True"}}]


def _kind_item(thing: str, kind: str, chain: Sequence[str]) -> Dict[str, Any]:
    return {"source": thing, "kind": "instance_of", "target": kind, "strength": 1.5, "axis": "B",
            "learned_from": "inference", "asked": True, "derived": list(chain),
            "lex": {"agent": thing, "action": "is a", "object": kind, "predicate": KIND_PREDICATE,
                    "n": "1", "denied": "False"}}


def _nearest(reach: Mapping[str, List[str]]) -> List[Tuple[str, List[str]]]:
    """The words at the shortest distance: what comes right after."""
    if not reach:
        return []
    best = min(len(path) for path in reach.values())
    return sorted(((w, p) for w, p in reach.items() if len(p) == best), key=lambda wp: wp[0])
