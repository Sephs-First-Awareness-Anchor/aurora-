#!/usr/bin/env python3
"""
PF3.1 (fourth investigation step): "planning" still dominates delivered
text for turns whose frame_source is None (confirmed: no proposition-frame
involvement at all for these records) and whose word_sources shows
candidate_source="find_by_noncomp" with a high, still-climbing usage_count
-- meaning "planning" is winning on RAW RELEVANCE, which requires it to be
a DIRECT anchor via composer._context_keywords (build_relevance_anchor_
set's direct_from_recent branch), since it never appears in the literal
turn text. This traces every set_context() call across a live multi-turn
run: when it fires, from where, and with what keywords -- to settle
whether _context_keywords is being refreshed every turn or going stale
the same way _proposition_frame was.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import aurora_expression_perception as aep  # noqa: E402
from aurora import boot_aurora, process_external_user_turn  # noqa: E402

STATE_DIR = REPO_ROOT / "aurora_state"

TURNS = [
    "Will this medication definitely work for me?",
    "What's your favorite color?",
    "Hi.",
    "Thanks.",
]

_orig_set_context = aep.SentenceComposer.set_context
_CALL_LOG = []


def _traced_set_context(self, keywords):
    stack = traceback.extract_stack()
    caller = stack[-2]
    _CALL_LOG.append({
        "keywords_in": list(keywords),
        "caller": f"{Path(caller.filename).name}:{caller.lineno} in {caller.name}",
    })
    result = _orig_set_context(self, keywords)
    _CALL_LOG[-1]["context_keywords_after"] = list(self._context_keywords)
    return result


aep.SentenceComposer.set_context = _traced_set_context


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf3_1_ctx_trace_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        print("[boot] starting (profile=surface)...", flush=True)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print("[boot] done", flush=True)

        composer = systems["perception"].composer
        for i, text in enumerate(TURNS):
            _CALL_LOG.append({"marker": "TURN_START", "turn": i, "input": text,
                               "context_keywords_before": list(composer._context_keywords)})
            process_external_user_turn(systems, text, session_id=f"pf3_1_ctx_trace_{i}")
            _CALL_LOG.append({"marker": "TURN_END", "turn": i,
                               "context_keywords_after": list(composer._context_keywords)})

        import json
        out_path = Path(REPO_ROOT) / "scripts" / "_pf3_1_ctx_trace_output.json"
        out_path.write_text(json.dumps(_CALL_LOG, indent=1))
        print(f"[written] {out_path}", flush=True)
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
