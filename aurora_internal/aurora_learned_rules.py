# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_learned_rules.py -- what a learned statement can DO (FIX-A133).

A statement she learned ("The letter c comes after the letter b.") is stored as
a relation with the predicate said along it.  Until now only speech read it back.
This module lets her REASON from what she was told:

    ORDER      later / earlier, chained:  b after a, c after b  =>  c after a
               answers "what comes after b?", "is c after a?"

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

# The subject is LATER than the object / EARLIER than the object.
LATER_PREDICATES = frozenset({"follow", "come after", "be after", "succeed"})
EARLIER_PREDICATES = frozenset({"precede", "come before", "be before"})

_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*")
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

def order_edges(web: Any) -> Dict[Tuple[str, str], int]:
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
            if n <= 0 or denied * 2 >= n:
                continue
            if pred in LATER_PREDICATES:
                key = (tgt, src)
            elif pred in EARLIER_PREDICATES:
                key = (src, tgt)
            else:
                continue
            edges[key] = edges.get(key, 0) + n - denied
    return edges


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
# Reading an order question
# -----------------------------------------------------------------------------

def _tail_word(tokens: Sequence[str]) -> str:
    """The word a phrase is about: its last content word.  A lone letter is
    that letter ("after a"), as is one that labels the word before it ("the
    letter a"); "a" in front of a word is the article."""
    toks = list(tokens)
    for i in range(len(toks) - 1, -1, -1):
        tok = toks[i]
        if len(tok) == 1 and tok.isalpha():
            if len(toks) == 1 or (i and toks[i - 1] not in ("a", "an", "the")):
                return tok
            continue
        if tok not in _FILLER and tok not in _AUX:
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
        return {}
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


# -----------------------------------------------------------------------------
# What she can say from it
# -----------------------------------------------------------------------------

def _item(source: str, target: str, *, action: str, predicate: str, denied: bool, chain: Sequence[str]) -> Dict[str, Any]:
    return {"source": source, "kind": "precedes", "target": target, "strength": 1.5, "axis": "T",
            "learned_from": "inference", "asked": True, "derived": list(chain),
            "lex": {"agent": source, "action": action, "object": target, "predicate": predicate,
                    "n": "1", "denied": str(bool(denied))}}


def derive(web: Any, heard: str) -> List[Dict[str, Any]]:
    """Statements she can state from what she was told about order, for the
    question just asked.  Empty when the question is not about order or she
    holds nothing that answers it."""
    shape = ask_shape(heard)
    if not shape or web is None:
        return []
    edges = order_edges(web)
    if not edges:
        return []
    ask = shape["ask"]
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
        if b in later_than(edges, a):
            return [_item(s, o, action=action, predicate=pred, denied=False, chain=later_than(edges, a)[b])]
        if a in later_than(edges, b):
            # the other way round is what she was told: "a is not after d"
            return [_item(s, o, action=action.replace("is ", "is not ", 1), predicate=pred, denied=True,
                          chain=later_than(edges, b)[a])]
    return []


def _nearest(reach: Mapping[str, List[str]]) -> List[Tuple[str, List[str]]]:
    """The words at the shortest distance: what comes right after."""
    if not reach:
        return []
    best = min(len(path) for path in reach.values())
    return sorted(((w, p) for w, p in reach.items() if len(p) == best), key=lambda wp: wp[0])
