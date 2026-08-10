#!/usr/bin/env python3
"""
AURORA GENEALOGY DIFFERENCE PRODUCER OBSERVATORY — REPORT RUN (Phase 3A.2)
================================================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Drives BOTH real call sites together -- a real producer
(`aurora_training_pulse.TrainingPulse._record_and_snapshot()`) and a real
consumer (`aurora_grammar_engine.GrammarEngine._log_relief_to_genealogy()`)
-- against a SHARED tick sequence and a SHARED `run_id`, with both the
producer sidecar (this phase) and the consumer sidecar (Phase 3A.1)
installed, then runs `correlate_producer_consumer()` on the result. This is
the dynamic complement to the static call-site catalog in this module's own
docstring: it directly tests whether two real call sites that plausibly
could fire "in the same turn" of a live session show any temporal or causal
connection when actually exercised together, rather than only arguing from
reading the source.

No behavioral wiring. No promotion gate output is read. See
docs/GENEALOGY_NATIVE_ENVIRONMENT_REPORT.md section 13.

IMPORTANT CAVEAT ON WHAT THIS DEMONSTRATES: this script's "same tick"
producer/consumer proximity is a property of the test design here (both
real call sites are driven, deliberately, from the same loop, once per
iteration) -- it validates that the correlation MECHANISM correctly
detects a same-tick/no-causal-link (Case B) pattern when one is actually
present, not a claim that real, unattended Aurora execution autonomously
interleaves TrainingPulse and GrammarEngine calls this tightly. The
static, code-level finding (producer outputs are never read by any known
consumer call site, confirmed by reading every real call site found) is
the stronger, non-synthetic evidence; this run demonstrates the instrument
works, using two real call sites, not a claim about their natural
co-occurrence rate in the wild.

KNOWN SIDE EFFECT: exercising GrammarEngine._log_relief_to_genealogy()
repeatedly can trigger real promotion-gate rejections, which write to the
shared aurora_state/pressure_experiences.jsonl singleton (see Phase 3A.1's
same finding). `git checkout -- aurora_state/pressure_experiences.jsonl`
after running this manually if you want the repo left byte-identical.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger
from aurora_internal.aurora_difference_buffer import DifferenceHistoryBuffer

from aurora_genealogy_cooccurrence_observatory import install as install_consumer_observatory
from aurora_genealogy_difference_producer_observatory import (
    install_producer_observatory,
    correlate_producer_consumer,
)


def run_combined_live_exercise(n_ticks: int = 12):
    import aurora_grammar_engine
    import aurora_training_pulse

    run_id = "phase3a2_combined_run"
    logger = ConstraintGenealogyLogger(run_id=run_id, output_dir=tempfile.mkdtemp())

    consumer_sink, uninstall_consumer = install_consumer_observatory(logger)
    producer_sink, uninstall_producer = install_producer_observatory()

    engine = aurora_grammar_engine.GrammarEngine(state_dir=tempfile.mkdtemp())
    engine.set_genealogy(logger)

    systems = {"_diff_history_buffer": DifferenceHistoryBuffer(), "run_id": run_id}
    pulse = aurora_training_pulse.TrainingPulse(systems)

    for i in range(n_ticks):
        pulse._tick = i
        pulse._record_and_snapshot()  # real producer call, same run/tick sequence
        engine._log_relief_to_genealogy(text_changed=True, clarity=0.5 + (i % 3) * 0.1, motif=None)  # real consumer call

    uninstall_consumer()
    uninstall_producer()
    return producer_sink, consumer_sink


if __name__ == "__main__":
    producer_sink, consumer_sink = run_combined_live_exercise()

    print(f"Producer observations: {len(producer_sink)}")
    print(f"Consumer observations: {len(consumer_sink)}")
    eligible = [o for o in consumer_sink if o.pair_eligible]
    print(f"Pair-eligible consumer observations: {len(eligible)}")
    print()

    finding = correlate_producer_consumer(producer_sink, consumer_sink, tick_window=2)
    print(f"Correlation case: {finding.case}")
    print(f"Detail: {finding.detail}")
    print()

    print("Sample producer observation:", producer_sink[0].to_dict() if producer_sink else None)
    print("Sample consumer observation:", eligible[0].to_dict() if eligible else None)
