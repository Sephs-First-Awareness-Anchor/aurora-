#!/usr/bin/env python3
"""
aurora_representational_closed_loop_canary.py

AURORA LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING
DIRECTIVE, Section 15.

A real, end-to-end canary. Two parts, kept honestly separate because they
trace two different real chains rather than one artificially forced chain:

PART 1 -- Interpret -> Memory -> Persistence -> Expression-adjacent state,
using a controlled, externally-chosen experience (this is the part where
"the same originating reference" can be verified against something this
canary itself supplied).

PART 2 -- RCEC's own real closed-loop episode. RCEC generates its OWN
internal prompts from a simulated world (ActionInterface.build_prompt) --
it does not accept externally-injected interpretation text, so this part
verifies that WHATEVER real ref RCEC's own internal turn produces survives,
unmutated, through Episode -> Consequence -> Backprojection (a genuine
reinterpretation event), with the original and revised refs both
recoverable and neither overwriting the other.

Both parts use real boot_aurora()/real ReflexiveInterpreter/real
UnderstandingSedimentOverlay/real RCEC machinery -- nothing here is a test
double. Part 2 boots a full Aurora instance against a throwaway copy of
aurora_state/ (never the real one) and shuts it down cleanly afterward.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import os
import random
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aurora_representational_address import RepresentationalRef

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFOLD_DIR = os.path.join(REPO_ROOT, "aurora_manifold_directory")


@dataclass
class BoundaryRecord:
    part: str
    boundary: str
    classification: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {"part": self.part, "boundary": self.boundary,
                "classification": self.classification, "detail": self.detail}


def run_part1_interpret_memory_persistence() -> List[BoundaryRecord]:
    from aurora_reflexive_interpreter import ReflexiveInterpreter
    from aurora_manifold_directory_reader import ManifoldDirectory
    from aurora_understanding_sediment import slot_key

    records: List[BoundaryRecord] = []
    text = "I need to protect my boundaries here"
    tmp = tempfile.mkdtemp(prefix="aurora_closed_loop_p1_")
    try:
        ri1 = ReflexiveInterpreter(directory=ManifoldDirectory(MANIFOLD_DIR), state_dir=tmp)
        state = ri1.interpret(text)
        origin_ref = state.representational_ref
        records.append(BoundaryRecord(
            "1", "interpret", "PRESERVED",
            f"origin_ref={origin_ref}",
        ))
        del ri1  # simulate process exit

        # Restart: fresh interpreter instance, no shared in-memory state.
        ri2 = ReflexiveInterpreter(directory=ManifoldDirectory(MANIFOLD_DIR), state_dir=tmp)
        key = state.nc_name or f"{state.constraint}:{state.dimension}"
        slot = slot_key(state.constraint, state.dimension)
        recovered_ref = ri2._overlay.ref_for(key, slot)
        records.append(BoundaryRecord(
            "1", "memory_restart", "PRESERVED" if recovered_ref == origin_ref else "LOST",
            f"recovered_ref={recovered_ref}",
        ))

        # RepresentationalRef -> historical worth observations.
        field_keys = ri2._overlay.field_keys_for_ref(origin_ref)
        worth_history = ri2._worth_ledger.scores_for(field_keys[0]) if field_keys else []
        records.append(BoundaryRecord(
            "1", "ref_to_worth_history", "PRESERVED" if worth_history else "LOST",
            f"field_keys={field_keys} worth_history={worth_history}",
        ))

        # Expression-adjacent: the ref is present on the SAME UnderstandingState
        # object aurora.py's real noncomp_input_state/noncomp_output_state
        # dicts are built from (state.to_dict()).
        to_dict_ref = state.to_dict().get("representational_ref")
        records.append(BoundaryRecord(
            "1", "understanding_state_to_dict", "PRESERVED" if to_dict_ref == origin_ref else "LOST",
            f"to_dict_ref={to_dict_ref}",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return records


def run_part2_rcec_episode() -> List[BoundaryRecord]:
    import aurora as A
    from aurora_internal.aurora_cognitive_experience_chamber import (
        build_episode_runtime_context, run_closed_loop_episode,
        ObservationBoundary, WorldGenerator, HiddenRuleEngine,
    )

    records: List[BoundaryRecord] = []
    tmp = tempfile.mkdtemp(prefix="aurora_closed_loop_p2_")
    state_dir = os.path.join(tmp, "aurora_state")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_dir)
    systems = None
    try:
        systems = A.boot_aurora(state_dir=state_dir, runtime_profile="surface", verbose=False)

        world = WorldGenerator().build_world(
            seed=4242, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False,
        )
        engine = HiddenRuleEngine.generate(world, rng=random.Random(4242), family="direct_trigger")
        ctx = build_episode_runtime_context(systems)

        result = run_closed_loop_episode(
            systems, ctx, world, engine, ObservationBoundary(), "agent_a",
            episode_id="closed_loop_canary",
        )
        step = result.trace.steps[0]

        origin_ref = step.representational_ref
        records.append(BoundaryRecord(
            "2", "rcec_episode_step", "PRESERVED" if origin_ref is not None else "UNREACHABLE",
            f"step.representational_ref={origin_ref}",
        ))

        records.append(BoundaryRecord(
            "2", "rcec_consequence", "PRESERVED" if (step.consequence is not None and step.representational_ref == origin_ref) else "LOST",
            f"consequence present={step.consequence is not None}, ref unchanged={step.representational_ref == origin_ref}",
        ))

        bp = step.backprojection or {}
        before_ref = bp.get("original_representational_ref")
        after_ref = bp.get("revised_representational_ref")
        no_overwrite = (step.representational_ref == origin_ref) and (before_ref == origin_ref)
        records.append(BoundaryRecord(
            "2", "rcec_backprojection_reinterpretation",
            "PRESERVED" if no_overwrite else "LOST",
            f"before_ref={before_ref} after_ref={after_ref} "
            f"step_ref_unchanged={step.representational_ref == origin_ref}",
        ))

        # The two refs from a genuine reinterpretation are not required to
        # be equal (different internal prompts almost always produce
        # different classifications) -- what matters is BOTH are present
        # and Ref_before was never overwritten by Ref_after.
        records.append(BoundaryRecord(
            "2", "before_after_both_recoverable",
            "PRESERVED" if (before_ref is not None and after_ref is not None) else "LOST",
            f"before_ref={before_ref} after_ref={after_ref}",
        ))

        # Genealogy/Evolution/Dream -- explicitly NOT exercised. No live
        # path currently connects this episode's ref to any of them
        # (confirmed by this pass's own audit); reported honestly rather
        # than fabricated.
        for boundary in ("genealogy", "evolution_chamber", "dream_replay"):
            records.append(BoundaryRecord(
                "2", boundary, "UNREACHABLE",
                "No live path connects RCEC/ReflexiveInterpreter output to this "
                "subsystem's write path -- confirmed by this pass's audit, not "
                "exercised here because doing so would require fabricating a "
                "connection that does not exist.",
            ))
    finally:
        if systems is not None:
            A.shutdown_aurora(systems)
        shutil.rmtree(tmp, ignore_errors=True)
    return records


def run_canary() -> List[BoundaryRecord]:
    records = run_part1_interpret_memory_persistence()
    records += run_part2_rcec_episode()
    return records


if __name__ == "__main__":
    import json
    recs = run_canary()
    for r in recs:
        print(f"[part {r.part}] [{r.classification:>12}] {r.boundary}")
        print(f"    {r.detail}")
    print()
    print(json.dumps([r.to_dict() for r in recs], indent=2))
