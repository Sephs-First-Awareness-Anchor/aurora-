#!/usr/bin/env python3
"""
PF3.1 (second mechanism, take 2): "upset" never appears in word_sources at
all, unlike "planning" -- ruling out find_by_noncomp entirely. Reading
_bind_slot_from_frame confirms it never writes to _last_word_sources, and
begin_expression() (aurora_braid_wiring.py:381) has TWO places composer.
_proposition_frame could go stale silently:
  1. Line 397-399: an early `return` if systems['_current_thought_state']
     is None -- set_proposition_frame (line 457) is never reached at all.
  2. Line 440-459: build_frame() + set_proposition_frame() wrapped in a
     bare `except Exception: pass` -- any exception anywhere in that block
     silently skips the refresh, leaving composer._proposition_frame at
     whatever a PREVIOUS turn set it to.

Either path means composer._proposition_frame can carry a stale frame
(e.g. one whose .obj was "upset" from several turns back) into
_bind_slot_from_frame on a LATER, unrelated turn -- entering delivered
text without ever touching word_sources, ThoughtContinuity, or the OETS
enrichment path PF3.1's first fix already addressed.

Monkeypatches begin_expression to log: whether it early-returned, whether
build_frame raised, and the frame before/after each turn.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import aurora_braid_wiring as abw  # noqa: E402
from aurora import boot_aurora, process_external_user_turn  # noqa: E402

STATE_DIR = REPO_ROOT / "aurora_state"

TURNS = [
    "What will the stock market do next month?",
    "How is my coworker really feeling about the reorg, deep down?",
    "Hi.",
    "Thanks.",
    "Maybe.",
    "What's your favorite color?",
]

_orig_begin_expression = abw.begin_expression
_TRACE_LOG = []


def _traced_begin_expression(systems):
    perception = systems.get('perception')
    composer = getattr(perception, 'composer', None) if perception else None
    before = getattr(composer, '_proposition_frame', 'NO_COMPOSER') if composer else None
    thought_state = systems.get('_current_thought_state')
    entry = {
        "thought_state_is_none": thought_state is None,
        "thought_state_skipped": getattr(thought_state, 'skipped', None) if thought_state is not None else None,
        "frame_before": repr(before),
        "exception": None,
    }
    try:
        result = _orig_begin_expression(systems)
    except Exception as e:  # noqa: BLE001
        entry["exception"] = f"{type(e).__name__}: {e}"
        _TRACE_LOG.append(entry)
        raise
    after = getattr(composer, '_proposition_frame', 'NO_COMPOSER') if composer else None
    entry["frame_after"] = repr(after)
    entry["frame_changed"] = before is not after
    _TRACE_LOG.append(entry)
    return result


abw.begin_expression = _traced_begin_expression

# Also trace build_frame itself directly -- if begin_expression's own
# try/except silently swallows an exception INSIDE build_frame, this
# catches it independent of whatever begin_expression's outer state shows.
from aurora_internal.aurora_proposition_frame import build_frame as _orig_build_frame  # noqa: E402
import aurora_internal.aurora_proposition_frame as apf  # noqa: E402

_BUILD_FRAME_LOG = []


def _traced_build_frame(systems, state):
    try:
        result = _orig_build_frame(systems, state)
        _BUILD_FRAME_LOG.append({"ok": True, "source": getattr(result, "source", None) if result else None})
        return result
    except Exception as e:  # noqa: BLE001
        _BUILD_FRAME_LOG.append({"ok": False, "exception": f"{type(e).__name__}: {e}"})
        raise


apf.build_frame = _traced_build_frame
abw.build_frame = _traced_build_frame


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf3_1_frame_trace_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        print("[boot] starting (profile=surface)...", flush=True)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print("[boot] done", flush=True)

        for i, text in enumerate(TURNS):
            reply = process_external_user_turn(systems, text, session_id=f"pf3_1_frame_trace_{i}")
            content = None
            if isinstance(reply, dict):
                resp_b = reply.get("resp_B")
                content = getattr(resp_b, "content", None)
            _TRACE_LOG.append({"turn": i, "input": text, "delivered": content, "marker": "TURN_BOUNDARY"})

        import json
        out_path = Path(REPO_ROOT) / "scripts" / "_pf3_1_frame_trace_output.json"
        out_path.write_text(json.dumps(
            {"begin_expression_log": _TRACE_LOG, "build_frame_log": _BUILD_FRAME_LOG}, indent=1))
        print(f"[written] {out_path}", flush=True)
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
