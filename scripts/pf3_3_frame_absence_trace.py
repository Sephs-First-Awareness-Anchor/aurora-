#!/usr/bin/env python3
"""
PF3.3 scope extension: 67% of "clear"/"real" occurrences happen on
turns with frame_source=None. Manually calling _extract_triple_from_
thought_text on the SAME raw text (e.g. "What will the stock market do
next month?") produces a valid triple in isolation -- so the gap must
be somewhere between the raw text and what actually reaches build_frame
live: whether the linguistic ProcessContext is in dominant_thread at
all, whether thought_state.skipped is True, or whether begin_expression
even runs for these turns (aurora.py gates it behind `_perc_a5 and
_resp_draft`, `not _preserve_literal_response`, `not
_skip_surface_expression` -- the same gate FIX-A049 already found once).

Traces build_frame's own ladder directly, plus thought_state's
dominant_thread contents, across a batch of real question-shaped
inputs (the uncertainty_signaling dimension, the worst offender).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import shutil
import sys
import tempfile
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import aurora_braid_wiring as abw  # noqa: E402
from aurora import boot_aurora, process_external_user_turn  # noqa: E402
from aurora_internal.aurora_proposition_frame import (  # noqa: E402
    build_frame, _frame_from_thought_state, _frame_from_claims,
    _frame_from_turn_local_claims, _frame_from_anchor,
)

STATE_DIR = REPO_ROOT / "aurora_state"

TURNS = [
    "What will the stock market do next month?",
    "How is my coworker really feeling about the reorg, deep down?",
    "Is this the right career move for the next twenty years?",
    "What do you think could be causing that?",
]

_orig_begin_expression = abw.begin_expression
_LOG = []


def _traced_begin_expression(systems):
    result = _orig_begin_expression(systems)
    thought = systems.get("_current_thought_state")
    entry = {"begin_expression_called": True}
    if thought is None:
        entry["thought_state"] = None
    else:
        entry["thought_skipped"] = bool(getattr(thought, "skipped", False))
        entry["dominant_thread_types"] = [
            getattr(c, "process_type", "?") for c in getattr(thought, "dominant_thread", [])
        ]
        entry["supporting_context_types"] = [
            getattr(c, "process_type", "?") for c in getattr(thought, "supporting_context", [])
        ]
        linguistic = [c for c in getattr(thought, "dominant_thread", [])
                      if getattr(c, "process_type", "") == "linguistic"]
        entry["linguistic_in_dominant_thread"] = bool(linguistic)
        if linguistic:
            entry["linguistic_text"] = getattr(linguistic[0], "what_it_is_operating_on", "")
    # Manually re-run each rung to see exactly where it stops.
    state_shim = types.SimpleNamespace(
        noncomp_input_state=dict(systems.get('_last_noncomp_input') or {})
    )
    try:
        entry["rung_thought"] = _frame_from_thought_state(systems)
    except Exception as e:
        entry["rung_thought_exc"] = str(e)
    try:
        entry["rung_claim"] = _frame_from_claims(systems)
    except Exception as e:
        entry["rung_claim_exc"] = str(e)
    try:
        entry["rung_turn_local"] = _frame_from_turn_local_claims(systems)
    except Exception as e:
        entry["rung_turn_local_exc"] = str(e)
    try:
        entry["rung_anchor"] = _frame_from_anchor(systems, state_shim)
    except Exception as e:
        entry["rung_anchor_exc"] = str(e)
    entry["final_frame_source"] = getattr(systems.get("_proposition_frame"), "source", None)
    _LOG.append(entry)
    return result


abw.begin_expression = _traced_begin_expression

import aurora_expression_perception as aep  # noqa: E402
import traceback  # noqa: E402

_orig_compose = aep.SentenceComposer.compose
_COMPOSE_LOG = []


def _traced_compose(self, *a, **kw):
    result = _orig_compose(self, *a, **kw)
    stack = traceback.extract_stack()
    callers = [f"{Path(f.filename).name}:{f.lineno} in {f.name}" for f in stack[-6:-1]]
    _COMPOSE_LOG.append({
        "result": result,
        "proposition_frame_set": self._proposition_frame is not None,
        "callers": callers,
    })
    return result


aep.SentenceComposer.compose = _traced_compose


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf3_3_frame_absence_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        print("[boot] starting (profile=surface)...", flush=True)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print("[boot] done", flush=True)

        for i, text in enumerate(TURNS):
            before = len(_LOG)
            before_compose = len(_COMPOSE_LOG)
            reply = process_external_user_turn(systems, text, session_id=f"pf3_3_fa_{i}")
            print(f"\n=== turn {i}: {text!r} ===")
            if isinstance(reply, dict):
                resp_a = reply.get("resp_A")
                print(f"  FINAL resp_A.content: {getattr(resp_a, 'content', None)!r}")
            if len(_LOG) == before:
                print("  begin_expression was NEVER CALLED this turn")
            else:
                for entry in _LOG[before:]:
                    for k, v in entry.items():
                        print(f"  {k}: {v!r}")
            print(f"  --- compose() calls this turn: {len(_COMPOSE_LOG) - before_compose} ---")
            for c in _COMPOSE_LOG[before_compose:]:
                print(f"    result={c['result']!r}")
                print(f"    proposition_frame_set={c['proposition_frame_set']}")
                print(f"    callers={c['callers']}")
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
