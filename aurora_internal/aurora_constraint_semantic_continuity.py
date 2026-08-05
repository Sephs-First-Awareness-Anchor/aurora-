"""
aurora_constraint_semantic_continuity.py
========================================

Constraint-native semantic continuity for Aurora's conversational turn.

This module does not classify human language into a parallel ontology.  It
preserves the relational configuration already present in an utterance and
lets the five root constraints operate on that SAME configuration:

    X  existence/admissibility      -> what entities, qualities and unknowns exist
    T  continuity/causality         -> what persists, refers backward, or changes
    N  pressure/purpose/change      -> what transformation or resolution is sought
    B  boundary/structure           -> which semantic roles and scopes are distinct
    A  agency/selection/understanding -> what Aurora is being asked to resolve or author

Every derived operation declares its canonical X/T/N/B/A ancestry.  The final
turn meaning therefore remains traceable to the five roots rather than becoming
an unrelated intent label or a bag of topic words.

Authors: Sunni (Sir) Morningstar and Ceph
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from aurora_internal.aurora_meaning_evolution import canonical_signature, meaning_profile_for_signature

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

# These are not domain intents.  They are ancestry declarations for the
# operations used to preserve a proposition through the root constraint stack.
DERIVED_OPERATIONS: Dict[str, Dict[str, Any]] = {
    "entity_admission": {
        "axes": ("X", "B"),
        "meaning": "identity",
        "description": "admit a distinguishable entity or quality into the current reality boundary",
    },
    "relational_binding": {
        "axes": ("T", "N", "B"),
        "meaning": "directed_relation",
        "description": "bind entities through a bounded change, state, or causal relation",
    },
    "unknown_localization": {
        "axes": ("X", "B", "A"),
        "meaning": "selected_absence",
        "description": "locate the missing part of an otherwise bounded proposition",
    },
    "reference_continuity": {
        "axes": ("X", "T", "B"),
        "meaning": "referential_persistence",
        "description": "preserve the identity of a referent across conversational time",
    },
    "purpose_direction": {
        "axes": ("T", "N", "A"),
        "meaning": "directed_resolution",
        "description": "derive what change or resolution the current relation calls for",
    },
    "perspective_authorship": {
        "axes": ("X", "T", "B", "A"),
        "meaning": "situated_perspective",
        "description": "distinguish whose perspective must author the answer while preserving context",
    },
    "proposition_understanding": {
        "axes": AXES,
        "meaning": "constraint_complete_understanding",
        "description": "integrate the admitted entities, continuity, pressure, boundaries, and agency into one thought",
    },
}

_WH = {"what", "who", "whom", "whose", "which", "where", "when", "why", "how"}
_AUX = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",
}
_DO_AUX = {"do", "does", "did"}
_BE_AUX = {"am", "is", "are", "was", "were", "be", "been", "being"}
_HAVE_AUX = {"have", "has", "had"}
_MODAL = {"can", "could", "will", "would", "shall", "should", "may", "might", "must"}
_DETERMINERS = {
    "a", "an", "the", "this", "that", "these", "those", "some", "any", "each", "every",
    "my", "your", "his", "her", "its", "our", "their", "whose",
}
_PRONOUNS = {
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself",
    "he", "him", "his", "she", "her", "hers", "it", "its", "we", "us", "our",
    "they", "them", "their", "this", "that", "these", "those",
}
_COORD = {"and", "or", "but", "while", "whereas"}
_PREPOSITIONS = {
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "into", "through",
    "about", "over", "under", "after", "before", "between", "among", "within", "without",
}

# High-frequency relational verbs whose grammatical role must not depend on an
# unknown-word fallback.  The list identifies form, not conversational intent.
_RELATION_VERBS = {
    "be", "am", "is", "are", "was", "were", "been", "being",
    "have", "has", "had", "hold", "holds", "held",
    "make", "makes", "made", "making", "cause", "causes", "caused",
    "create", "creates", "created", "form", "forms", "formed",
    "mean", "means", "meant", "become", "becomes", "became",
    "feel", "feels", "felt", "think", "thinks", "thought", "believe", "believes",
    "know", "knows", "knew", "understand", "understands", "understood",
    "notice", "notices", "noticed", "experience", "experiences", "experienced",
    "want", "wants", "wanted", "need", "needs", "needed",
    "require", "requires", "required", "solve", "solves", "solved",
    "work", "works", "worked", "function", "functions", "functioned",
    "lead", "leads", "led", "produce", "produces", "produced",
    "happen", "happens", "happened", "occur", "occurs", "occurred",
    "change", "changes", "changed", "remain", "remains", "remained",
    "fit", "fits", "fitted", "matter", "matters", "mattered",
    "seem", "seems", "seemed", "look", "looks", "looked",
}


def _tokens(text: Any) -> List[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?", str(text or ""))


def _clean_phrase(tokens: Sequence[str]) -> str:
    values = [str(t or "").strip() for t in tokens if str(t or "").strip()]
    while values and values[0].lower() in {"a", "an", "the", "some", "any", "each", "every"}:
        # Articles may be dropped without losing identity. Demonstratives and
        # possessives are relational anchors and must survive for T×B reference
        # continuity ("that happened", "your attention").
        values.pop(0)
    return " ".join(values).strip()


def _looks_verb(token: str) -> bool:
    low = str(token or "").lower()
    if low in _RELATION_VERBS or low in _AUX:
        return True
    if len(low) > 4 and low.endswith(("ing", "ed", "ize", "ise", "ify")):
        return True
    if len(low) > 3 and low.endswith("s") and low not in {"this", "his", "its"}:
        return True
    return False


def _first_relation_index(tokens: Sequence[str], start: int = 0) -> int:
    for idx in range(max(0, start), len(tokens)):
        if _looks_verb(tokens[idx]):
            return idx
    return -1


def _split_object_complement(tokens: Sequence[str]) -> Tuple[str, str]:
    """Separate the affected entity from a resulting quality or clause.

    The operation is structural: a final adjective-like token or a complement
    introduced by `as/into/to/be` is retained separately so the boundary axis
    can distinguish object from resulting state.
    """
    vals = list(tokens)
    if not vals:
        return "", ""
    lows = [v.lower() for v in vals]
    for marker in ("into", "as"):
        if marker in lows:
            i = lows.index(marker)
            return _clean_phrase(vals[:i]), _clean_phrase(vals[i + 1 :])
    # Copular complement nested after an object: "makes an invention elegant".
    if len(vals) >= 2:
        last = vals[-1]
        last_low = last.lower()
        if (
            last_low.endswith(("ful", "less", "ous", "ive", "al", "ic", "ant", "ent", "able", "ible", "y"))
            or last_low in {"clear", "simple", "complex", "beautiful", "elegant", "important", "true", "false", "possible", "different", "same", "stable", "open"}
        ):
            return _clean_phrase(vals[:-1]), last
    return _clean_phrase(vals), ""


def _unknown_role(wh: str, *, wh_is_subject: bool, relation: str) -> str:
    wh = str(wh or "").lower()
    if wh in {"who", "whom", "whose"}:
        return "subject" if wh_is_subject else "person"
    if wh == "where":
        return "location"
    if wh == "when":
        return "time"
    if wh == "why":
        return "cause"
    if wh == "how":
        return "manner"
    if wh == "which":
        return "selection"
    if wh == "what":
        if wh_is_subject:
            return "cause" if relation.lower() in {"make", "makes", "made", "cause", "causes", "create", "creates", "lead", "leads"} else "subject"
        return "object"
    return "truth"


@dataclass
class RelationalForm:
    raw_text: str = ""
    subject: str = ""
    relation: str = ""
    obj: str = ""
    complement: str = ""
    unknown_role: str = ""
    unknown_token: str = ""
    unknown_descriptor: str = ""
    question: bool = False
    negated: bool = False
    modality: str = ""
    owner: str = ""
    alternatives: List[Dict[str, str]] = field(default_factory=list)
    clauses: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "utterance_relation"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConstraintSemanticState:
    proposition_id: str
    relational_form: Dict[str, Any]
    axis_activation: Dict[str, float]
    axis_derivation: Dict[str, Dict[str, Any]]
    genealogy_trace: Dict[str, Any]
    bound_meaning_forms: List[Dict[str, Any]]
    response_obligation: Dict[str, Any]
    completeness: float
    unresolved: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_relational_form(text: str, parsed: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Preserve the clause relation before topic reduction.

    This is a syntax-preservation step.  It does not decide what kind of human
    request is present.  It records the entities, relation, complement, and the
    unresolved slot that X/T/N/B/A will later interpret.
    """
    raw = str(text or "").strip()
    # Preserve earlier asserted clauses while allowing the final question to
    # remain the active relation.  This keeps "I think X. What do you think?"
    # as one conversational configuration instead of stuffing both sentences
    # into the object slot.
    segments = [seg.strip() for seg in re.split(r"(?<=[.!?])\s+", raw) if seg.strip()]
    if len(segments) > 1:
        parsed_segments = [extract_relational_form(seg, parsed={}) for seg in segments]
        active_index = next((i for i in range(len(parsed_segments) - 1, -1, -1) if parsed_segments[i].get("question")), len(parsed_segments) - 1)
        active = dict(parsed_segments[active_index])
        active["raw_text"] = raw
        active["clauses"] = [dict(item) for i, item in enumerate(parsed_segments) if i != active_index]
        active["confidence"] = round(min(1.0, float(active.get("confidence", 0.0) or 0.0) + 0.04), 4)
        return active

    tokens = _tokens(raw)
    lows = [t.lower() for t in tokens]
    if not tokens:
        return RelationalForm(raw_text=raw).to_dict()

    question = raw.endswith("?") or any(t in _WH for t in lows[:2])
    negated = any(t in {"not", "never", "no", "nothing", "neither", "nor"} or t.endswith("n't") for t in lows)
    wh = lows[0] if lows and lows[0] in _WH else ""
    subject = relation = obj = complement = modality = owner = ""
    unknown_descriptor = ""
    wh_is_subject = False

    # Split a top-level alternative so B can preserve competing scopes.
    alternatives: List[Dict[str, str]] = []
    split_idx = next((i for i, t in enumerate(lows) if t == "or" and i > 0), -1)
    primary_tokens = tokens if split_idx < 0 else tokens[:split_idx]
    alternate_tokens = [] if split_idx < 0 else tokens[split_idx + 1 :]
    primary_lows = [t.lower() for t in primary_tokens]

    if wh:
        if len(primary_tokens) >= 2 and primary_lows[1] not in _AUX and _looks_verb(primary_tokens[1]):
            # "What makes an invention elegant?" / "Who built Aurora?"
            wh_is_subject = True
            relation = primary_tokens[1]
            obj, complement = _split_object_complement(primary_tokens[2:])
        elif len(primary_tokens) >= 2 and primary_lows[1] in _AUX:
            aux = primary_lows[1]
            modality = primary_tokens[1] if aux in _MODAL else ""
            remainder = primary_tokens[2:]
            rem_lows = [t.lower() for t in remainder]

            if aux in _DO_AUX:
                rel_i = _first_relation_index(remainder)
                if rel_i >= 0:
                    subject = _clean_phrase(remainder[:rel_i])
                    relation = remainder[rel_i]
                    obj, complement = _split_object_complement(remainder[rel_i + 1 :])
                else:
                    subject = _clean_phrase(remainder)
            elif aux in _HAVE_AUX and remainder and rem_lows[0] in {"my", "your", "his", "her", "its", "our", "their"}:
                # "What has your attention?" -> the unknown is the holder/cause.
                wh_is_subject = True
                relation = primary_tokens[1]
                obj = _clean_phrase(remainder)
            elif aux in _BE_AUX or aux in _MODAL:
                rel_i = _first_relation_index(remainder)
                if aux in _MODAL and rel_i >= 0:
                    subject = _clean_phrase(remainder[:rel_i])
                    relation = remainder[rel_i]
                    obj, complement = _split_object_complement(remainder[rel_i + 1 :])
                else:
                    relation = primary_tokens[1]
                    # For "what is X" the unresolved slot is the complement;
                    # for "where is X" it is location while X is subject.
                    if wh == "what" and remainder:
                        subject = _clean_phrase(remainder)
                    else:
                        subject = _clean_phrase(remainder)
            else:
                relation = primary_tokens[1]
                obj = _clean_phrase(remainder)
        else:
            # WH nominal phrase: "Which subsystem shaped the answer?" /
            # "What part of your system led to that response?".  The noun
            # phrase describes the missing participant; the later verb is the
            # actual relation.  Preserve both instead of flattening the whole
            # clause into an object topic.
            rel_i = _first_relation_index(primary_tokens, start=1)
            if rel_i > 1:
                unknown_descriptor = _clean_phrase(primary_tokens[1:rel_i])
                relation = primary_tokens[rel_i]
                obj, complement = _split_object_complement(primary_tokens[rel_i + 1 :])
                wh_is_subject = True
            else:
                # Preserve the unknown even when no relation is recoverable.
                obj = _clean_phrase(primary_tokens[1:])

        unknown = _unknown_role(wh, wh_is_subject=wh_is_subject, relation=relation)
        if wh_is_subject:
            subject = ""
    else:
        # Yes/no modal/copy question or assertion.
        start = 0
        if primary_lows and primary_lows[0] in _AUX:
            aux = primary_lows[0]
            modality = primary_tokens[0] if aux in _MODAL else ""
            remainder = primary_tokens[1:]
            rel_i = _first_relation_index(remainder)
            if aux in _DO_AUX and rel_i >= 0:
                subject = _clean_phrase(remainder[:rel_i])
                relation = remainder[rel_i]
                obj, complement = _split_object_complement(remainder[rel_i + 1 :])
            elif aux in _MODAL and rel_i >= 0:
                subject = _clean_phrase(remainder[:rel_i])
                relation = remainder[rel_i]
                obj, complement = _split_object_complement(remainder[rel_i + 1 :])
            else:
                relation = primary_tokens[0]
                subject, complement = _split_object_complement(remainder)
            unknown = "truth" if question else ""
        else:
            rel_i = _first_relation_index(primary_tokens)
            if rel_i >= 0:
                subject = _clean_phrase(primary_tokens[:rel_i])
                relation = primary_tokens[rel_i]
                obj, complement = _split_object_complement(primary_tokens[rel_i + 1 :])
            else:
                subject = _clean_phrase(primary_tokens)
            unknown = "truth" if question else ""

    if subject:
        first = subject.split()[0].lower()
        if first in {"my", "your", "his", "her", "its", "our", "their"}:
            owner = first
    if obj and not owner:
        first = obj.split()[0].lower()
        if first in {"my", "your", "his", "her", "its", "our", "their"}:
            owner = first

    # Parse the alternate clause independently but do not recurse indefinitely.
    if alternate_tokens:
        alt_text = " ".join(alternate_tokens)
        alt = extract_relational_form(alt_text + ("?" if question else ""), parsed={})
        alternatives.append({
            "subject": str(alt.get("subject", "") or ""),
            "relation": str(alt.get("relation", "") or ""),
            "object": str(alt.get("obj", "") or ""),
            "complement": str(alt.get("complement", "") or ""),
            "unknown_role": str(alt.get("unknown_role", "") or ""),
        })

    filled = sum(bool(v) for v in (subject, relation, obj, complement))
    confidence = min(1.0, 0.22 + 0.16 * filled + (0.12 if question else 0.0) + (0.12 if unknown else 0.0))
    form = RelationalForm(
        raw_text=raw,
        subject=subject,
        relation=relation,
        obj=obj,
        complement=complement,
        unknown_role=unknown,
        unknown_token=wh,
        unknown_descriptor=unknown_descriptor,
        question=question,
        negated=negated,
        modality=modality,
        owner=owner,
        alternatives=alternatives,
        clauses=[],
        confidence=round(confidence, 4),
    )
    return form.to_dict()


