# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Function words (and, or, but, that, ...) as members of joined generalizations, from her own lexical signals (Sir, 2026-11-15).

The words that every sentence leans on are the noisiest crystals: tied to everything, so tied to nothing in particular.  What sets them apart is not a
label but what they do, and she already has three records of that.  This module turns each into association evidence, with the standing it has earned,
and lets the promotion module find the generalization that joins them.  Isolated: plain mappings in, an `AssociationStore` out; nothing running imports it.

  * the pragmatic role groups (`_WORD_ROLES`: and -> addition, but -> contrast, because -> consequence, ...) are a hand-authored scaffold.  They are kept so
    the structure is visible, and are NOT counted: reading a lookup is not having lived it.  Source `lexical_scaffold`.
  * the word classes she found herself (`LexicalStructure`: words whose successors are alike) are counted, as strongly as they have been re-found.
    Source `lexical_class`.
  * the grounding candidates (`AuroraLexicalGrounding`: a structural applicability family per word) count only through the evidence they earned by
    consequence; evidence whose provenance is the inherited scaffold is not counted.  Source `lexical_grounding`.
  * a role group that falls inside a found class joins it: the class generalizes over the groups it holds, by the share of the group it covers.

No English label is stored as a meaning (Build 771): a generalization is named by what it is (`pragmatic:addition`, `lexclass:L0@2`, `lexfam:...`), and a
caller may add a name of its own.  Every strength is a degree; nothing is cut off.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from aurora_internal.crystal_associations import AssociationStore

SCAFFOLD_PROVENANCE = "inherited_scaffold"


def _degree(x: float, k: float = 1.0) -> float:
    x = max(0.0, float(x))
    return x / (x + k)


def role_id(role: str) -> str:
    return f"pragmatic:{role}"


def class_id(identity: str) -> str:
    return f"lexclass:{identity}"


def family_id(family: str) -> str:
    return f"lexfam:{family}"


def place_scaffold(store: AssociationStore, role_of: Mapping[str, str]) -> int:
    """word -> `is_a` its pragmatic role group, from the hand-authored lookup.  Kept, never counted."""
    n = 0
    for word, role in sorted(role_of.items()):
        n += bool(store.add(str(word), role_id(str(role)), "is_a", ref=f"scaffold:{word}:{role}", source="lexical_scaffold", strength=1.0))
    return n


def place_classes(store: AssociationStore, classes: Mapping[str, Iterable[str]], confirmations: Optional[Mapping[str, int]] = None) -> int:
    """Each word class she found (identity -> members), counted at the degree its re-finding earns: one finding is half, each further one more."""
    n = 0
    for identity, members in sorted(classes.items()):
        st = _degree((confirmations or {}).get(identity, 1))
        for w in sorted({str(m) for m in members}):
            n += bool(store.add(w, class_id(identity), "is_a", ref=f"class:{identity}:{w}", source="lexical_class", strength=st))
    return n


def place_families(store: AssociationStore, candidates: Iterable[Mapping[str, Any]]) -> int:
    """Each grounding candidate puts its word in its applicability family.  The weight is the evidence she earned (provenance other than the inherited
    scaffold); a candidate with none is kept as scaffold and not counted."""
    n = 0
    for c in candidates:
        word, fam = str(c.get("word") or ""), str(c.get("applicability_family") or "")
        if not word or not fam:
            continue
        earned = sum(1 for e in c.get("evidence") or [] if str(e.get("provenance") or "") != SCAFFOLD_PROVENANCE)
        ref = f"family:{fam}:{word}:{c.get('candidate_id', '')}"
        if earned:
            n += bool(store.add(word, family_id(fam), "is_a", ref=ref, source="lexical_grounding", strength=_degree(earned), weight=float(earned)))
        else:
            n += bool(store.add(word, family_id(fam), "is_a", ref=ref, source="lexical_scaffold", strength=1.0))
    return n


def join_groups(store: AssociationStore, role_of: Mapping[str, str], classes: Mapping[str, Iterable[str]],
                confirmations: Optional[Mapping[str, int]] = None) -> int:
    """A role group generalizes up into a class that holds it: `pragmatic:<role>` `is_a` `lexclass:<id>`, by the share of the group's words the class covers,
    at the class's own standing.  A group the class does not touch does not join it.  This is how groups of different roles (addition, contrast,
    consequence) that she finds to behave alike become ONE generalization."""
    groups: Dict[str, set] = {}
    for w, r in role_of.items():
        groups.setdefault(str(r), set()).add(str(w))
    n = 0
    for identity, members in sorted(classes.items()):
        mem = {str(m) for m in members}
        st = _degree((confirmations or {}).get(identity, 1))
        for role, words in sorted(groups.items()):
            share = len(words & mem) / len(words)
            if share > 0.0:
                n += bool(store.add(role_id(role), class_id(identity), "is_a", ref=f"join:{role}:{identity}", source="lexical_class",
                                    strength=share * st))
    return n


def members_of_generalization(store: AssociationStore, g: str) -> Dict[str, float]:
    """What a generalization holds, with the counted degree it is held to (a scaffold-only member has none)."""
    return dict(store.incoming(g, "is_a"))


def generalizations(store: AssociationStore, word: str) -> List[str]:
    """The lexical generalizations a word is counted into, strongest first."""
    conn = store.connections_for(word)
    return [g for g, _ in sorted(conn.items(), key=lambda kv: (-kv[1], kv[0])) if g.startswith(("pragmatic:", "lexclass:", "lexfam:"))]
