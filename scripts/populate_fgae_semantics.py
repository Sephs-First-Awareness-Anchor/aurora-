#!/usr/bin/env python3
"""Populate Aurora's manifold slots with FGAE semantic entries.

This is a deterministic data population pass for FGAE_SPECIFICATION.md.  It
does not recompute or modify slot geometry; it derives the semantic layer from
the existing NonComp identity and slot properties.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Tuple


MANIFOLD_DIR = Path("aurora_manifold_directory")
INDEX_FILE = MANIFOLD_DIR / "_index.json"

DOMAIN_FIELDS: Dict[str, Dict[str, Any]] = {
    "X": {
        "domain": "Information",
        "anchor": "Information",
        "terms": [
            "signal",
            "presence",
            "evidence",
            "registration",
            "trace",
            "visibility",
            "occurrence",
            "record",
            "salience",
            "fact",
            "instance",
            "absence",
        ],
    },
    "T": {
        "domain": "Belief",
        "anchor": "Belief",
        "terms": [
            "continuity",
            "expectation",
            "memory",
            "anticipation",
            "stance",
            "revision",
            "persistence",
            "sequence",
            "direction",
            "commitment",
            "drift",
            "stability",
        ],
    },
    "N": {
        "domain": "Purpose",
        "anchor": "Purpose",
        "terms": [
            "energy",
            "value",
            "effort",
            "yield",
            "burden",
            "resource",
            "investment",
            "load",
            "relief",
            "sustainability",
            "balance",
            "motivation",
        ],
    },
    "B": {
        "domain": "Meaning",
        "anchor": "Meaning",
        "terms": [
            "boundary",
            "distinction",
            "frame",
            "context",
            "clarity",
            "ambiguity",
            "scope",
            "edge",
            "category",
            "interpretation",
            "limit",
            "membership",
        ],
    },
    "A": {
        "domain": "Understanding",
        "anchor": "Understanding",
        "terms": [
            "agency",
            "ownership",
            "choice",
            "intention",
            "accountability",
            "claim",
            "responsibility",
            "decision",
            "authority",
            "correction",
            "judgment",
            "answerability",
        ],
    },
}

CLUSTER_CHARACTER: Dict[str, str] = {
    "IDENTITY": "self-referential identity",
    "ORIENTATION": "directional stance",
    "INTENSITY": "magnitude and force",
    "ECONOMY": "cost and value",
    "CONTRAST": "distinction and boundary",
    "CROSS_RULE": "cross-constraint rule transfer",
}

CLUSTER_TERMS: Dict[str, List[str]] = {
    "IDENTITY": ["self", "identity", "nature", "native center", "own-form"],
    "ORIENTATION": ["stance", "direction", "lean", "towardness", "orientation"],
    "INTENSITY": ["weight", "force", "amplitude", "pressure", "magnitude"],
    "ECONOMY": ["cost", "yield", "burden", "value", "expenditure"],
    "CONTRAST": ["boundary", "difference", "edge", "separation", "contrast"],
    "CROSS_RULE": ["translation", "transfer", "bridge", "cross-rule", "lens"],
}

DIMENSION_TERMS: Dict[str, List[str]] = {
    "OPERATOR": ["operation", "activation", "agency", "rule", "application"],
    "POLARITY": ["orientation", "lean", "direction", "bias", "polarity"],
    "MAGNITUDE": ["intensity", "scale", "weight", "amplitude", "measure"],
    "COST": ["cost", "burden", "investment", "economy", "price"],
    "DIFFERENCE": ["distinction", "contrast", "edge", "separation", "difference"],
}

LEVERAGE_TERMS = {
    "leverage": "supported",
    "neutral": "conditional",
    "overhead": "careful",
}

DEPTH_TERMS = {
    "I-A": "core",
    "I-B": "latent",
    "I-D": "emerging",
    "I-C": "peripheral",
}

COST_TERMS = {
    "low": "light",
    "moderate": "weighted",
    "high": "committed",
    "deep": "consequential",
}

ACCOUNTABILITY_TERMS = {
    "committed": "owned",
    "assertive": "asserted",
    "declarative": "declared",
    "tentative": "tentative",
    "observational": "observed",
    "exploratory": "probing",
}

DOMAIN_SPEAKABLE: Dict[str, List[str]] = {
    "X": ["signal", "evidence", "trace", "presence", "record"],
    "T": ["belief", "continuity", "expectation", "memory", "stance", "revision"],
    "N": ["purpose", "effort", "value", "burden", "yield", "sustainability"],
    "B": ["meaning", "boundary", "distinction", "context", "clarity", "limit"],
    "A": ["understanding", "agency", "ownership", "accountability", "claim", "responsibility"],
}

SPEAKABILITY_BANNED_TOKENS = {
    "cluster_pair",
    "nc_manifold",
    "sub",
    "law",
    "xlaw",
    "slot",
    "coordinate",
    "constraint",
    "operator",
    "polarity",
    "magnitude",
    "cross_rule",
    "cross-rule",
    "leverage",
    "overhead",
    "neutral",
    "supported",
    "asserted",
    "declared",
}

LABELISH_PATTERN = re.compile(r"[A-Z]:[A-Z]|[A-Z]{2,}|[_{}\\[\\]]|\\w+-\\w+-\\w+")

LEXICON_STOPWORDS = {
    "the",
    "and",
    "but",
    "because",
    "though",
    "with",
    "about",
    "from",
    "between",
    "within",
    "through",
    "toward",
    "this",
    "that",
    "there",
    "what",
    "when",
    "where",
    "would",
    "could",
    "should",
    "just",
    "really",
}

ROLE_WEIGHT = {
    "noun": 5,
    "verb": 4,
    "adjective": 3,
    "adverb": 2,
}

GRAMMAR_AFFORDANCE_BY_DIM: Dict[str, Dict[str, str]] = {
    "OPERATOR": {
        "grammar_axis": "operator",
        "surface_affordance": "action-or-verb-use",
        "runtime_question": "what can this word do in the utterance",
    },
    "POLARITY": {
        "grammar_axis": "polarity",
        "surface_affordance": "stance-or-modal-use",
        "runtime_question": "which way does this word lean in the utterance",
    },
    "MAGNITUDE": {
        "grammar_axis": "magnitude",
        "surface_affordance": "degree-or-modifier-use",
        "runtime_question": "how strongly does this word qualify the utterance",
    },
    "COST": {
        "grammar_axis": "cost",
        "surface_affordance": "commitment-or-weight-use",
        "runtime_question": "what does this word cost Aurora to say",
    },
    "DIFFERENCE": {
        "grammar_axis": "difference",
        "surface_affordance": "boundary-or-contrast-use",
        "runtime_question": "what distinction does this word mark in the utterance",
    },
}

SELF_FAMILY_ANCHORS = {
    "X": "Existential_Operator_of_Existence",
    "T": "Temporal_Operator_of_Temporal",
    "N": "Energetic_Operator_of_Energetic",
    "B": "Boundary_Operator_of_Boundary",
    "A": "Agentive_Operator_of_Agency",
}

SELF_FAMILY_NONCOMP_BY_TARGET_DIM = {
    ("X", "POLARITY"): "Existential_Polarity_of_Existence",
    ("X", "MAGNITUDE"): "Existential_Magnitude_of_Existence",
    ("X", "COST"): "Existential_Cost_of_Existence",
    ("X", "DIFFERENCE"): "Existential_Difference_of_Existence",
    ("T", "POLARITY"): "Temporal_Polarity_of_Temporal",
    ("T", "MAGNITUDE"): "Temporal_Magnitude_of_Temporal",
    ("T", "COST"): "Temporal_Cost_of_Temporal",
    ("T", "DIFFERENCE"): "Temporal_Difference_of_Temporal",
    ("N", "POLARITY"): "Energetic_Polarity_of_Energetic",
    ("N", "MAGNITUDE"): "Energetic_Magnitude_of_Energetic",
    ("N", "COST"): "Energetic_Cost_of_Energetic",
    ("N", "DIFFERENCE"): "Energetic_Difference_of_Energetic",
    ("B", "POLARITY"): "Boundary_Polarity_of_Boundary",
    ("B", "MAGNITUDE"): "Boundary_Magnitude_of_Boundary",
    ("B", "COST"): "Boundary_Cost_of_Boundary",
    ("B", "DIFFERENCE"): "Boundary_Difference_of_Boundary",
    ("A", "POLARITY"): "Agentive_Polarity_of_Agency",
    ("A", "MAGNITUDE"): "Agentive_Magnitude_of_Agency",
    ("A", "COST"): "Agentive_Cost_of_Agency",
    ("A", "DIFFERENCE"): "Agentive_Difference_of_Agency",
}


class FGAEError(RuntimeError):
    """Raised when the FGAE population or validation contract is violated."""


def stable_index(seed: str, modulo: int) -> int:
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate(seed)) % modulo


def pick(values: List[str], seed: str) -> str:
    return values[stable_index(seed, len(values))]


def clause_i(depth_score: float) -> str:
    if depth_score >= 0.8:
        return "I-A"
    if depth_score >= 0.4:
        return "I-B"
    if depth_score >= 0.1:
        return "I-D"
    return "I-C"


def clause_ii(leverage_class: str) -> str:
    mapping = {"leverage": "II-A", "neutral": "II-B", "overhead": "II-C"}
    try:
        return mapping[leverage_class]
    except KeyError as exc:
        raise FGAEError(f"unknown leverage_class {leverage_class!r}") from exc


def clause_iii(slot: MutableMapping[str, Any]) -> str:
    return "III-A" if slot["is_resonant"] or float(slot["depth_score"]) >= 0.4 else "III-B"


def accountability_class(weight: float, seed: str) -> str:
    if weight >= 0.7:
        return pick(["declarative", "assertive", "committed"], seed)
    if weight >= 0.4:
        return pick(["tentative", "observational"], seed)
    return "exploratory"


def cost_class(combined_cost: float) -> str:
    if combined_cost <= 90:
        return "low"
    if combined_cost <= 150:
        return "moderate"
    if combined_cost <= 200:
        return "high"
    return "deep"


def density_count(evolution_grade: float) -> int:
    """Return the minimum valid FGAE density for disk-aware population."""
    if evolution_grade >= 0.7:
        return 8
    if evolution_grade >= 0.5:
        return 5
    if evolution_grade >= 0.3:
        return 3
    return 1


def density_range(evolution_grade: float) -> Tuple[int, int]:
    if evolution_grade >= 0.7:
        return 8, 12
    if evolution_grade >= 0.5:
        return 5, 7
    if evolution_grade >= 0.3:
        return 3, 4
    return 1, 2


def register_for(slot: MutableMapping[str, Any]) -> str:
    depth = float(slot["depth_score"])
    acct = float(slot["accountability_weight"])
    cost = float(slot["combined_cost"])
    if slot["is_resonant"] and depth >= 0.8 and acct >= 0.7:
        return "intimate"
    if cost > 200:
        return "formal"
    if not slot["is_resonant"] or slot["sub_law_c"] != slot["col_law_c"]:
        return "technical"
    if cost <= 90 and acct < 0.4:
        return "colloquial"
    return "neutral"


def clean_summary(summary: str) -> str:
    return " ".join(summary.replace(".", "").split())


def grammar_affordance_for_slot(data: MutableMapping[str, Any], slot: MutableMapping[str, Any]) -> Dict[str, Any]:
    target = data["nc_target"]
    col_dim = slot["col_law_d"]
    sub_dim = slot["sub_law_d"]
    noncomp_dim = data["nc_dim"]
    primary_ref = (
        SELF_FAMILY_ANCHORS[target]
        if col_dim == "OPERATOR"
        else SELF_FAMILY_NONCOMP_BY_TARGET_DIM.get((target, col_dim))
    )
    noncomp_ref = (
        SELF_FAMILY_ANCHORS[target]
        if noncomp_dim == "OPERATOR"
        else SELF_FAMILY_NONCOMP_BY_TARGET_DIM.get((target, noncomp_dim))
    )
    return {
        "layer_model": "5-diagonal-anchor-plus-20-self-family-grammar",
        "diagonal_anchor_reference": SELF_FAMILY_ANCHORS[target],
        "primary_grammar_reference": primary_ref,
        "noncomp_dimension_reference": noncomp_ref,
        "primary_dimension": col_dim,
        "secondary_dimension": sub_dim,
        "noncomp_dimension": noncomp_dim,
        "primary_affordance": GRAMMAR_AFFORDANCE_BY_DIM[col_dim],
        "secondary_affordance": GRAMMAR_AFFORDANCE_BY_DIM[sub_dim],
        "noncomp_affordance": GRAMMAR_AFFORDANCE_BY_DIM[noncomp_dim],
        "slot_role": (
            "diagonal_anchor"
            if data.get("nc_is_diagonal") and slot.get("is_anchor")
            else "self_family_grammar"
            if data["nc_law_c"] == data["nc_target"]
            else "cross_family_intersection"
        ),
    }


def _clean_lexicon_word(word: str) -> str | None:
    cleaned = " ".join(word.strip().split())
    if not cleaned or cleaned.lower() in LEXICON_STOPWORDS:
        return None
    if " " in cleaned:
        return None
    if len(cleaned) > 40 or len(cleaned) < 3:
        return None
    if "-" in cleaned or "_" in cleaned or "/" in cleaned:
        return None
    if not re.fullmatch(r"[A-Za-z][A-Za-z']{1,39}", cleaned):
        return None
    if not is_speakable(cleaned):
        return None
    return cleaned


def load_aurora_lexicon(manifold_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Merge Aurora's lexicon and OETS words into one candidate pool."""
    base_dir = manifold_dir.parent
    merged: Dict[str, Dict[str, Any]] = {}
    lexicon_path = base_dir / "aurora_state" / "lexicon.json"
    if lexicon_path.exists():
        data = json.loads(lexicon_path.read_text())
        for raw_word, entry in data.get("entries", {}).items():
            word = _clean_lexicon_word(str(raw_word))
            if not word:
                continue
            merged[word.lower()] = {
                "word": word,
                "role": entry.get("role", ""),
                "meaning": str(entry.get("meaning", "")),
                "usage_count": int(entry.get("usage_count") or 0),
                "source": "lexicon",
            }
    for oets_path in [base_dir / "aurora_state" / "aurora_oets_web.json", base_dir / "aurora_oets_web.json"]:
        if not oets_path.exists():
            continue
        data = json.loads(oets_path.read_text())
        for raw_word, node in data.get("nodes", {}).items():
            word = _clean_lexicon_word(str(node.get("word") or raw_word))
            if not word:
                continue
            definitions = node.get("definitions") or []
            definition_text = " ".join(str(item.get("text", "")) for item in definitions if isinstance(item, dict))
            key = word.lower()
            current = merged.get(key, {})
            merged[key] = {
                "word": word,
                "role": current.get("role") or node.get("role", ""),
                "meaning": (current.get("meaning", "") + " " + definition_text).strip(),
                "usage_count": max(int(current.get("usage_count") or 0), int(node.get("times_used_in_expression") or 0), int(node.get("times_encountered") or 0)),
                "source": "lexicon+oets" if current else "oets",
            }
    return merged


