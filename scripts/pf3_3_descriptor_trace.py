#!/usr/bin/env python3
"""
PF3.3 diagnostic: the live full-profile battery showed descriptor
repetition share ("clear"+"real" fraction) essentially unchanged
(9.22% -> 9.64%) after the neighborhood filter, even with co-occurrence
relations excluded. Direct inspection of a handful of real frame.subject/
obj pairs against the committed OETS graph (aurora_state/aurora_oets_
web.json) shows most everyday conversational nouns ("medication",
"coworker", "favorite") have ZERO relations at all -- meaning the
neighborhood is just {subject, obj} themselves, which almost never
intersects a descriptor (adjective) candidate pool, so the filter
falls through to the unfiltered pool (correctly fail-quiet) on most
turns. This traces _select_constraint_word's descriptor branch directly
across real live turns to confirm: how often does the neighborhood
filter actually have any candidates to work with?

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import aurora_expression_perception as aep  # noqa: E402
from aurora import boot_aurora, process_external_user_turn  # noqa: E402

STATE_DIR = REPO_ROOT / "aurora_state"

TURNS = [
    "What will the stock market do next month?",
    "How is my coworker really feeling about the reorg, deep down?",
    "He's a bit nervous around new people.",
    "What's your favorite color?",
    "I told my friend I was fine, but I've been crying all week.",
    "The meeting requires careful planning.",
]

_orig = aep.SentenceComposer._descriptor_neighborhood
_LOG = []


def _traced(self, frame):
    neighborhood = _orig(self, frame)
    entry = {
        "frame_subject": getattr(frame, "subject", None) if frame else None,
        "frame_obj": getattr(frame, "obj", None) if frame else None,
        "neighborhood_size": len(neighborhood),
        "neighborhood_sample": sorted(neighborhood)[:10],
    }
    if self._has_oets and frame is not None:
        get_all = getattr(self._oets.web, "get_all_relations_for", None)
        if callable(get_all):
            for term in (getattr(frame, "subject", ""), getattr(frame, "obj", "")):
                if not term:
                    continue
                term = str(term).strip().lower()
                try:
                    rels = get_all(term) or []
                except Exception:
                    rels = []
                for rel in rels:
                    other = rel.target_word if rel.source_word == term else rel.source_word
                    if str(other).lower() in ("clear", "real"):
                        entry.setdefault("clear_real_rel_sources", []).append(
                            (term, other, rel.source_of_knowledge))
    _LOG.append(entry)
    return neighborhood


aep.SentenceComposer._descriptor_neighborhood = _traced


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf3_3_trace_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        print("[boot] starting (profile=surface)...", flush=True)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print("[boot] done", flush=True)

        for i, text in enumerate(TURNS):
            reply = process_external_user_turn(systems, text, session_id=f"pf3_3_trace_{i}")
            content = None
            if isinstance(reply, dict):
                resp_b = reply.get("resp_B")
                content = getattr(resp_b, "content", None)
            print(f"\n=== turn {i}: {text!r} -> {content!r}")

        print("\n\n=== _descriptor_neighborhood call log ===")
        for entry in _LOG:
            print(entry)
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
