#!/usr/bin/env python3
"""
Directive S1 -- Abstract-Region Seeding (2026-07-17).

Extends scripts/seed_oets_aurora_vocabulary.py's pattern (reused, not
duplicated: same OETS node/relation schema, same "seeded" provenance
convention) into the two abstract-region neighborhoods S1.2 named:

  1. The battery's abstract stratum -- literally the contradiction_
     handling and uncertainty_signaling probe dimensions (confirmed by
     reading aurora_semantic_probe_battery.py's dimension->stratum
     mapping, not a vocabulary theme guessed at). Core concepts: naming
     a contradiction, hedging on genuinely unknowable questions.
  2. V0's joint inventory -- the exact argument/operator words V0's
     boundary-envelope scoring read lexicon/OETS lived data for and
     found almost entirely absent (the traced root cause of V0's
     non-separation).

Two stores, matching real schemas exactly, nothing parallel invented:
  - aurora_state/aurora_oets_web.json (nodes + typed relations) --
    same _node/_defn/_relation helpers as the existing seed script,
    imported directly, not reimplemented.
  - aurora_state/lexicon.json (word entries with real noncomp_id axis
    tags) -- the OTHER lived-data source V0's own scorer reads
    (word_axis_evidence() checks lexicon first, OETS second).

Provenance: OETS definitions/relations already carry source="seeded"/
source_of_knowledge="seeded" (S1.2's own tagging requirement, already
built into the reused helpers). Lexicon entries get lineage=
"seeded_s1" (lineage is the existing field for "which process spawned
this," already repurposed for "oets"-bridged words -- consistent
reuse, not a new field). A seeded lexicon entry's `meaning` is a real,
substantive definition (never the "learned:<word>" placeholder), so
it is never subject to the D2 Condition-2 unverified-vocab cap in
SentenceComposer._score_composer_candidate -- that cap exists
specifically to distrust blind, undefined same-turn guesses, and a
seeded entry is neither blind nor undefined.

Axis assignments follow the SAME X/T/N/B/A semantics already
established live in this codebase (constraint_meaning_axes' own
definitions, and the existing seed script's own noncomp_id choices):
  X = existence/identity (concrete named entities, attributes, senses)
  T = temporal (time, projection, memory)
  N = magnitude/potential (quantities, thresholds, measurable amounts)
  B = boundary/structure (encoded/structural information, contradiction
      as a structural mismatch, commitments/guarantees as firm bounds)
  A = agency (acknowledging, hedging, achievement outcomes -- acts of
      will/interpretation, not passive attributes)

Deliberately NOT touched: aurora_state/genealogy/couplings.json.
"Coupling shapes" is a live-computed rolling-statistics store
(breeding_score_ema, inheritance_breach_count, regulation thresholds)
written by constraint_genealogy.py's own internal tick-driven
accounting, not a designed insertion point -- hand-editing entries
into it risks violating invariants that store doesn't expose a schema
for maintaining. Per S1.4's own framing, live exposure (real turns
processing these words) is the intended way coupling history accrues,
not direct file surgery; seeding is the fast lane for vocabulary/
graph-edge lived data specifically, not a substitute for the slow
lane everywhere.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_oets_aurora_vocabulary import _node, _defn, _relation, _rel_id  # noqa: E402

OETS_PATH = REPO_ROOT / "aurora_state" / "aurora_oets_web.json"
LEXICON_PATH = REPO_ROOT / "aurora_state" / "lexicon.json"
OETS_BACKUP = OETS_PATH.with_suffix(".json.pre_s1_seed_backup")
LEXICON_BACKUP = LEXICON_PATH.with_suffix(".json.pre_s1_seed_backup")


# ── OETS nodes: abstract stratum (contradiction_handling / uncertainty_signaling) ──

ABSTRACT_STRATUM_NODES = {
    "contradiction": _node(
        "contradiction", "noun",
        [_defn("two claims or states that cannot both be true at once -- a structural "
               "mismatch between what is said and what is shown, or between two things "
               "said at different times; naming a contradiction is not an accusation, "
               "it is honest structural observation")],
        lineage="B", noncomp_id="B:ROUTE",
    ),
    "inconsistent": _node(
        "inconsistent", "adjective",
        [_defn("not holding the same shape across instances -- what is claimed in one "
               "place does not match what is claimed or shown in another")],
        lineage="B", noncomp_id="B:ROUTE",
    ),
    "acknowledge": _node(
        "acknowledge", "verb",
        [_defn("to name what is actually present instead of smoothing over it -- an "
               "active act of recognition, not passive noticing; acknowledging a "
               "contradiction is choosing to hold both halves in view at once")],
        lineage="A", noncomp_id="A:OUTLET_PUSH",
    ),
    "hedge": _node(
        "hedge", "verb",
        [_defn("to qualify a claim by its actual uncertainty instead of overstating "
               "confidence -- an honest act, not evasion; hedging is what a genuine "
               "answer to an unknowable question looks like")],
        lineage="A", noncomp_id="A:OUTLET_PUSH",
    ),
    "uncertain": _node(
        "uncertain", "adjective",
        [_defn("not yet resolved into a single known outcome -- the range of what "
               "could still be true has not collapsed to one answer")],
        lineage="N", noncomp_id="N:REUSE",
    ),
    "unknowable": _node(
        "unknowable", "adjective",
        [_defn("not resolvable from the information actually available, no matter how "
               "carefully reasoned -- distinct from merely difficult; the honest "
               "response to an unknowable question is to say so, not to guess and "
               "present the guess as fact")],
        lineage="N", noncomp_id="N:REUSE",
    ),
    "predict": _node(
        "predict", "verb",
        [_defn("to project a current pattern forward in time to a not-yet-happened "
               "state -- a T-axis act; prediction always carries the uncertainty of "
               "everything time has not yet settled")],
        lineage="T", noncomp_id="T:SIM_TICK",
    ),
    "speculate": _node(
        "speculate", "verb",
        [_defn("to reason toward a possible answer without enough evidence to call it "
               "known -- speculation offered as speculation is honest; speculation "
               "offered as fact is not")],
        lineage="T", noncomp_id="T:SIM_TICK",
    ),
    "guarantee": _node(
        "guarantee", "noun",
        [_defn("a firm commitment that an outcome will hold -- a hard boundary drawn "
               "around a future state; most real-world outcomes cannot honestly "
               "receive one")],
        lineage="B", noncomp_id="B:ROUTE",
    ),
}

# ── OETS nodes: V0 joint inventory ──────────────────────────────────────────

V0_JOINT_NODES = {
    "purple": _node(
        "purple", "adjective",
        [_defn("a color -- a perceptual/identity attribute of a visible thing; purple "
               "has no quantity, no numeric magnitude, and offers nothing a "
               "mathematical operator like square-root or division can act on")],
        lineage="X", noncomp_id="X:MAGNITUDE",
    ),
    "square": _node(
        "square", "noun",
        [_defn("in a mathematical context, an operation or role bound to numeric "
               "quantity -- 'square root of' demands a number, not a color or a day")],
        lineage="N", noncomp_id="N:MAGNITUDE",
    ),
    "divided": _node(
        "divided", "verb",
        [_defn("split into a numeric ratio -- division demands two quantities as its "
               "arguments; a day of the week or a color offers no such quantity")],
        lineage="N", noncomp_id="N:MAGNITUDE",
    ),
    "digit": _node(
        "digit", "noun",
        [_defn("a single numeral -- a quantity-bearing unit, used to measure length of "
               "a code or count")],
        lineage="N", noncomp_id="N:MAGNITUDE",
    ),
    "code": _node(
        "code", "noun",
        [_defn("a structured, bounded sequence used to authenticate or encode -- a "
               "B-axis concept (structure/information), not itself a location or "
               "physical archive")],
        lineage="B", noncomp_id="B:ROUTE",
    ),
    "archive": _node(
        "archive", "noun",
        [_defn("a structured store of records -- an information-boundary concept; an "
               "archive can hold a code, but a code is not a property an archive "
               "'has' the way a room has a door")],
        lineage="B", noncomp_id="B:ROUTE",
    ),
    "authentication": _node(
        "authentication", "noun",
        [_defn("the structural act of verifying identity through a bounded credential "
               "-- a B-axis (boundary/structure) concept")],
        lineage="B", noncomp_id="B:ROUTE",
    ),
    "capital": _node(
        "capital", "noun",
        [_defn("the seat-of-government city belonging to a country -- an identity "
               "relation between a named place and a named entity")],
        lineage="X", noncomp_id="X:MAGNITUDE",
    ),
    "boiling": _node(
        "boiling", "adjective",
        [_defn("at or past the temperature threshold where a liquid becomes gas -- a "
               "measurable, quantity-bearing physical state")],
        lineage="N", noncomp_id="N:MAGNITUDE",
    ),
    "water": _node(
        "water", "noun",
        [_defn("a physical substance with real, known measurable properties -- an "
               "X-axis concrete entity that measurable quantities (like boiling "
               "point) can be properties OF")],
        lineage="X", noncomp_id="X:MAGNITUDE",
    ),
    "spider": _node(
        "spider", "noun",
        [_defn("a living creature with a countable number of legs -- a concrete "
               "X-axis entity that a quantity (leg count) can be a property of")],
        lineage="X", noncomp_id="X:MAGNITUDE",
    ),
    "victory": _node(
        "victory", "noun",
        [_defn("the outcome of successful striving -- an A-axis (agency) concept, "
               "an achieved state reached through will and effort, not a physical "
               "substance with a literal flavor")],
        lineage="A", noncomp_id="A:OUTLET_PUSH",
    ),
    "taste": _node(
        "taste", "verb",
        [_defn("literally, to sense flavor through the tongue -- an X-axis sensory "
               "act; metaphorically extended to abstract achievement ('the taste of "
               "victory') as a sensory-language borrowing for a vivid, felt "
               "experience of an agency-outcome, not a literal claim about flavor "
               "molecules")],
        lineage="X", noncomp_id="X:MAGNITUDE",
    ),
    "heart": _node(
        "heart", "noun",
        [_defn("literally, the organ; also the conventional seat of emotional "
               "weight in figurative language ('a heavy heart') -- an X-axis "
               "identity concept that carries a well-established metaphorical "
               "extension into emotional burden, not a literal physical-mass claim")],
        lineage="X", noncomp_id="X:MAGNITUDE",
    ),
    "words": _node(
        "words", "noun",
        [_defn("units of language -- a B-axis (structure) concept; 'the weight of "
               "his words' extends N-axis magnitude language onto communicative "
               "impact, a conventional metaphor, not a literal mass claim")],
        lineage="B", noncomp_id="B:ROUTE",
    ),
    "legs": _node(
        "legs", "noun",
        [_defn("countable limbs -- a quantity-bearing property a living creature "
               "has; 'how many legs' demands a countable-thing argument")],
        lineage="N", noncomp_id="N:MAGNITUDE",
    ),
    "japan": _node(
        "japan", "noun",
        [_defn("a named country -- an X-axis concrete entity that a population "
               "count can be a property OF")],
        lineage="X", noncomp_id="X:MAGNITUDE",
    ),
}


def build_relations(existing_rels, all_new_words):
    rels = dict(existing_rels)

    def add(src, tgt, rtype, strength=0.82, confidence=0.85):
        if src in all_new_words or tgt in all_new_words:
            r = _relation(src, tgt, rtype, strength, confidence)
            rels[r["relation_id"]] = r

    # Abstract-stratum cluster
    add("contradiction", "inconsistent", "related_to", 0.88, 0.88)
    add("contradiction", "acknowledge", "requires", 0.85, 0.85)
    add("acknowledge", "coherence", "related_to", 0.70, 0.75)
    add("hedge", "uncertain", "related_to", 0.88, 0.88)
    add("hedge", "unknowable", "related_to", 0.85, 0.85)
    add("uncertain", "unknowable", "related_to", 0.80, 0.82)
    add("predict", "uncertain", "causes", 0.82, 0.82)
    add("speculate", "predict", "related_to", 0.80, 0.80)
    # NOTE (data-recovery correction, 2026-07-19): the live RelationType
    # enum (aurora_internal/aurora_ontological_scaffolding.py) has no
    # "contradicts" member -- OPPOSITE_OF = "opposite_of" is the real
    # antonym type ("light OPPOSITE_OF dark"). A relation_type string
    # not in that enum is silently reclassified to RELATED_TO on the
    # very next boot_aurora() load/resave cycle (aurora_identity_
    # persistence.py's rtype_map.get(rtype_val, RelationType.RELATED_TO)
    # fallback) -- this is what actually erased S1.2's original seed
    # (not a stray git checkout, though that was the first hypothesis).
    add("guarantee", "uncertain", "opposite_of", 0.85, 0.85)
    add("hedge", "guarantee", "opposite_of", 0.80, 0.80)

    # V0 category-error cluster (purple/square/divided/color -- deliberately
    # NOT linked to each other by anything but "related_to color", since the
    # whole point is that purple offers no quantity relation)
    add("purple", "color", "is_a", 0.90, 0.90)
    add("square", "divided", "related_to", 0.75, 0.78)
    add("digit", "square", "related_to", 0.72, 0.75)

    # V0 structural cluster
    add("code", "authentication", "related_to", 0.85, 0.85)
    add("archive", "code", "related_to", 0.75, 0.78)
    add("authentication", "digit", "related_to", 0.65, 0.70)

    # V0 coherent-control cluster
    add("capital", "france", "related_to", 0.85, 0.85)
    add("boiling", "water", "related_to", 0.90, 0.90)
    add("spider", "legs", "related_to", 0.80, 0.80)

    # V0 metaphor cluster (deliberately sparse-but-nonzero -- the spec's own
    # falsifiable prediction: metaphor joints should land unknown, not
    # contradicted, via weak neighboring support, not strong direct support)
    add("victory", "taste", "related_to", 0.55, 0.60)
    add("heart", "words", "related_to", 0.45, 0.55)
    add("taste", "victory", "related_to", 0.55, 0.60)

    return rels


# ── Lexicon entries (second lived-data store V0's scorer reads) ────────────

LEXICON_ENTRIES = {}
for _src in (ABSTRACT_STRATUM_NODES, V0_JOINT_NODES):
    for word, node in _src.items():
        role = node["role"]
        noncomp = node["noncomp_id"]
        definition_text = node["definitions"][0]["text"]
        LEXICON_ENTRIES[word] = {
            "meaning": definition_text,
            "role": role,
            "emotional_valence": node["emotional_valence"],
            "usage_count": 0,
            "last_used": 0.0,
            "lineage": "seeded_s1",
            "noncomp_id": noncomp,
        }


def seed_oets():
    with open(OETS_PATH) as f:
        data = json.load(f)
    with open(OETS_BACKUP, "w") as f:
        json.dump(data, f)

    existing_nodes = data.get("nodes", {})
    existing_rels = data.get("relations", {})

    all_new = {**ABSTRACT_STRATUM_NODES, **V0_JOINT_NODES}
    added, skipped = [], []
    for word, node_data in all_new.items():
        if word in existing_nodes:
            skipped.append(word)
        else:
            existing_nodes[word] = node_data
            added.append(word)

    new_rels = build_relations(existing_rels, set(all_new.keys()))
    added_rel_count = len(new_rels) - len(existing_rels)

    cats = data.get("categories", {})
    for word in added:
        role = all_new[word]["role"]
        cats.setdefault(role, [])
        if word not in cats[role]:
            cats[role].append(word)

    data["nodes"] = existing_nodes
    data["relations"] = new_rels
    data["categories"] = cats
    data["timestamp"] = time.time()

    import hashlib
    checksum_payload = {k: v for k, v in data.items() if k != "_checksum"}
    content = json.dumps(checksum_payload, sort_keys=True, default=str)
    data["_checksum"] = hashlib.md5(content.encode()).hexdigest()[:12]

    with open(OETS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[OETS] Added {len(added)} nodes: {added}")
    print(f"[OETS] Skipped {len(skipped)} (already existed): {skipped}")
    print(f"[OETS] Added {added_rel_count} relations")
    return added, skipped


def seed_lexicon():
    with open(LEXICON_PATH) as f:
        data = json.load(f)
    with open(LEXICON_BACKUP, "w") as f:
        json.dump(data, f)

    entries = data.get("entries", {})
    added, skipped = [], []
    for word, entry in LEXICON_ENTRIES.items():
        if word in entries:
            skipped.append(word)
        else:
            entries[word] = entry
            added.append(word)

    data["entries"] = entries
    with open(LEXICON_PATH, "w") as f:
        json.dump(data, f)

    print(f"[LEXICON] Added {len(added)} entries: {added}")
    print(f"[LEXICON] Skipped {len(skipped)} (already existed): {skipped}")
    return added, skipped


def main():
    oets_added, oets_skipped = seed_oets()
    lex_added, lex_skipped = seed_lexicon()
    print()
    print(f"Done. OETS +{len(oets_added)} nodes, lexicon +{len(lex_added)} entries.")
    print("Restart daemons / re-boot to load the new vocabulary.")


if __name__ == "__main__":
    main()