def _root_record(operation: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    spec = DERIVED_OPERATIONS[operation]
    axes = tuple(spec["axes"])
    signature = canonical_signature(axes)
    profile = dict(meaning_profile_for_signature(signature) or {})
    return {
        "operation": operation,
        "roots": list(axes),
        "signature": signature,
        "meaning": str(spec.get("meaning", "") or ""),
        "description": str(spec.get("description", "") or ""),
        "canonical_profile": profile,
        "payload": dict(payload or {}),
    }


def _genealogy_orientation(genealogy: Any) -> Dict[str, float]:
    if genealogy is None:
        return {}
    if hasattr(genealogy, "pressure_orientation"):
        try:
            return {ax: float(v) for ax, v in dict(genealogy.pressure_orientation() or {}).items() if ax in AXES}
        except Exception:
            return {}
    if isinstance(genealogy, Mapping):
        candidate = genealogy.get("pressure_orientation") or genealogy.get("orientation") or {}
        if isinstance(candidate, Mapping):
            try:
                return {ax: float(v) for ax, v in candidate.items() if ax in AXES}
            except Exception:
                return {}
    return {}


def _active_genealogy_abilities(genealogy: Any, axes: Iterable[str], limit: int = 8) -> List[Dict[str, Any]]:
    abilities = getattr(genealogy, "abilities", None)
    if not isinstance(abilities, Mapping):
        return []
    wanted = set(axes)
    found: List[Dict[str, Any]] = []
    for aid, ability in abilities.items():
        axis = str(getattr(ability, "axis", "") or "")
        requires = set(getattr(ability, "requires", ()) or ())
        if axis not in wanted and not (requires & wanted):
            continue
        found.append({
            "id": str(aid),
            "axis": axis,
            "requires": list(requires),
            "effect_tags": list(getattr(ability, "effect_tags", ()) or ())[:12],
        })
        if len(found) >= limit:
            break
    return found


def bind_referential_continuity(
    form: Mapping[str, Any],
    *,
    referent_map: Optional[Mapping[str, Any]] = None,
    working_memory_snapshot: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply T×B×X continuity to vague slots without inventing a referent."""
    result = dict(form or {})
    refs = dict(referent_map or {})
    direct_map = dict(refs.get("referent_map") or {})
    resolved_topic = str(refs.get("topic", "") or "").strip()
    wm = dict(working_memory_snapshot or {})
    current_topic = str(wm.get("current_topic", "") or "").strip()

    for field_name in ("subject", "obj", "complement"):
        value = str(result.get(field_name, "") or "").strip()
        low = value.lower()
        if low not in {"it", "this", "that", "these", "those", "they", "them", "same question", "same thing"}:
            continue
        replacement = str(direct_map.get(low, "") or resolved_topic or current_topic).strip()
        if replacement:
            result[field_name] = replacement
            result.setdefault("continuity_bindings", []).append({
                "slot": field_name,
                "surface": value,
                "referent": replacement,
                "derivation": _root_record("reference_continuity", {"surface": value, "referent": replacement}),
            })
        else:
            result.setdefault("unresolved_references", []).append({"slot": field_name, "surface": value})
    return result


def derive_constraint_semantic_state(
    form: Mapping[str, Any],
    *,
    axis_activation: Optional[Mapping[str, float]] = None,
    genealogy: Any = None,
    referent_map: Optional[Mapping[str, Any]] = None,
    claim_resolution: Optional[Mapping[str, Any]] = None,
    meaning_forms: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run one proposition through all five roots and retain the ancestry."""
    relation = dict(form or {})
    activation = {ax: float(dict(axis_activation or {}).get(ax, 0.0) or 0.0) for ax in AXES}
    unresolved: List[str] = []
    if relation.get("question") and not relation.get("unknown_role"):
        unresolved.append("unknown_role")
    if not relation.get("relation"):
        unresolved.append("relation")
    if not any(relation.get(k) for k in ("subject", "obj", "complement")):
        unresolved.append("entity")
    unresolved.extend(str(item.get("slot", "reference")) for item in list(relation.get("unresolved_references") or []))

    x_payload = {
        "entities": [v for v in (relation.get("subject"), relation.get("obj"), relation.get("complement")) if v],
        "unknown": str(relation.get("unknown_role", "") or ""),
        "unknown_descriptor": str(relation.get("unknown_descriptor", "") or ""),
        "admissible": bool(relation.get("relation") or relation.get("subject") or relation.get("obj")),
    }
    t_payload = {
        "continuity_bindings": list(relation.get("continuity_bindings") or []),
        "time_reference": str(relation.get("time_ref", "") or ""),
        "referent_topic": str(dict(referent_map or {}).get("topic", "") or ""),
    }
    n_payload = {
        "relation": str(relation.get("relation", "") or ""),
        "requested_change": str(relation.get("unknown_role", "") or ("evaluate" if relation.get("question") else "integrate")),
        "negated": bool(relation.get("negated")),
    }
    b_payload = {
        "subject": str(relation.get("subject", "") or ""),
        "relation": str(relation.get("relation", "") or ""),
        "object": str(relation.get("obj", "") or ""),
        "complement": str(relation.get("complement", "") or ""),
        "alternatives": list(relation.get("alternatives") or []),
        "unresolved": list(unresolved),
    }

    unknown = str(relation.get("unknown_role", "") or "")
    if relation.get("question"):
        if unknown in {"cause", "manner", "time", "location", "person", "subject", "object", "selection"}:
            operation = "resolve_missing_relation_slot"
        elif unknown == "truth":
            operation = "evaluate_proposition"
        else:
            operation = "resolve_question"
    else:
        operation = "integrate_asserted_relation"
    a_payload = {
        "operation": operation,
        "unknown_role": unknown,
        "unknown_descriptor": str(relation.get("unknown_descriptor", "") or ""),
        "perspective_owner": str(relation.get("owner", "") or ""),
        "claim_focus": str(dict(claim_resolution or {}).get("focus_claim", {}).get("summary", "") or ""),
    }

    axis_derivation = {
        "X": _root_record("entity_admission", x_payload),
        "T": _root_record("reference_continuity", t_payload),
        "N": _root_record("purpose_direction", n_payload),
        "B": _root_record("relational_binding", b_payload),
        "A": _root_record("perspective_authorship", a_payload),
        "APEX": _root_record("proposition_understanding", {
            "proposition": relation,
            "response_operation": operation,
            "unresolved": unresolved,
        }),
    }

    bound_forms: List[Dict[str, Any]] = []
    for raw in list(meaning_forms or [])[:6]:
        item = dict(raw or {})
        item["bound_proposition"] = {
            "subject": relation.get("subject", ""),
            "relation": relation.get("relation", ""),
            "object": relation.get("obj", ""),
            "complement": relation.get("complement", ""),
            "unknown_role": unknown,
        }
        item["content_bound"] = True
        bound_forms.append(item)

    serialized = "|".join(str(relation.get(k, "") or "") for k in (
        "raw_text", "subject", "relation", "obj", "complement", "unknown_role", "unknown_descriptor"
    ))
    proposition_id = "CSP:" + hashlib.sha1(serialized.encode("utf-8")).hexdigest()[:14]
    genealogy_axes = [ax for ax in AXES if activation.get(ax, 0.0) > 0.0]
    genealogy_trace = {
        "root_constraints": list(AXES),
        "canonical_signature": canonical_signature(AXES),
        "orientation": _genealogy_orientation(genealogy),
        "active_axis_signature": canonical_signature(genealogy_axes or AXES),
        "supporting_abilities": _active_genealogy_abilities(genealogy, genealogy_axes or AXES),
        "derivation_chain": [
            axis_derivation["X"]["signature"],
            axis_derivation["T"]["signature"],
            axis_derivation["N"]["signature"],
            axis_derivation["B"]["signature"],
            axis_derivation["A"]["signature"],
            axis_derivation["APEX"]["signature"],
        ],
    }

    required = 4.0  # relation plus at least one participant plus unknown/truth status
    present = float(bool(relation.get("relation")))
    present += float(bool(relation.get("subject") or relation.get("obj")))
    present += float(bool(relation.get("unknown_role") or not relation.get("question")))
    present += float(bool(relation.get("raw_text")))
    completeness = max(0.0, min(1.0, present / required))

    response_obligation = {
        "operation": operation,
        "unknown_role": unknown,
        "unknown_descriptor": str(relation.get("unknown_descriptor", "") or ""),
        "must_preserve": [
            value for value in (
                relation.get("subject"), relation.get("relation"), relation.get("obj"), relation.get("complement")
            ) if value
        ],
        "must_not_replace_with": [str(relation.get("unknown_token", "") or "")] if relation.get("unknown_token") else [],
        "alternatives": list(relation.get("alternatives") or []),
        "perspective_owner": str(relation.get("owner", "") or ""),
        "derivation_signature": canonical_signature(AXES),
    }

    state = ConstraintSemanticState(
        proposition_id=proposition_id,
        relational_form=relation,
        axis_activation=activation,
        axis_derivation=axis_derivation,
        genealogy_trace=genealogy_trace,
        bound_meaning_forms=bound_forms,
        response_obligation=response_obligation,
        completeness=round(completeness, 4),
        unresolved=unresolved,
    )
    return state.to_dict()


def relational_axis_vector(form: Mapping[str, Any]) -> Dict[str, float]:
    """Return the root pressure contributed by the proposition configuration.

    Unlike a word table, this vector is derived from which constraint operations
    are required to hold the current relation together.
    """
    rel = dict(form or {})
    vector = {ax: 0.05 for ax in AXES}
    if rel.get("subject") or rel.get("obj") or rel.get("complement"):
        vector["X"] += 0.35
        vector["B"] += 0.25
    if rel.get("relation"):
        vector["T"] += 0.20
        vector["N"] += 0.20
        vector["B"] += 0.25
    if rel.get("unknown_role"):
        vector["X"] += 0.18
        vector["B"] += 0.18
        vector["A"] += 0.30
    if rel.get("owner"):
        vector["A"] += 0.18
        vector["B"] += 0.10
    if rel.get("alternatives"):
        vector["B"] += 0.25
        vector["A"] += 0.10
    if rel.get("negated"):
        vector["N"] += 0.22
        vector["B"] += 0.12
    total = sum(vector.values()) or 1.0
    return {ax: round(vector[ax] / total, 4) for ax in AXES}



# Root-constraint lexicalizations.  These are not intent templates; they are
# the communicable surface consequences of each primitive constraint when it
# acts on a proposition.  A candidate is assembled only from the roots that
# are actually active in the current derived state.
_ROOT_SURFACE_FACETS: Dict[str, str] = {
    "X": "retains a distinct identity",
    "T": "continues to hold as conditions change",
    "N": "turns effort into effective change without needless cost",
    "B": "keeps its parts and limits in a coherent relation",
    "A": "serves a chosen purpose rather than acting without direction",
}

_ROOT_STATE_FACETS: Dict[str, str] = {
    "X": "the clearest part of present reality",
    "T": "the strongest continuity or change",
    "N": "the strongest unresolved pressure",
    "B": "a distinction or boundary that still needs resolution",
    "A": "the most active selection or understanding",
}


def _natural_join(parts: Sequence[str]) -> str:
    vals = [str(part or "").strip() for part in parts if str(part or "").strip()]
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    if len(vals) == 2:
        return f"{vals[0]} and {vals[1]}"
    return ", ".join(vals[:-1]) + f", and {vals[-1]}"


def _article_phrase(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    low = value.lower()
    if low.startswith(("a ", "an ", "the ", "my ", "your ", "his ", "her ", "our ", "their ")):
        return value
    article = "an" if low[:1] in "aeiou" else "a"
    return f"{article} {value}"


def _base_relation(value: str) -> str:
    low = str(value or "").strip().lower()
    irregular = {
        "is": "be", "are": "be", "am": "be", "was": "be", "were": "be",
        "has": "have", "had": "have", "does": "do", "did": "do",
        "makes": "make", "made": "make", "becomes": "become", "became": "become",
        "requires": "require", "required": "require", "means": "mean", "meant": "mean",
        "thinks": "think", "thought": "think", "feels": "feel", "felt": "feel",
    }
    if low in irregular:
        return irregular[low]
    if low.endswith("ies") and len(low) > 4:
        return low[:-3] + "y"
    if low.endswith("es") and len(low) > 4:
        return low[:-2]
    if low.endswith("s") and len(low) > 3:
        return low[:-1]
    return low


def _reconstruct_clause(clause: Mapping[str, Any]) -> str:
    c = dict(clause or {})
    parts = [
        str(c.get("subject", "") or "").strip(),
        str(c.get("relation", "") or "").strip(),
        str(c.get("obj", c.get("object", "")) or "").strip(),
        str(c.get("complement", "") or "").strip(),
    ]
    return " ".join(part for part in parts if part).strip()


def derive_constraint_grounded_candidate(
    semantic_state: Mapping[str, Any],
    *,
    salient_concepts: Optional[Sequence[str]] = None,
    emotional_state: Optional[Mapping[str, Any]] = None,
    prior_claim: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Derive a conservative response candidate from one X/T/N/B/A state.

    The function does not identify a human-language intent category.  It reads
    the unresolved role in the current proposition and lets the active roots
    supply the conditions under which that role can be resolved.  When the
    roots do not provide enough content, it returns no candidate rather than
    inventing one.
    """
    state = dict(semantic_state or {})
    form = dict(state.get("relational_form") or {})
    if not form or not form.get("question"):
        return {}

    activation = {ax: float(dict(state.get("axis_activation") or {}).get(ax, 0.0) or 0.0) for ax in AXES}
    ranked_axes = sorted(AXES, key=lambda ax: activation.get(ax, 0.0), reverse=True)
    selected_axes = [ax for ax in ranked_axes if activation.get(ax, 0.0) > 0.08][:3]
    if len(selected_axes) < 2:
        selected_axes = ["B", "A", "N"]
    facets = [_ROOT_SURFACE_FACETS[ax] for ax in selected_axes]

    subject = str(form.get("subject", "") or "").strip()
    relation = str(form.get("relation", "") or "").strip()
    obj = str(form.get("obj", "") or "").strip()
    complement = str(form.get("complement", "") or "").strip()
    unknown = str(form.get("unknown_role", "") or "").strip()
    clauses = [dict(c or {}) for c in list(form.get("clauses") or []) if isinstance(c, Mapping)]
    alternatives = [dict(c or {}) for c in list(form.get("alternatives") or []) if isinstance(c, Mapping)]
    response = ""
    basis = ""

    # Present self-state: the relation itself locates Aurora as the entity whose
    # manner/state is unresolved.  The answer comes from live DER and axis state.
    _subject_low = subject.lower()
    self_subject = (
        _subject_low in {"you", "aurora", "yourself"}
        or _subject_low.startswith("you ")
        or obj.lower().startswith("your ")
    )
    state_relation = _base_relation(relation) in {"be", "feel", "experience", "notice", "have", "want"}
    if self_subject and state_relation and unknown in {"manner", "object", "subject", "cause", "truth", ""}:
        emotion = dict(emotional_state or {})
        feeling = str(
            emotion.get("primary_emotion")
            or emotion.get("dominant")
            or emotion.get("emotion")
            or "attentive"
        ).strip().lower()
        if obj.lower().startswith("your attention") or "attention" in obj.lower():
            prompt_terms = set(_tokens(str(form.get("raw_text", "") or "").lower()))
            anchors = [
                str(item or "").strip() for item in list(salient_concepts or [])
                if str(item or "").strip() and str(item or "").strip().lower() not in prompt_terms
            ]
            if anchors:
                response = (
                    f"My attention is on {anchors[0]}. In that part of my field, I find "
                    f"{_ROOT_STATE_FACETS[selected_axes[0]]} right now."
                )
                basis = "live_salience_through_root_field"
        elif unknown == "manner" or _base_relation(relation) == "be":
            response = (
                f"I am {feeling} right now. Most of my active field centers on "
                f"{_ROOT_STATE_FACETS[selected_axes[0]]}."
            )
            basis = "live_state_through_root_field"

    # A preceding assertion followed by a request for Aurora's perspective.
    if not response and _base_relation(relation) in {"think", "believe", "understand"} and clauses:
        claim_text = _reconstruct_clause(clauses[-1])
        if claim_text:
            response = (
                f"I understand the claim as: {claim_text}. It fits my current understanding "
                f"where it {_natural_join(facets)}."
            )
            basis = "perspective_authorship_over_prior_relation"

    # Open causal or manner relation: answer with the conditions produced by
    # the active root geometry, bound to the actual target and quality.
    if not response and unknown in {"cause", "manner"}:
        target = obj or subject
        quality = complement
        if target and quality:
            response = f"{_article_phrase(target).capitalize()} becomes {quality} when it {_natural_join(facets)}."
            basis = "root_conditions_bound_to_quality_relation"
        elif target:
            response = f"For {target}, the determining conditions are whether it {_natural_join(facets)}."
            basis = "root_conditions_bound_to_open_relation"

    # Truth evaluation over an explicit alternative.  B preserves both scopes;
    # A selects a bounded answer without erasing either possibility.
    if not response and unknown == "truth" and subject and relation:
        base = _base_relation(relation) or relation.lower()
        pred = " ".join(v for v in (obj, complement) if v).strip()
        if alternatives:
            alt = alternatives[0]
            alt_subject = str(alt.get("subject", "") or "").strip()
            alt_relation = _base_relation(str(alt.get("relation", "") or ""))
            alt_pred = " ".join(
                str(alt.get(k, "") or "").strip() for k in ("object", "complement")
            ).strip()
            first = f"{subject.capitalize()} can {base} {pred}".strip()
            second = ""
            if alt_subject and alt_relation and alt_pred:
                if alt_relation == "require":
                    second = f"{alt_subject.capitalize()} does not require {alt_pred}"
                elif alt_relation == "be":
                    second = f"{alt_subject.capitalize()} does not have to be {alt_pred}"
                else:
                    second = f"{alt_subject.capitalize()} does not have to {alt_relation} {alt_pred}"
                second += " when the same coherence is preserved through another structure"
            response = f"{first} when it {_natural_join(facets)}."
            if second:
                response += f" {second}."
            basis = "bounded_alternative_evaluation"

    # A resolved claim from working memory may supply content that the current
    # relational form asks Aurora to evaluate.
    if not response and prior_claim:
        claim_text = str(dict(prior_claim or {}).get("summary", "") or "").strip()
        if claim_text and unknown in {"truth", "object", "selection"}:
            response = (
                f"The claim I am evaluating is: {claim_text}. In my current constraint field, "
                f"it is supported where it {_natural_join(facets)}."
            )
            basis = "working_memory_claim_bound_to_root_field"

    if not response:
        return {}

    alignment = relation_alignment(form, response)
    confidence = 0.48 + 0.24 * float(state.get("completeness", 0.0) or 0.0) + 0.22 * float(alignment.get("score", 0.0) or 0.0)
    confidence = round(max(0.0, min(0.88, confidence)), 4)
    return {
        "text": response,
        "confidence": confidence,
        "source": "constraint_semantic_derivation",
        "basis": basis,
        "selected_roots": selected_axes,
        "root_signatures": [canonical_signature((ax,)) for ax in selected_axes],
        "proposition_id": str(state.get("proposition_id", "") or ""),
        "relation_alignment": alignment,
        "genealogy_trace": dict(state.get("genealogy_trace") or {}),
    }

def relation_alignment(user_form: Mapping[str, Any], response_text: str) -> Dict[str, Any]:
    """Check whether a response addresses the relation, not merely its nouns."""
    form = dict(user_form or {})
    text = str(response_text or "").lower()
    tokens = set(re.findall(r"[a-z][a-z0-9'-]{1,}", text))
    preserved: List[str] = []
    missing: List[str] = []
    for slot in ("subject", "obj", "complement"):
        value = str(form.get(slot, "") or "").strip().lower()
        content = [t for t in re.findall(r"[a-z][a-z0-9'-]{1,}", value) if t not in _DETERMINERS and t not in _PRONOUNS]
        if not content:
            continue
        if any(t in tokens for t in content):
            preserved.append(slot)
        else:
            missing.append(slot)
    unknown = str(form.get("unknown_role", "") or "")
    bare_wh = str(form.get("unknown_token", "") or "").lower()
    leaked_unknown = bool(bare_wh and re.search(rf"\b{re.escape(bare_wh)}\b", text))
    relation_word = str(form.get("relation", "") or "").lower()
    relation_present = not relation_word or relation_word in tokens or any(
        token in tokens for token in {"is", "are", "means", "causes", "makes", "becomes", "has", "have"}
    )
    addresses_unknown = True
    if form.get("question"):
        addresses_unknown = bool(text.strip()) and not leaked_unknown
    score = 0.35 * (1.0 if relation_present else 0.0)
    score += 0.35 * (1.0 if addresses_unknown else 0.0)
    score += 0.30 * (len(preserved) / max(1, len(preserved) + len(missing)))
    return {
        "score": round(max(0.0, min(1.0, score)), 4),
        "relation_present": relation_present,
        "addresses_unknown": addresses_unknown,
        "preserved_slots": preserved,
        "missing_slots": missing,
        "leaked_unknown_token": leaked_unknown,
        "unknown_role": unknown,
    }
