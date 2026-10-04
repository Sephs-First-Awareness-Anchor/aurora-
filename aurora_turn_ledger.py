"""
aurora_turn_ledger.py

Canonical per-turn record. One instance lives at systems["_turn_ledger"]
for the duration of a single _run_live_response_turn call, is reset at the
start of the NEXT turn, and is read by any subsystem that would otherwise
recompute something already known this turn (parse, crest ranking,
chain-down revisions, resolution, final response).

This does not replace crystal storage. It is the scratch-of-record DURING
a turn; _deposit_turn_experience_into_crystals (aurora.py) reads the
finished ledger at the end of the turn and writes the durable slice of it
into the DPS crystal, so cross-turn memory and within-turn reuse are two
separate, explicit steps instead of one function trying to do both.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time


class TurnLedger:
    __slots__ = (
        "user_text", "turn_tick", "started_at",
        "parsed", "parsed_source_text",
        "conscious_frame", "conscious_crest", "sensory_state",
        "input_state", "form_state",
        "crest_contributions", "crest_top_source",
        "chain_down_trace", "systems_touched", "final_response",
    )

    def __init__(self, user_text: str, turn_tick: Optional[int] = None) -> None:
        self.user_text = user_text
        self.turn_tick = turn_tick
        self.started_at = time.time()
        self.parsed: Dict[str, Any] = {}
        self.parsed_source_text: str = ""
        # Representational state of THIS turn's input, measured before the turn's
        # own observation creates any nodes (see aurora._input_representation_state).
        self.input_state: Dict[str, Any] = {}
        # Which reply form was delivered against that state, and whether the state
        # supported it (aurora._record_reply_form_state).
        self.form_state: Dict[str, Any] = {}
        self.conscious_frame: Dict[str, Any] = {}
        self.conscious_crest: Dict[str, Any] = {}
        self.sensory_state: Dict[str, Any] = {}
        self.crest_contributions: List[Dict[str, Any]] = []
        self.crest_top_source: str = ""
        self.chain_down_trace: List[Dict[str, Any]] = []
        self.systems_touched: List[str] = []
        self.final_response: str = ""

    def mark_touched(self, name: str) -> None:
        if name not in self.systems_touched:
            self.systems_touched.append(name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_text": self.user_text,
            "turn_tick": self.turn_tick,
            "started_at": self.started_at,
            "parsed": dict(self.parsed or {}),
            "parsed_source_text": self.parsed_source_text,
            "input_state": dict(self.input_state or {}),
            "form_state": dict(self.form_state or {}),
            "conscious_frame": dict(self.conscious_frame or {}),
            "conscious_crest": dict(self.conscious_crest or {}),
            "sensory_state": dict(self.sensory_state or {}),
            "crest_contributions": list(self.crest_contributions or []),
            "crest_top_source": self.crest_top_source,
            "chain_down_trace": list(self.chain_down_trace or []),
            "systems_touched": list(self.systems_touched or []),
            "final_response": self.final_response,
        }


def reset_turn_ledger(
    systems: Optional[Dict[str, Any]],
    user_text: str,
    turn_tick: Optional[int] = None,
) -> Optional[TurnLedger]:
    """Call ONCE, at the top of _run_live_response_turn, before any parsing
    happens. Replaces the previous turn's ledger outright -- this is scratch
    state for the turn in progress, not an accumulating log."""
    if not isinstance(systems, dict):
        return None
    ledger = TurnLedger(user_text, turn_tick=turn_tick)
    systems["_turn_ledger"] = ledger
    return ledger


def current_turn_ledger(systems: Optional[Dict[str, Any]]) -> Optional[TurnLedger]:
    """Any subsystem calls this before doing its own parse/compute to check
    whether the answer already exists for this turn."""
    if not isinstance(systems, dict):
        return None
    ledger = systems.get("_turn_ledger")
    return ledger if isinstance(ledger, TurnLedger) else None
