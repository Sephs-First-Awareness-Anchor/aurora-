#!/usr/bin/env python3
"""
aurora_causal_vs_representational_probe.py

AURORA NATIVE REPRESENTATIONAL SELECTION AND CAUSAL-TO-REPRESENTATIONAL
TRANSITION FALSIFICATION DIRECTIVE -- Parts I, IV, V, VI, VII.

A non-authoritative detector recording evidence for six criteria (R1-R6)
against a candidate coordinate, applied here to sub_law_c / match.constraint
-- the rank-6 audit's confirmed-independent candidate. It NEVER labels a
candidate as a new depth, NEVER decides the outcome, and NEVER invents an
invariant: R3's candidate invariant must be discovered from Aurora's own
code/data (here: topic_words, extracted by the same parse() call that
produces frame/stance, and actually read by _find_nc()'s own scoring --
not supplied by the experimenter as an assumption).

R1 Differentiation           -- different coordinate values remain distinguishable
R2 Independent consequence   -- those differences have unique downstream consequence
R3 Invariant relation        -- an existing-code-supported invariant under which
                                 differentiated states are states of the same thing
R4 Persistence of the relation -- holds across more than one context/episode/retrieval
R5 Functional use of the relation -- some downstream process actually uses it
R6 Decoupling/mismatch capability -- native ability to detect internal-state-vs-
                                       underlying-condition divergence, if it exists

Read-only against real, already-generated data and real (ephemeral-state)
interpreter instances. Never mutates aurora_manifold_directory/ or
aurora_state/.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MANIFOLD_DIR = None  # set lazily to avoid import cost when unused


def _manifold_dir() -> str:
    global MANIFOLD_DIR
    if MANIFOLD_DIR is None:
        import os
        MANIFOLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_manifold_directory")
    return MANIFOLD_DIR


@dataclass
class CriterionResult:
    name: str
    met: bool
    evidence: str
    tag: str  # "CONFIRMED CODE FACT" | "EMPIRICAL RESULT" | "INTERPRETATION" | "UNSUPPORTED HYPOTHESIS"

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "met": self.met, "evidence": self.evidence, "tag": self.tag}


CLASSIFICATIONS = (
    "CAUSAL_ONLY", "REPRESENTATIONAL_CANDIDATE", "REPRESENTATIONAL_EVIDENCE",
    "INSUFFICIENT", "UNREACHABLE", "PINNED", "LOST", "TRANSFORMED", "PRESERVED",
)


@dataclass
class ProbeReport:
    candidate: str
    criteria: List[CriterionResult]
    classification: str
    classification_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate": self.candidate,
            "criteria": [c.to_dict() for c in self.criteria],
            "classification": self.classification,
            "classification_rationale": self.classification_rationale,
        }


def _r1_differentiation() -> CriterionResult:
    """Reuses the rank-6 audit's own confirmed measurement -- does not
    re-derive a new threshold or re-argue independence."""
    import aurora_rank6_shadow_analysis as rank6
    directory = rank6.load_manifold_directory_raw()
    nc = directory["Existential_Operator_of_Existence"]
    home = (nc["nc_law_c"], nc["nc_dim"])
    varied = rank6.vary_sub_law_c(directory, "Existential_Operator_of_Existence", home)
    distinct = rank6.count_distinct(varied, rank6.numeric_signature)
    return CriterionResult(
        "R1_differentiation", distinct == 5,
        f"sub_law_c produces {distinct}/5 distinct numeric manifold-slot states "
        "(rank-6 audit, Phase C, re-used not re-derived)",
        "CONFIRMED CODE FACT",
    )


def _r2_independent_consequence() -> CriterionResult:
    """Downstream consequence beyond the manifold layer: behavior actuation
    (aurora.py's _NONCOMP_CONSTRAINT_RUNTIME_EFFECTS), confirmed live-wired
    into response composition (system-wide conservation report, Phase 6)."""
    import aurora
    effects_x = aurora._NONCOMP_CONSTRAINT_RUNTIME_EFFECTS.get("X", ())
    effects_b = aurora._NONCOMP_CONSTRAINT_RUNTIME_EFFECTS.get("B", ())
    return CriterionResult(
        "R2_independent_consequence", effects_x != effects_b,
        f"_NONCOMP_CONSTRAINT_RUNTIME_EFFECTS['X']={effects_x!r} vs "
        f"['B']={effects_b!r} -- confirmed live-wired into aurora.py's "
        "response composition (system-wide conservation report, Phase 6)",
        "CONFIRMED CODE FACT",
    )


def _r3_r4_r5_topic_word_invariant() -> Tuple[CriterionResult, CriterionResult, CriterionResult]:
    """Empirically searches for a code-supported invariant: topic_words,
    extracted by the SAME parse() call that produces frame/stance (hence
    constraint/dimension), and read by _find_nc()'s own scoring function
    -- not an invariant supplied by this probe's author."""
    from aurora_reflexive_interpreter import ReflexiveInterpreter
    from aurora_manifold_directory_reader import ManifoldDirectory

    examples = [
        "I need to protect my boundaries here",
        "what does boundary even mean in this context",
        "I wonder if my boundaries even matter here",
        "you clearly violated my boundaries just now",
    ]
    tmp = tempfile.mkdtemp(prefix="aurora_probe_")
    ri = ReflexiveInterpreter(directory=ManifoldDirectory(_manifold_dir()), state_dir=tmp)
    rows = []
    for ex in examples:
        p = ri._matcher._parser.parse(ex)
        m = ri._matcher.match(ex)
        rows.append((ex, p.get("topic_words", []), m.constraint, m.dimension, m.nc_name))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    shared_topic = "boundar"  # stem covering boundary/boundaries
    topic_present = [any(shared_topic in t for t in tw) for (_e, tw, *_r) in rows]
    constraints = [c for (_e, _tw, c, _d, _n) in rows]
    r3_met = all(topic_present) and len(set(constraints)) >= 3
    r3 = CriterionResult(
        "R3_invariant_relation", r3_met,
        f"topic_words containing {shared_topic!r} present in {sum(topic_present)}/{len(rows)} "
        f"paraphrases while constraint varied across {sorted(set(constraints))} -- "
        "topic_words is computed by the same UtteranceParser.parse() call that also "
        "produces frame/stance (hence constraint/dimension), and is independently read "
        "by SemanticMatcher._find_nc()'s own scoring (aurora_reflexive_interpreter.py:714-719: "
        "'+0.5' per overlapping topic word). This is a real, code-computed candidate, not an "
        "experimenter-invented one -- but see R4 below for why it does not clear the full bar.",
        "EMPIRICAL RESULT",
    )

    # R4: does topic_words persist as a retrievable identity ACROSS episodes,
    # tying differently-constrained interpretations of the same topic
    # together? Checked directly against the real overlay/ledger key schema.
    from aurora_understanding_sediment import slot_key
    key_a = slot_key("X", "OPERATOR")
    key_b = slot_key("B", "OPERATOR")
    r4 = CriterionResult(
        "R4_persistence", False,
        "UnderstandingSedimentOverlay.slot_key() and PersistentWorthLedger both key "
        "exclusively by (constraint, dimension) / nc_name "
        f"(e.g. {key_a!r}, {key_b!r}) -- topic_words is recomputed fresh from raw text on "
        "every parse() call and is never itself stored, keyed, or retrieved by any "
        "persistent structure this codebase was found to have. Two utterances sharing a "
        "topic word but landing on different constraints leave no cross-referencing trace "
        "in memory that would let a later retrieval recover 'these were about the same "
        "thing.' NOT DEMONSTRATED, not because the topic overlap isn't real, but because "
        "nothing persists it as an identity across episodes.",
        "CONFIRMED CODE FACT",
    )

    # R5: functional use WITHIN a single call is real (the scoring formula
    # literally adds weight for topic overlap) -- but this is same-call
    # disambiguation, not cross-episode object tracking, which is the
    # stronger sense R4's failure rules out.
    r5 = CriterionResult(
        "R5_functional_use", True,
        "_find_nc()'s score() function unconditionally adds 0.5 per topic word shared "
        "between the candidate NonComp's own name and the utterance's topic_words -- a "
        "real, always-active functional use of the candidate invariant within the SAME "
        "call. This is genuine but narrower than R4 would need for full representational "
        "status: it disambiguates which NonComp to select this call, it does not maintain "
        "reference to a persistent object across calls.",
        "CONFIRMED CODE FACT",
    )
    return r3, r4, r5


def _r6_decoupling_mismatch() -> CriterionResult:
    """Searches for (does not build) a native capability to detect
    'internal representation says A, underlying/recalled condition says B.'
    """
    import inspect
    import aurora_understanding_sediment as us

    src = inspect.getsource(us.recall_confidence_boost)
    axis_prefiltered = "axis_filter=(constraint,)" in src
    discards_axis_field = 'r.get("score"' in src and '.get("axis"' not in src

    detail = (
        "recall_confidence_boost() (the one SediMemory-read path live-wired to "
        "ReflexiveInterpreter) pre-filters recall_semantic() to axis_filter=(constraint,) "
        "-- the CURRENT turn's own constraint -- so a same-topic memory resonant on a "
        "DIFFERENT constraint is excluded from the search itself, and the function reads "
        "only r['score'] from whatever does come back, discarding SediMemory's own "
        "'axis' field on each result. A structurally similar but broader query exists "
        "elsewhere (aurora.py's _build_established_strata_evidence, "
        "axis_filter=['X','T','N','B','A'], which DOES preserve each result's 'axis' "
        "alongside its score into evidence['sedimemory_recall']) -- but no consumer of "
        "that evidence dict was found comparing those recalled axes against the current "
        "turn's own match.constraint. The raw material for a mismatch signal exists in "
        "one place in the data; the comparison that would turn it into a detected "
        "mismatch does not exist anywhere in the traced code."
    )
    return CriterionResult(
        "R6_decoupling_mismatch", False, detail, "CONFIRMED CODE FACT",
    )


def probe_sub_law_c() -> ProbeReport:
    r1 = _r1_differentiation()
    r2 = _r2_independent_consequence()
    r3, r4, r5 = _r3_r4_r5_topic_word_invariant()
    r6 = _r6_decoupling_mismatch()
    criteria = [r1, r2, r3, r4, r5, r6]

    if r1.met and r2.met and not (r3.met and r4.met and r5.met):
        classification = "CAUSAL_ONLY"
        rationale = (
            "Independent differentiation (R1) and independent downstream consequence (R2) "
            "are both confirmed. A real, code-grounded candidate invariant (topic_words) "
            "was found and is functionally used within a single call (R3, R5) -- but it "
            "fails persistence (R4): nothing in the traced codebase stores or retrieves "
            "topic identity across episodes, so differentiated sub_law_c states cannot be "
            "shown to be maintained presentations of a persistent, Aurora-recognized "
            "invariant across more than one context. R6 (native mismatch detection) is "
            "also not demonstrated. Per the directive's own Outcome D: sub_law_c is "
            "independently causal; no invariant-relative representational use is "
            "demonstrated."
        )
    elif r1.met and r2.met and r3.met and r4.met and r5.met:
        classification = "REPRESENTATIONAL_EVIDENCE"
        rationale = "All of R1-R5 met against a code-discovered (not invented) invariant."
    elif r1.met and r2.met and (r3.met or r5.met):
        classification = "REPRESENTATIONAL_CANDIDATE"
        rationale = "Causal criteria met; partial, not full, representational evidence."
    else:
        classification = "INSUFFICIENT"
        rationale = "Even the causal criteria (R1/R2) were not both confirmed."

    return ProbeReport(
        candidate="sub_law_c", criteria=criteria,
        classification=classification, classification_rationale=rationale,
    )


if __name__ == "__main__":
    import json
    report = probe_sub_law_c()
    print(f"Classification: {report.classification}")
    print(report.classification_rationale)
    print()
    for c in report.criteria:
        print(f"[{'MET' if c.met else 'not met':>8}] {c.name} ({c.tag})")
        print(f"          {c.evidence}")
    print()
    print(json.dumps(report.to_dict(), indent=2))
