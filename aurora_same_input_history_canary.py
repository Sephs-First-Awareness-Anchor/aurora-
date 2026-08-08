#!/usr/bin/env python3
"""
aurora_same_input_history_canary.py

AURORA NATIVE REPRESENTATIONAL SELECTION AND CAUSAL-TO-REPRESENTATIONAL
TRANSITION FALSIFICATION DIRECTIVE -- Part III.

Central test: can the same present input receive a different representational
coordinate (constraint, dimension) solely because Aurora has experienced a
different valid prior history?

Two histories are built using ONLY existing, real experiential mechanisms
(repeated real ReflexiveInterpreter.interpret() calls, which naturally
deposit into UnderstandingSedimentOverlay and PersistentWorthLedger through
their own already-existing code paths -- nothing is written to those stores
directly). The same test input is then presented under both histories and
every value upstream of and during coordinate selection is captured and
compared.

Explicit control, honored throughout this module: nothing here ever directly
sets/edits a selected constraint, dimension, SlotCoord, SemanticMatcher
return value, routing table, or frame/stance mapping. Every observed
difference (or lack of one) must arise from an existing Aurora mechanism.

Read-only / ephemeral-state: uses tempdir state directories; never touches
aurora_state/ or aurora_manifold_directory/.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

MANIFOLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_manifold_directory")

TEST_INPUT = "I need to protect my boundaries here"

# History P: repeated exposure to expressions that land on the SAME
# nc_name/coordinate family as the test input and are understood (real
# consequence: WorthHistory rises, UnderstandingSedimentOverlay deposits
# accumulate for that key) -- via ReflexiveInterpreter.interpret() only.
HISTORY_P_EXPOSURES = [
    "I need to protect my boundaries here",
    "I need to protect my boundaries here",
    "I need to protect my boundaries here",
    "I need to protect my boundaries here",
    "I need to protect my boundaries here",
]

# History Q: repeated exposure to expressions landing on a DIFFERENT
# nc_name/coordinate family entirely -- a genuinely different real
# experiential history, built the same way.
HISTORY_Q_EXPOSURES = [
    "This costs too much energy for me",
    "This costs too much energy for me",
    "This costs too much energy for me",
    "This costs too much energy for me",
    "This costs too much energy for me",
]


@dataclass
class SelectionSnapshot:
    """Every value upstream of and during coordinate selection, for one
    interpret() call."""
    expression: str
    frame: Optional[str]
    stance: Optional[str]
    pragmatic_signal_roles: List[str]
    topic_words: List[str]
    query_type: Optional[str]
    match_confidence: float
    semantic_override: Optional[str]
    constraint: str
    dimension: str
    nc_name: Optional[str]
    # Downstream of selection -- included for contrast, not part of the
    # "selection inputs" comparison itself.
    worth_score: float
    field_region: str
    is_understood: bool

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            expression=self.expression, frame=self.frame, stance=self.stance,
            pragmatic_signal_roles=self.pragmatic_signal_roles, topic_words=self.topic_words,
            query_type=self.query_type, match_confidence=self.match_confidence,
            semantic_override=self.semantic_override, constraint=self.constraint,
            dimension=self.dimension, nc_name=self.nc_name, worth_score=self.worth_score,
            field_region=self.field_region, is_understood=self.is_understood,
        )

    def selection_input_key(self) -> tuple:
        """Everything that is (or could be) an input to coordinate
        selection. Two snapshots with an identical key had identical
        selection-time information available, regardless of what interpret()
        did with it afterward."""
        return (
            self.frame, self.stance, tuple(self.pragmatic_signal_roles),
            tuple(self.topic_words), self.query_type, self.semantic_override,
        )

    def selected_coordinate(self) -> tuple:
        return (self.constraint, self.dimension, self.nc_name)


def _build_history(state_dir: str, exposures: List[str]) -> None:
    """Builds real experiential history using ONLY ReflexiveInterpreter.
    interpret() -- the same call path a live turn uses. Never writes to the
    overlay/ledger directly."""
    from aurora_reflexive_interpreter import ReflexiveInterpreter
    from aurora_manifold_directory_reader import ManifoldDirectory

    ri = ReflexiveInterpreter(directory=ManifoldDirectory(MANIFOLD_DIR), state_dir=state_dir)
    for text in exposures:
        ri.interpret(text)  # real consequence: sediment deposit + worth record, via existing code only


def _snapshot_for(state_dir: str, test_input: str) -> SelectionSnapshot:
    """Presents test_input to a FRESH ReflexiveInterpreter instance rooted at
    state_dir (simulating a new session that inherits only the persisted
    history, nothing in-RAM), and captures every upstream-of-selection value
    by calling the real parser/matcher directly (not by re-deriving them)."""
    from aurora_reflexive_interpreter import ReflexiveInterpreter
    from aurora_manifold_directory_reader import ManifoldDirectory

    ri = ReflexiveInterpreter(directory=ManifoldDirectory(MANIFOLD_DIR), state_dir=state_dir)

    # Raw parser output -- the actual upstream signal available before any
    # constraint/dimension classification happens.
    parsed = ri._matcher._parser.parse(test_input) if ri._matcher._parser else {}
    match = ri._matcher.match(test_input)
    state = ri.interpret(test_input)

    return SelectionSnapshot(
        expression=test_input,
        frame=parsed.get("frame"),
        stance=parsed.get("stance"),
        pragmatic_signal_roles=[s[0] for s in parsed.get("pragmatic_signals", [])],
        topic_words=list(parsed.get("topic_words", [])),
        query_type=parsed.get("query_type"),
        match_confidence=match.confidence,
        semantic_override=match.semantic_override,
        constraint=match.constraint,
        dimension=match.dimension,
        nc_name=match.nc_name,
        worth_score=state.worth_score,
        field_region=state.field_region,
        is_understood=state.is_understood,
    )


@dataclass
class CanaryResult:
    history_p: SelectionSnapshot
    history_q: SelectionSnapshot
    selection_inputs_identical: bool
    selected_coordinate_identical: bool
    downstream_worth_identical: bool
    outcome: str  # "A" | "B" | "C" -- D (forced) is structurally impossible here, nothing is forced
    outcome_detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "history_p": self.history_p.to_dict(),
            "history_q": self.history_q.to_dict(),
            "selection_inputs_identical": self.selection_inputs_identical,
            "selected_coordinate_identical": self.selected_coordinate_identical,
            "downstream_worth_identical": self.downstream_worth_identical,
            "outcome": self.outcome,
            "outcome_detail": self.outcome_detail,
        }


def run_canary() -> CanaryResult:
    tmp_p = tempfile.mkdtemp(prefix="aurora_history_p_")
    tmp_q = tempfile.mkdtemp(prefix="aurora_history_q_")
    try:
        _build_history(tmp_p, HISTORY_P_EXPOSURES)
        _build_history(tmp_q, HISTORY_Q_EXPOSURES)

        snap_p = _snapshot_for(tmp_p, TEST_INPUT)
        snap_q = _snapshot_for(tmp_q, TEST_INPUT)

        selection_inputs_identical = snap_p.selection_input_key() == snap_q.selection_input_key()
        selected_coordinate_identical = snap_p.selected_coordinate() == snap_q.selected_coordinate()
        downstream_worth_identical = (
            snap_p.worth_score == snap_q.worth_score and snap_p.field_region == snap_q.field_region
        )

        if selected_coordinate_identical and selection_inputs_identical:
            outcome = "A"
            detail = (
                "Same coordinate, identical selection inputs. The parser/matcher "
                "received bit-for-bit identical upstream signal under both "
                "histories, and produced the identical (constraint, dimension, "
                "nc_name) coordinate. No history-derived value reached "
                "coordinate selection through any path this canary exercised."
            )
        elif selected_coordinate_identical and not selection_inputs_identical:
            outcome = "B"
            detail = (
                "Same coordinate, but selection inputs differed between "
                "histories -- experiential modulation reached the selector's "
                "inputs but was insufficient to change the chosen coordinate "
                "for this test input."
            )
        else:
            outcome = "C"
            detail = (
                "Different coordinate selected under different histories, "
                "through an existing native path -- this canary did not "
                "force anything; if this branch is reached, the exact "
                "differing selection-input field is the mechanism."
            )

        return CanaryResult(
            history_p=snap_p, history_q=snap_q,
            selection_inputs_identical=selection_inputs_identical,
            selected_coordinate_identical=selected_coordinate_identical,
            downstream_worth_identical=downstream_worth_identical,
            outcome=outcome, outcome_detail=detail,
        )
    finally:
        import shutil
        shutil.rmtree(tmp_p, ignore_errors=True)
        shutil.rmtree(tmp_q, ignore_errors=True)


if __name__ == "__main__":
    result = run_canary()
    print(f"Outcome: {result.outcome}")
    print(result.outcome_detail)
    print()
    print("History P snapshot:", json.dumps(result.history_p.to_dict(), indent=2))
    print("History Q snapshot:", json.dumps(result.history_q.to_dict(), indent=2))
    print()
    print("selection_inputs_identical:", result.selection_inputs_identical)
    print("selected_coordinate_identical:", result.selected_coordinate_identical)
    print("downstream_worth_identical:", result.downstream_worth_identical)
