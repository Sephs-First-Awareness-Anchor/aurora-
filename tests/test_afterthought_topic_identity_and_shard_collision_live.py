"""Live-boundary regression for Build 725's afterthought repair.

The old Build 616 test expected afterthought simulations to derive semantic
subjects from prompt wording. That contract is intentionally obsolete. The
live requirement now is that deeper afterthought cognition is non-blocking and
retains the initiating turn identity.
"""
import time
from types import SimpleNamespace

import aurora


def test_afterthought_dispatch_returns_before_deeper_episode_finishes():
    class SlowSimulation:
        def run_episode(self, **_kwargs):
            time.sleep(0.20)
            return SimpleNamespace(episode_id="live-afterthought")

    systems = {
        "aurora": SimpleNamespace(gateway=SimpleNamespace(simulation=SlowSimulation())),
        "ExistenceMode": SimpleNamespace(BOUNDED="bounded"),
        "_current_turn_id": "live-turn-1",
    }
    started = time.perf_counter()
    thread = aurora._dispatch_afterthought_subsurface(
        systems, "What should I make of this?", session_id="live", turn_tick=1,
    )
    assert time.perf_counter() - started < 0.12
    assert systems["_last_afterthought_dispatch"]["cause"]["turn_id"] == "live-turn-1"
    thread.join(timeout=1.0)
    assert systems["_last_afterthought_result"]["cause"]["turn_id"] == "live-turn-1"
    assert systems["_last_afterthought_result"]["episode_id"] == "live-afterthought"
