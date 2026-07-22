#!/usr/bin/env python3
"""One-off: trace exactly what calls process_external_user_turn a second
time within a single outer call, now that W1's linguistic ProcessContext
is in place. Instruments _run_simulation_live_response_bridge directly
so it's visible even if the outer call-count wrapper doesn't catch it."""
import shutil, sys, tempfile, traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import aurora as A  # noqa: E402

scratch = tempfile.mkdtemp(prefix="aurora_w1_reentrancy_")
shutil.copytree(str(REPO_ROOT / "aurora_state"), str(Path(scratch) / "aurora_state"))
systems = A.boot_aurora(state_dir=str(Path(scratch) / "aurora_state"))

orig_bridge = A._run_simulation_live_response_bridge
bridge_calls = [0]

def _traced_bridge(sys_arg, *, selected, context, mode, runtime_context=None):
    bridge_calls[0] += 1
    depth = int(sys_arg.get("_live_turn_depth", 0) or 0)
    print(f"[BRIDGE CALL #{bridge_calls[0]}] _live_turn_depth={depth} "
          f"same_systems_obj={sys_arg is systems} prompt={context.get('prompt', '')!r}", flush=True)
    return orig_bridge(sys_arg, selected=selected, context=context, mode=mode, runtime_context=runtime_context)

A._run_simulation_live_response_bridge = _traced_bridge

orig_peut = A.process_external_user_turn
depth_track = [0]

def _traced(sys_arg, user_text, **kwargs):
    depth_track[0] += 1
    this_depth = depth_track[0]
    if this_depth > 1:
        print(f"\n=== RECURSIVE process_external_user_turn CALL (depth={this_depth}) "
              f"for text={user_text!r} ===", flush=True)
        traceback.print_stack()
    try:
        return orig_peut(sys_arg, user_text, **kwargs)
    finally:
        depth_track[0] -= 1

A.process_external_user_turn = _traced

TURNS = [
    "Hi Aurora, how are you today?",
    "What's your name?",
    "Good morning!",
    "What is a guitar chord?",
    "Tell me about photosynthesis.",
    "Can you help me understand recursion?",
    "What do you think about music?",
    "How does memory work?",
    "Do you dream?",
    "What's the weather like?",
    "Can you explain gravity?",
    "What is your favorite color?",
    "Tell me a story.",
    "How do plants grow?",
    "What is consciousness?",
    "Do you like poetry?",
    "What is the speed of light?",
    "How do you learn new things?",
    "What makes you curious?",
    "Goodnight Aurora.",
]

try:
    for i, t in enumerate(TURNS):
        depth_track[0] = 0
        print(f"\n--- turn {i}: {t!r} ---", flush=True)
        A.process_external_user_turn(systems, t)
finally:
    A.process_external_user_turn = orig_peut
    A._run_simulation_live_response_bridge = orig_bridge
    shutil.rmtree(scratch, ignore_errors=True)
