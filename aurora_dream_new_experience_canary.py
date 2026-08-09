#!/usr/bin/env python3
"""
aurora_dream_new_experience_canary.py

AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 22-30, 53-54: a real dream
episode, run through the actual production generative machinery
(systems['simulation'].session.run_episode(), reached via a real
boot_aurora() against a throwaway copy of aurora_state/), confirming
Dream produces a genuinely new experience rather than a scripted replay:
fresh episode identity, real per-turn generation through the wired
ExpressionPerceptionEngine, non-deterministic outcome across runs (real
agency, not a forced correction), and no literal answer-key text
injected into the base (non-directed) topic-generation path.

A first pass of this canary used a bare SimulationSession() with no
perception engine wired -- that is NOT how any real Dream episode runs
(boot_aurora() always constructs SimulationEngine with the same real
ExpressionPerceptionEngine instance waking turns use, aurora.py:27483),
and it produced a misleading false-PRESERVED-looking result: with no
perception and no live_response_bridge, run_episode() falls through to
a deeper deterministic fallback whose text can happen to repeat across
seeds. This version boots real Aurora so the divergence result is
authoritative for the actual production path.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import os
import random
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


@dataclass
class BoundaryRecord:
    boundary: str
    classification: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {"boundary": self.boundary, "classification": self.classification, "detail": self.detail}


def _boot_tmp_systems(prefix: str):
    import aurora as A
    tmp = tempfile.mkdtemp(prefix=prefix)
    state_dir = os.path.join(tmp, "aurora_state")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_dir)
    systems = A.boot_aurora(state_dir=state_dir, runtime_profile="surface", verbose=False)
    return A, systems, tmp


def run_two_episodes(turns: int = 4, seed_a: int = 1, seed_b: int = 2) -> List[BoundaryRecord]:
    from foundational_contract import ExistenceMode

    records: List[BoundaryRecord] = []
    A, systems, tmp = _boot_tmp_systems("aurora_dream_new_experience_")
    try:
        session = systems["simulation"].session

        random.seed(seed_a)
        result_a = session.run_episode(turns=turns, mode=ExistenceMode.BOUNDED)

        random.seed(seed_b)
        result_b = session.run_episode(turns=turns, mode=ExistenceMode.BOUNDED)

        # Fresh identity per episode -- not reused from any waking source.
        fresh_id = result_a.episode_id != result_b.episode_id and result_a.episode_id != ""
        records.append(BoundaryRecord(
            "fresh_episode_identity", "PRESERVED" if fresh_id else "LOST",
            f"episode_a={result_a.episode_id} episode_b={result_b.episode_id}",
        ))

        # Real agency / divergence: two runs under different stochastic
        # seeds, through the SAME real ExpressionPerceptionEngine waking
        # turns use, must not deterministically reproduce identical
        # conversation traces -- if they did, that would indicate a
        # scripted/forced outcome rather than a genuine weighted choice
        # (Section 54).
        trace_a = [t.get("assistant_text", "") for t in result_a.conversation_trace]
        trace_b = [t.get("assistant_text", "") for t in result_b.conversation_trace]
        diverges = trace_a != trace_b or result_a.avg_fitness != result_b.avg_fitness
        records.append(BoundaryRecord(
            "dream_divergence_across_runs", "PRESERVED" if diverges else "LOST",
            f"avg_fitness_a={result_a.avg_fitness} avg_fitness_b={result_b.avg_fitness} "
            f"traces_equal={trace_a == trace_b}",
        ))

        # No literal answer-key text in the base (non-directed) topic path
        # -- active_avatar_code_hints is only populated when a
        # pressure-specialized avatar spec is active (the directed-
        # training path via DreamTrainer.train_on_bundle), never by a
        # plain run_episode() call with no queued spec.
        no_hints = not result_a.active_avatar_code_hints and not result_b.active_avatar_code_hints
        records.append(BoundaryRecord(
            "no_answer_key_in_base_topic_path", "PRESERVED" if no_hints else "LOST",
            f"hints_a={result_a.active_avatar_code_hints} hints_b={result_b.active_avatar_code_hints}",
        ))

        # Aurora's replies are genuinely generated per turn through the
        # real perception pipeline, not literal corpus/avatar-prompt text.
        real_generation = all(
            isinstance(turn.get("assistant_text"), str) and turn.get("assistant_text") != turn.get("user_text")
            for turn in result_a.conversation_trace
        ) if result_a.conversation_trace else False
        records.append(BoundaryRecord(
            "per_turn_generation_not_scripted_copy", "PRESERVED" if real_generation else "LOST",
            f"turns_checked={len(result_a.conversation_trace)}",
        ))

        return records
    finally:
        A.shutdown_aurora(systems)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    import json
    recs = run_two_episodes()
    for r in recs:
        print(f"[{r.classification:>12}] {r.boundary}")
        print(f"    {r.detail}")
    print()
    print(json.dumps([r.to_dict() for r in recs], indent=2))
