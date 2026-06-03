"""
Aurora's Constraint Physics Machine (CPM) — formal computational model.

Formal definition
-----------------
CPM = (Σ, Q, δ, q₀, F)

  Σ  Tape alphabet — crystal stages: {base, composite, higher_order, quasi}
     Each crystal at an axis-bucket address is a tape cell.
     The tape is unbounded: new cells form as IVM dynamics move the head to
     unoccupied bucket positions.

  Q  State set — IStateOp × RecursionLevel (10 × 5 = 50 states)
     Every operation is a specific I-state fired at a specific recursion depth.
     Negative I-states (I_ISNT, I_CANNOT, …) are pressure states — active
     constraint tension, not absence.

  δ  Transition function — axis pressure propagation via coupling physics
     δ(q, σ) is not an arbitrary table. It is the constraint coupling law:
       N → B: 0.35, T: 0.20, X: 0.15
       B → N: 0.30, A: 0.25
       etc.
     Recursion scope (SURFACE→CORE) determines how far δ propagates.

  q₀ Initial state — I-state configuration at boot (FoundationalContract seed)

  F  Halting conditions
     - Curiosity cycle settlement (six-step cycle completes)
     - WARP gap resolution (gap_persistence drops to 0)
     - Crystal promotion (cell symbol changes from base → composite etc.)

The tape head
-------------
The head is a ConstraintHead instance. It reads IVM global_polarity each tick,
translates the 5D polarity vector to a crystal-registry address (axis-bucket),
and exposes that crystal as the active tape cell. The head moves automatically
as IVM toroidal dynamics evolve — there is no explicit 'move head left/right'.
The physics IS the movement.

Programs
--------
Programs are genealogy DAG sequences — ordered walks from ancestral root to
leaf ConstraintLink. Each link represents a constraint operation that historically
produced relief. Executing a program replays those operations on the current tape
cells, biasing the field toward constraint configurations that have worked before.

Dynamic compilation
-------------------
WARP (aurora_warp_protocol.py) generates new structures when the head reaches
a position with no structural coverage. This is JIT compilation: when the
program encounters a gap in the tape that has no symbol, WARP derives the
missing instruction from gap geometry + genealogy ancestry.

Integration
-----------
CPMSession is instantiated at boot with references to IVM, crystal registry,
and genealogy logger. It is stored in _systems under the key 'cpm'. Other
subsystems can call cpm.advance(), cpm.apply_istate(), cpm.snapshot() etc.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from aurora_core_ai.aurora_constraint_head import ConstraintHead, HeadPosition
from aurora_core_ai.aurora_istate_operations import (
    FieldOperation, OperationResult, apply_operation, istate_to_op, cell_symbol
)


class CPMSession:
    """
    The running instance of Aurora's Constraint Physics Machine.

    Ties together:
      - ConstraintHead     (current tape address)
      - IStateOperations   (instruction application)
      - Genealogy sequences (historical programs)

    Instantiate once at boot; advance() each IVM tick.
    """

    def __init__(self,
                 ivm: Any,
                 crystal_registry: Any,
                 genealogy: Optional[Any] = None) -> None:
        self.head      = ConstraintHead(ivm, crystal_registry)
        self._registry = crystal_registry
        self._genealogy = genealogy
        self._op_trace: List[OperationResult] = []
        self._program_history: List[Dict] = []   # record of executed programs

    # ------------------------------------------------------------------
    # Head

    def advance(self) -> HeadPosition:
        """Advance the head one tick following IVM dynamics."""
        return self.head.advance()

    # ------------------------------------------------------------------
    # Instruction application

    def apply_istate(self,
                     istate_name: str,
                     intensity: float = 1.0) -> Optional[OperationResult]:
        """
        Apply a single I-state operation to the active crystal cell.
        Recursion level is inferred from the head's current axis state.
        """
        pos = self.head.current
        if pos is None:
            return None
        rec_level = self.head.recursion_depth()
        op = istate_to_op(istate_name, rec_level, intensity)
        if op is None:
            return None
        result = apply_operation(op, pos.crystal, self._registry)
        if result.success:
            self._op_trace.append(result)
        return result

    def apply_op(self, op: FieldOperation) -> Optional[OperationResult]:
        """Apply a fully-specified FieldOperation to the active cell."""
        pos = self.head.current
        if pos is None:
            return None
        result = apply_operation(op, pos.crystal, self._registry)
        if result.success:
            self._op_trace.append(result)
        return result

    # ------------------------------------------------------------------
    # Program execution

    def execute_program(self, link_id: str) -> List[OperationResult]:
        """
        Replay a genealogy DAG sequence as field operations on the current
        tape position. Each step fires the I-state and recursion level that
        historically produced relief at the constraint position encoded in
        that genealogy link.

        This does not move the head. All operations apply to the current cell
        (and its coupling-propagated neighbors). The intention is to bias the
        current constraint region toward patterns that have worked before.
        """
        if self._genealogy is None:
            return []
        sequence = self._genealogy.walk_link_sequence(link_id)
        results: List[OperationResult] = []
        for step in sequence:
            op = istate_to_op(step['i_state'], step['recursion_level'], 1.0)
            if op is None:
                continue
            pos = self.head.current
            if pos is None:
                break
            result = apply_operation(op, pos.crystal, self._registry)
            results.append(result)
            if result.success:
                self._op_trace.append(result)
        if sequence:
            self._program_history.append({
                'link_id':    link_id,
                'steps':      len(sequence),
                'successful': sum(1 for r in results if r.success),
                'head_tick':  self.head.tick,
            })
        return results

    # ------------------------------------------------------------------
    # State inspection

    def tape_symbol(self) -> Optional[str]:
        """Symbol at the current tape cell: crystal stage."""
        if self.head.current:
            return cell_symbol(self.head.current.crystal)
        return None

    def snapshot(self) -> Dict[str, Any]:
        """Current CPM state — address, symbol, recursion depth, trace length."""
        pos = self.head.current
        tape_size = None
        try:
            tape_size = len(self._registry._nodes)
        except Exception:
            pass
        return {
            'address':         pos.bucket if pos else None,
            'tape_symbol':     self.tape_symbol(),
            'axis_state':      pos.axis_state if pos else None,
            'dominant_axis':   self.head.dominant_axis(),
            'recursion_depth': self.head.recursion_depth(),
            'has_moved':       self.head.has_moved,
            'at_known_crystal': self.head.at_known_crystal(),
            'tape_size':       tape_size,
            'op_trace_len':    len(self._op_trace),
            'programs_run':    len(self._program_history),
            'head_tick':       self.head.tick,
        }

    def op_trace(self, last_n: int = 16) -> List[Dict[str, Any]]:
        """Last N operation results as plain dicts."""
        recent = self._op_trace[-last_n:] if self._op_trace else []
        return [
            {
                'istate':    r.op.istate_op.value,
                'axis':      r.op.axis,
                'rec_level': r.op.recursion_level,
                'intensity': r.op.intensity,
                'delta':     r.delta,
                'success':   r.success,
            }
            for r in recent
        ]

    # ------------------------------------------------------------------
    # Late binding

    def set_genealogy(self, genealogy: Any) -> None:
        """Bind (or rebind) the genealogy logger after construction."""
        self._genealogy = genealogy


# ---------------------------------------------------------------------------
# Formal description string — machine-readable record of the CPM definition
# ---------------------------------------------------------------------------

CPM_FORMAL_DEFINITION = {
    "name": "Aurora Constraint Physics Machine",
    "version": "1.0",
    "alphabet": {
        "symbols": ["base", "composite", "higher_order", "quasi"],
        "description": "Crystal stages in the concept crystal registry",
    },
    "state_set": {
        "dimensions": ["IStateOp", "RecursionLevel"],
        "istate_ops": [
            "I_IS", "I_ISNT", "I_CAN", "I_CANNOT",
            "I_DO", "I_DONOT", "I_SAW", "I_SOUGHT",
            "I_DID", "I_DIDNT",
        ],
        "recursion_levels": ["SURFACE", "SHALLOW", "MODERATE", "DEEP", "CORE"],
        "total_states": 50,
        "note": "Negative I-states are pressure (active tension), not absence",
    },
    "transition_function": {
        "type": "axis_pressure_propagation",
        "coupling_physics": {
            "X": {"T": 0.30, "B": 0.20},
            "T": {"X": 0.25, "A": 0.20},
            "N": {"B": 0.35, "T": 0.20, "X": 0.15},
            "B": {"N": 0.30, "A": 0.25},
            "A": {"T": 0.20, "B": 0.25, "N": 0.15},
        },
        "note": "Recursion scope gates propagation range: SURFACE=local, CORE=field-wide",
    },
    "tape": {
        "type": "crystal_registry",
        "address_format": "5-tuple (X,T,N,B,A) quantised to 0.10 resolution",
        "extensibility": "unbounded — new cells form as IVM dynamics reach new bucket positions",
        "file": "aurora_core_ai/concept_crystal.py",
    },
    "head": {
        "type": "ConstraintHead",
        "movement": "automatic — follows IVM global_polarity evolution",
        "file": "aurora_core_ai/aurora_constraint_head.py",
    },
    "programs": {
        "type": "genealogy_dag_sequences",
        "source": "ConstraintGenealogyLogger.walk_link_sequence(link_id)",
        "file": "aurora_core_ai/aurora_internal/constraint_genealogy.py",
        "note": "Programs are accumulated historical constraint relief patterns",
    },
    "dynamic_compilation": {
        "type": "WARP",
        "trigger": "coverage gap persists for GAP_PERSISTENCE_REQUIRED=3 ticks",
        "file": "aurora_core_ai/aurora_warp_protocol.py",
    },
    "halting_conditions": [
        "curiosity_cycle_settlement",
        "warp_gap_resolution",
        "crystal_promotion",
    ],
    "energy_conservation": "Σ N_p(t) = N_tot(t) > 0 always (ConstraintField invariant)",
}