def lexicon_keywords(data: MutableMapping[str, Any], slot: MutableMapping[str, Any]) -> List[str]:
    keys: List[str] = []
    for family in [data["nc_target"], data["nc_law_c"], slot["sub_law_c"], slot["col_law_c"]]:
        field = DOMAIN_FIELDS[family]
        keys.extend([field["domain"], field["anchor"], *field["terms"]])
    keys.extend(CLUSTER_TERMS.get(slot["sub_cluster"], []))
    keys.extend(DIMENSION_TERMS.get(slot["sub_law_d"], []))
    keys.extend(DIMENSION_TERMS.get(slot["col_law_d"], []))
    keys.extend(str(data.get("nc_semantic_summary", "")).replace(".", " ").split())
    return [key.lower() for key in keys if len(key) > 3]


def lexicon_candidates(
    data: MutableMapping[str, Any],
    slot: MutableMapping[str, Any],
    aurora_lexicon: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    cache_key = (
        data["nc_target"],
        data["nc_law_c"],
        slot["sub_law_c"],
        slot["sub_law_d"],
        slot["sub_cluster"],
        slot["col_law_c"],
        slot["col_law_d"],
        slot["cluster_pair"],
        str(slot["leverage_class"]),
        clause_i(float(slot["depth_score"])),
        cost_class(float(slot["combined_cost"])),
    )
    cache = aurora_lexicon.setdefault("__candidate_cache__", {})
    if cache_key in cache:
        return cache[cache_key]
    keys = lexicon_keywords(data, slot)
    candidates: List[Tuple[float, Dict[str, Any]]] = []
    seen_words = set()
    for key in keys:
        for probe in [key, key.rstrip("s")]:
            if not probe or probe in seen_words:
                continue
            entry = aurora_lexicon.get(probe)
            if not entry:
                continue
            seen_words.add(probe)
            word = str(entry["word"])
            lower_word = word.lower()
            meaning = str(entry.get("meaning", "")).lower()
            score = 0.0
            if key == lower_word:
                score += 30
            elif key in lower_word or lower_word in key:
                score += 12
            elif key in meaning:
                score += 5
            score += min(float(entry.get("usage_count") or 0), 50.0) / 10.0
            score += ROLE_WEIGHT.get(str(entry.get("role", "")).lower(), 0)
            if slot["is_resonant"]:
                score += 2
            candidates.append((score, entry))
    if not candidates:
        for family in [data["nc_target"], slot["sub_law_c"], slot["col_law_c"]]:
            for probe in DOMAIN_SPEAKABLE[family]:
                if probe in seen_words:
                    continue
                entry = aurora_lexicon.get(probe.lower())
                if not entry:
                    continue
                seen_words.add(probe)
                score = 10 + min(float(entry.get("usage_count") or 0), 50.0) / 10.0
                candidates.append((score, entry))
    if not candidates:
        for dict_key, entry in aurora_lexicon.items():
            if str(dict_key).startswith("__"):
                continue
            word = str(entry["word"]).lower()
            if word in DOMAIN_FIELDS[data["nc_target"]]["terms"] or word in DOMAIN_FIELDS[slot["sub_law_c"]]["terms"]:
                candidates.append((5.0, entry))
    if not candidates:
        cache[cache_key] = []
        return cache[cache_key]
    candidates.sort(key=lambda item: (-item[0], item[1]["word"].lower()))
    cache[cache_key] = [entry for _, entry in candidates[:40]]
    return cache[cache_key]


def is_speakable(phrase: str) -> bool:
    text = " ".join(str(phrase).strip().split())
    if not text:
        return False
    lowered = text.lower()
    if LABELISH_PATTERN.search(text):
        return False
    if any(token in lowered for token in SPEAKABILITY_BANNED_TOKENS):
        return False
    if ":" in text or "[" in text or "]" in text or "{" in text or "}" in text:
        return False
    if lowered.count("-") > 0:
        return False
    return bool(re.search(r"[a-zA-Z]", text))


def _candidate_word(
    data: MutableMapping[str, Any],
    slot: MutableMapping[str, Any],
    entry_index: int,
    aurora_lexicon: Dict[str, Dict[str, Any]],
) -> Tuple[str, str]:
    candidates = lexicon_candidates(data, slot, aurora_lexicon)
    if candidates:
        candidate = candidates[entry_index % len(candidates)]
        return str(candidate["word"]).lower(), str(candidate.get("source") or "lexicon")
    target_pool = DOMAIN_SPEAKABLE[data["nc_target"]]
    sub_pool = DOMAIN_SPEAKABLE[slot["sub_law_c"]]
    pool = [word for word in target_pool + sub_pool if " " not in word]
    return pick(pool, f"{slot['slot_id']}:{entry_index}:fallback").lower(), "fallback-domain-bank"


def derivation_note(
    data: MutableMapping[str, Any],
    slot: MutableMapping[str, Any],
    word_or_phrase: str,
    lexicon_word: str,
    lexicon_source: str,
) -> str:
    sub_cluster, col_cluster = slot["cluster_pair"].split(":", 1)
    summary = clean_summary(str(data["nc_semantic_summary"]))
    target_domain = DOMAIN_FIELDS[data["nc_target"]]["domain"]
    sub_domain = DOMAIN_FIELDS[slot["sub_law_c"]]["domain"]
    acct = accountability_class(float(slot["accountability_weight"]), slot["slot_id"])
    cost = cost_class(float(slot["combined_cost"]))
    grammar = grammar_affordance_for_slot(data, slot)
    affordance = grammar["primary_affordance"]["surface_affordance"]
    templates = [
        (
            f"{word_or_phrase} fits cluster_pair {slot['cluster_pair']} because Aurora's {lexicon_source} word "
            f"{lexicon_word!r} can speak the {target_domain} field through a {sub_domain} lens; "
            f"the {CLUSTER_CHARACTER.get(sub_cluster, sub_cluster.lower())} to "
            f"{CLUSTER_CHARACTER.get(col_cluster, col_cluster.lower())} geometry makes it a {cost} "
            f"{acct} expression, while {grammar['primary_grammar_reference']} supplies the {affordance} grammar affordance for this summary: {summary}"
        ),
        (
            f"At cluster_pair {slot['cluster_pair']}, {word_or_phrase} is justified by the {lexicon_source} "
            f"lexical seed {lexicon_word!r}: it stays word-only while joining "
            f"{target_domain} with {sub_domain}, and its {cost} cost class plus {acct} accountability "
            f"matches the slot grammar affordance from {grammar['primary_grammar_reference']}: {summary}"
        ),
        (
            f"{word_or_phrase} belongs to cluster_pair {slot['cluster_pair']} because the slot asks for "
            f"{CLUSTER_CHARACTER.get(sub_cluster, sub_cluster.lower())} expressed through "
            f"{CLUSTER_CHARACTER.get(col_cluster, col_cluster.lower())}; Aurora's {lexicon_source} seed "
            f"{lexicon_word!r} grounds that word in the 5-anchor/20-grammar layer via "
            f"{grammar['primary_grammar_reference']} for the summary: {summary}"
        ),
    ]
    return templates[stable_index(slot["slot_id"] + word_or_phrase, len(templates))]


def build_entry(
    data: MutableMapping[str, Any],
    slot: MutableMapping[str, Any],
    entry_index: int,
    anchor_word: str | None,
    aurora_lexicon: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    seed = f"{slot['slot_id']}:{entry_index}"
    lexicon_word, lexicon_source = _candidate_word(data, slot, entry_index, aurora_lexicon)
    entry = {
        "entry_id": f"{slot['slot_id']}:ENTRY:{entry_index:02d}",
        "word_or_phrase": "",
        "entry_type": "phrase",
        "register": register_for(slot),
        "clause_i_level": clause_i(float(slot["depth_score"])),
        "clause_ii_level": clause_ii(str(slot["leverage_class"])),
        "clause_iii_influence": clause_iii(slot),
        "accountability_class": accountability_class(float(slot["accountability_weight"]), seed),
        "cost_class": cost_class(float(slot["combined_cost"])),
        "lexicon_source": lexicon_source,
        "grammar_affordance": grammar_affordance_for_slot(data, slot),
        "derivation_note": "",
    }
    if entry_index == 0 and anchor_word:
        entry["word_or_phrase"] = anchor_word
        entry["entry_type"] = "word"
        lexicon_word = anchor_word
        lexicon_source = "representational-anchor"
        entry["lexicon_source"] = lexicon_source
    else:
        entry["word_or_phrase"] = lexicon_word
        entry["entry_type"] = "word"
    entry["derivation_note"] = derivation_note(data, slot, entry["word_or_phrase"], lexicon_word, lexicon_source)
    return entry


def populate_slot(
    data: MutableMapping[str, Any],
    slot: MutableMapping[str, Any],
    aurora_lexicon: Dict[str, Dict[str, Any]],
) -> int:
    count = density_count(float(slot["evolution_grade"]))
    anchor_word = None
    if data.get("nc_is_diagonal") and slot.get("is_anchor"):
        anchor_word = data.get("representational_anchor")
        count = max(count, 2)
    entries = [build_entry(data, slot, idx, anchor_word if idx == 0 else None, aurora_lexicon) for idx in range(count)]
    slot["with_semantics"] = True
    slot["semantic_entries"] = entries
    return len(entries)


def validate_slot(data: MutableMapping[str, Any], slot: MutableMapping[str, Any]) -> List[str]:
    errors: List[str] = []
    entries = slot.get("semantic_entries") or []
    min_count, max_count = density_range(float(slot["evolution_grade"]))
    if data.get("nc_is_diagonal") and slot.get("is_anchor"):
        min_count = max(min_count, 2)
    if not slot.get("with_semantics") or not entries:
        errors.append(f"FGAE-V01 {slot['slot_id']}")
    if not (min_count <= len(entries) <= max_count):
        errors.append(f"FGAE-V09 {slot['slot_id']} expected {min_count}-{max_count} got {len(entries)}")
    if data.get("nc_is_diagonal") and slot.get("is_anchor"):
        anchor = data.get("representational_anchor")
        if not entries or entries[0].get("word_or_phrase") != anchor:
            errors.append(f"FGAE-V08 {slot['slot_id']}")
    expected_i = clause_i(float(slot["depth_score"]))
    expected_ii = clause_ii(str(slot["leverage_class"]))
    expected_iii = clause_iii(slot)
    expected_cost = cost_class(float(slot["combined_cost"]))
    acct_weight = float(slot["accountability_weight"])
    for entry in entries:
        if entry.get("clause_i_level") != expected_i:
            errors.append(f"FGAE-V02 {entry.get('entry_id')}")
        if entry.get("clause_ii_level") != expected_ii:
            errors.append(f"FGAE-V03 {entry.get('entry_id')}")
        if entry.get("clause_iii_influence") != expected_iii:
            errors.append(f"FGAE-V04 {entry.get('entry_id')}")
        acct = entry.get("accountability_class")
        if acct_weight >= 0.7 and acct not in {"declarative", "assertive", "committed"}:
            errors.append(f"FGAE-V05 {entry.get('entry_id')}")
        if 0.4 <= acct_weight < 0.7 and acct not in {"tentative", "observational"}:
            errors.append(f"FGAE-V05 {entry.get('entry_id')}")
        if acct_weight < 0.4 and acct != "exploratory":
            errors.append(f"FGAE-V05 {entry.get('entry_id')}")
        if entry.get("cost_class") != expected_cost:
            errors.append(f"FGAE-V06 {entry.get('entry_id')}")
        note = entry.get("derivation_note")
        if not isinstance(note, str) or "cluster_pair" not in note:
            errors.append(f"FGAE-V07 {entry.get('entry_id')}")
        if entry.get("entry_type") == "construction":
            errors.append(f"FGAE-V10 {entry.get('entry_id')} construction entry not emitted by this pass")
        word_or_phrase = str(entry.get("word_or_phrase", ""))
        if entry.get("entry_type") != "word" or " " in word_or_phrase.strip() or not is_speakable(word_or_phrase):
            errors.append(f"FGAE-V13 {entry.get('entry_id')} {entry.get('word_or_phrase')!r}")
        grammar = entry.get("grammar_affordance")
        if not isinstance(grammar, dict) or grammar.get("layer_model") != "5-diagonal-anchor-plus-20-self-family-grammar":
            errors.append(f"FGAE-V14 {entry.get('entry_id')} missing grammar affordance layer")
        elif not grammar.get("diagonal_anchor_reference") or not grammar.get("primary_grammar_reference"):
            errors.append(f"FGAE-V14 {entry.get('entry_id')} incomplete grammar affordance reference")
    return errors


def validate_noncomp(data: MutableMapping[str, Any]) -> List[str]:
    errors: List[str] = []
    for slot in data["slots"]:
        errors.extend(validate_slot(data, slot))
    return errors


def ordered_entries(index: MutableMapping[str, Any]) -> Iterable[MutableMapping[str, Any]]:
    entries = list(index["entries"])
    diagonal_order = {
        "Existential_Operator_of_Existence": 0,
        "Temporal_Polarity_of_Belief": 1,
        "Energetic_Cost_of_Purpose": 2,
        "Boundary_Difference_of_Meaning": 3,
        "Agentive_Operator_of_Agency": 4,
    }

    def order(entry: MutableMapping[str, Any]) -> Tuple[int, str, str]:
        if entry["nc_name"] in diagonal_order:
            return (0, f"{diagonal_order[entry['nc_name']]:03d}", entry["nc_name"])
        if entry["nc_law_c"] == entry["nc_target"]:
            return (1, entry["nc_law_c"], entry["nc_name"])
        return (2, entry["nc_law_c"] + entry["nc_target"], entry["nc_name"])

    return sorted(entries, key=order)


def populate(manifold_dir: Path, force: bool) -> Dict[str, int]:
    index_path = manifold_dir / "_index.json"
    index = json.loads(index_path.read_text())
    aurora_lexicon = load_aurora_lexicon(manifold_dir)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    processed = 0
    skipped = 0
    total_entries = 0
    index_by_name = {entry["nc_name"]: entry for entry in index["entries"]}
    for index_entry in ordered_entries(index):
        path = manifold_dir / index_entry["file"]
        data = json.loads(path.read_text())
        if data.get("with_semantics") is True and not force:
            errors = validate_noncomp(data)
            if errors:
                raise FGAEError("\n".join(errors[:40]))
            skipped += 1
            total_entries += int(data.get("semantic_entry_count", 0))
            continue
        semantic_entry_count = 0
        for slot in data["slots"]:
            semantic_entry_count += populate_slot(data, slot, aurora_lexicon)
        data["with_semantics"] = True
        data["semantic_population_date"] = now
        data["semantic_entry_count"] = semantic_entry_count
        errors = validate_noncomp(data)
        if errors:
            raise FGAEError("\n".join(errors[:40]))
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
        idx = index_by_name[data["nc_name"]]
        idx["with_semantics"] = True
        idx["semantic_population_date"] = now
        idx["semantic_entry_count"] = semantic_entry_count
        total_entries += semantic_entry_count
        processed += 1
    index["with_semantics"] = all(entry.get("with_semantics") is True for entry in index["entries"])
    index["semantic_population_date"] = now
    index["semantic_entry_count"] = sum(int(entry.get("semantic_entry_count", 0)) for entry in index["entries"])
    if index["with_semantics"] is not True:
        raise FGAEError("index root with_semantics did not resolve true after population")
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {"processed": processed, "skipped": skipped, "entries": total_entries}


def validate_all(manifold_dir: Path) -> Dict[str, int]:
    index = json.loads((manifold_dir / "_index.json").read_text())
    errors: List[str] = []
    file_count = 0
    slot_count = 0
    entry_count = 0
    for index_entry in index["entries"]:
        data = json.loads((manifold_dir / index_entry["file"]).read_text())
        file_count += 1
        slot_count += len(data["slots"])
        entry_count += sum(len(slot.get("semantic_entries") or []) for slot in data["slots"])
        if data.get("with_semantics") is not True:
            errors.append(f"FGAE-V01 {data['nc_name']} file with_semantics false")
        errors.extend(validate_noncomp(data))
        idx_entry = next(entry for entry in index["entries"] if entry["nc_name"] == data["nc_name"])
        if idx_entry.get("with_semantics") is not True:
            errors.append(f"FGAE-V01 index {data['nc_name']} with_semantics false")
        if idx_entry.get("semantic_entry_count") != data.get("semantic_entry_count"):
            errors.append(f"index entry count mismatch {data['nc_name']}")
    if index.get("with_semantics") is not True:
        errors.append("FGAE-V01 index root with_semantics false")
    if file_count != 125:
        errors.append(f"expected 125 NonComps got {file_count}")
    if slot_count != 78125:
        errors.append(f"expected 78125 slots got {slot_count}")
    if errors:
        raise FGAEError("\n".join(errors[:80]))
    return {"files": file_count, "slots": slot_count, "entries": entry_count}


def export_semantic_directory(manifold_dir: Path, output_path: Path) -> Dict[str, int]:
    """Write a compact directory containing only the FGAE-added semantic layer."""
    index = json.loads((manifold_dir / "_index.json").read_text())
    directory: Dict[str, Any] = {
        "generated_from": "FGAE_SPECIFICATION.md",
        "source_index": str(manifold_dir / "_index.json"),
        "with_semantics": index.get("with_semantics"),
        "semantic_population_date": index.get("semantic_population_date"),
        "semantic_entry_count": index.get("semantic_entry_count"),
        "noncomp_count": len(index.get("entries", [])),
        "slot_count": 0,
        "axes": {},
    }
    for index_entry in index["entries"]:
        axis = index_entry["file"].split("/", 1)[0]
        data = json.loads((manifold_dir / index_entry["file"]).read_text())
        nc_directory = {
            "file": index_entry["file"],
            "nc_name": data["nc_name"],
            "nc_law_c": data["nc_law_c"],
            "nc_dim": data["nc_dim"],
            "nc_target": data["nc_target"],
            "nc_domain": data["nc_domain"],
            "nc_cluster": data["nc_cluster"],
            "nc_is_diagonal": data["nc_is_diagonal"],
            "representational_anchor": data.get("representational_anchor"),
            "nc_semantic_summary": data["nc_semantic_summary"],
            "with_semantics": data.get("with_semantics"),
            "semantic_population_date": data.get("semantic_population_date"),
            "semantic_entry_count": data.get("semantic_entry_count"),
            "slots": [
                {
                    "slot_id": slot["slot_id"],
                    "with_semantics": slot.get("with_semantics"),
                    "semantic_entries": slot.get("semantic_entries", []),
                }
                for slot in data["slots"]
            ],
        }
        directory["slot_count"] += len(nc_directory["slots"])
        directory["axes"].setdefault(axis, {})[data["nc_name"]] = nc_directory
    output_path.write_text(json.dumps(directory, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {
        "files": directory["noncomp_count"],
        "slots": directory["slot_count"],
        "entries": int(directory.get("semantic_entry_count") or 0),
        "bytes": output_path.stat().st_size,
    }


def _semantic_directory_header(manifold_dir: Path, index: MutableMapping[str, Any]) -> Dict[str, Any]:
    return {
        "generated_from": "FGAE_SPECIFICATION.md",
        "source_index": str(manifold_dir / "_index.json"),
        "with_semantics": index.get("with_semantics"),
        "semantic_population_date": index.get("semantic_population_date"),
        "semantic_entry_count": index.get("semantic_entry_count"),
        "noncomp_count": len(index.get("entries", [])),
    }


def _semantic_noncomp_directory(
    manifold_dir: Path,
    index_entry: MutableMapping[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    axis = index_entry["file"].split("/", 1)[0]
    data = json.loads((manifold_dir / index_entry["file"]).read_text())
    return axis, {
        "file": index_entry["file"],
        "nc_name": data["nc_name"],
        "nc_law_c": data["nc_law_c"],
        "nc_dim": data["nc_dim"],
        "nc_target": data["nc_target"],
        "nc_domain": data["nc_domain"],
        "nc_cluster": data["nc_cluster"],
        "nc_is_diagonal": data["nc_is_diagonal"],
        "representational_anchor": data.get("representational_anchor"),
        "nc_semantic_summary": data["nc_semantic_summary"],
        "with_semantics": data.get("with_semantics"),
        "semantic_population_date": data.get("semantic_population_date"),
        "semantic_entry_count": data.get("semantic_entry_count"),
        "slots": [
            {
                "slot_id": slot["slot_id"],
                "with_semantics": slot.get("with_semantics"),
                "semantic_entries": slot.get("semantic_entries", []),
            }
            for slot in data["slots"]
        ],
    }


def export_semantic_shards(manifold_dir: Path, output_dir: Path, max_bytes: int) -> Dict[str, int]:
    """Write parseable JSON shard files no larger than max_bytes."""
    index = json.loads((manifold_dir / "_index.json").read_text())
    if max_bytes < 1_000_000:
        raise FGAEError("max shard bytes is too small to be useful")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FGAEError(f"{output_dir} already exists and is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    header = _semantic_directory_header(manifold_dir, index)
    part_prefix = "FGAE_SEMANTIC_DIRECTORY"
    manifest: Dict[str, Any] = {
        **header,
        "max_shard_bytes": max_bytes,
        "parts": [],
    }
    part_count = 0
    total_slots = 0
    total_entries = 0
    current_axes: Dict[str, Dict[str, Any]] = {}
    current_files = 0
    current_slots = 0
    current_entries = 0

    def make_payload(axes: Dict[str, Dict[str, Any]], part_number: int) -> Dict[str, Any]:
        return {
            **header,
            "shard": {
                "part": part_number,
                "max_bytes": max_bytes,
                "noncomp_count": current_files,
                "slot_count": current_slots,
                "semantic_entry_count": current_entries,
            },
            "axes": axes,
        }

    def serialized_size(axes: Dict[str, Dict[str, Any]], part_number: int) -> int:
        return len(json.dumps(make_payload(axes, part_number), ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 1

    def flush() -> None:
        nonlocal part_count, current_axes, current_files, current_slots, current_entries
        if not current_axes:
            return
        part_count += 1
        payload = make_payload(current_axes, part_count)
        part_name = f"{part_prefix}.part_{part_count:03d}.json"
        part_path = output_dir / part_name
        part_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        part_size = part_path.stat().st_size
        if part_size > max_bytes:
            raise FGAEError(f"{part_name} exceeded shard limit: {part_size} > {max_bytes}")
        manifest["parts"].append(
            {
                "file": part_name,
                "bytes": part_size,
                "noncomp_count": current_files,
                "slot_count": current_slots,
                "semantic_entry_count": current_entries,
            }
        )
        current_axes = {}
        current_files = 0
        current_slots = 0
        current_entries = 0

    for index_entry in index["entries"]:
        axis, nc_directory = _semantic_noncomp_directory(manifold_dir, index_entry)
        nc_name = nc_directory["nc_name"]
        nc_slots = len(nc_directory["slots"])
        nc_entries = int(nc_directory.get("semantic_entry_count") or 0)
        trial_axes = json.loads(json.dumps(current_axes, ensure_ascii=False))
        trial_axes.setdefault(axis, {})[nc_name] = nc_directory
        if current_axes and serialized_size(trial_axes, part_count + 1) > max_bytes:
            flush()
            trial_axes = {axis: {nc_name: nc_directory}}
        if serialized_size(trial_axes, part_count + 1) > max_bytes:
            raise FGAEError(f"{nc_name} is too large for one {max_bytes}-byte shard")
        current_axes = trial_axes
        current_files += 1
        current_slots += nc_slots
        current_entries += nc_entries
        total_slots += nc_slots
        total_entries += nc_entries
    flush()
    manifest["part_count"] = part_count
    manifest["slot_count"] = total_slots
    manifest["exported_semantic_entry_count"] = total_entries
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {
        "parts": part_count,
        "files": len(index.get("entries", [])),
        "slots": total_slots,
        "entries": total_entries,
        "manifest_bytes": manifest_path.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate and validate FGAE semantics.")
    parser.add_argument("--manifold-dir", default=str(MANIFOLD_DIR))
    parser.add_argument("--force", action="store_true", help="repopulate even when with_semantics is already true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--export-directory", help="write a semantic-layer-only directory JSON to this path")
    parser.add_argument("--export-shards", help="write semantic-layer-only JSON shards into this directory")
    parser.add_argument("--max-shard-bytes", type=int, default=20_000_000)
    args = parser.parse_args()
    manifold_dir = Path(args.manifold_dir)
    if args.export_shards:
        result = export_semantic_shards(manifold_dir, Path(args.export_shards), args.max_shard_bytes)
        print(json.dumps({"exported_shards": result}, sort_keys=True))
        return
    if args.export_directory:
        result = export_semantic_directory(manifold_dir, Path(args.export_directory))
        print(json.dumps({"exported": result}, sort_keys=True))
        return
    if args.validate_only:
        result = validate_all(manifold_dir)
        print(json.dumps({"validated": result}, sort_keys=True))
        return
    result = populate(manifold_dir, force=args.force)
    validation = validate_all(manifold_dir)
    print(json.dumps({"populated": result, "validated": validation}, sort_keys=True))


if __name__ == "__main__":
    main()
