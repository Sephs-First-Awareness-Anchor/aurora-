"""Real-boot proof that IVMLattice.tick() -- and PR #210's constitutive
ConstraintField behavior riding on top of it -- actually fires during a
real conversational turn, not just against fixtures.

Context: PR #210 gave ConstraintField constitutive behavior and wired it
into IVMLattice.tick(), but tick() itself was never called anywhere in
Aurora's live runtime -- only by aurora_ivm.py's own self-tests and the
offline corpus_runner.py. This follow-up adds one call site in
_run_live_response_turn's Subsurface-safe zone (after on_surface_ready,
so it can never delay or alter what Aurora says), on the same
systems['lattice'] instance gw._synthesize() -> consciousness.process()
-> lattice.admit() already populates with real conversational evidence
every turn. This test proves the wiring fires end-to-end on a real turn,
mirroring the real-boot methodology tests/test_governance_liveness.py
uses (boot, run one real turn, assert on post-turn state) rather than
inferring liveness from source/comments alone.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def test_real_turn_advances_lattice_tick_and_populates_constraint_field():
    scratch = tempfile.mkdtemp(prefix="aurora_lattice_driveshaft_")
    try:
        shutil.copytree(
            os.path.join(REPO_ROOT, "aurora_state"),
            os.path.join(scratch, "aurora_state"),
        )
        import aurora as A

        systems = A.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)
        systems["_session_turn_buffer"] = []

        lattice = systems.get("lattice")
        assert lattice is not None, "boot_aurora() did not register systems['lattice']"
        ticks_before = lattice.total_ticks

        result = A.process_external_user_turn(
            systems, "Hi Aurora, how are you doing today?",
            source_label="lattice_driveshaft_test",
        )
        assert result.get("resp_B") is not None, "process_external_user_turn returned no resp_B"

        assert lattice.total_ticks > ticks_before, (
            "IVMLattice.tick() did not run during a real live turn -- "
            "the driveshaft is disconnected again"
        )
        assert lattice._constraint_field is not None
        assert lattice._constraint_field.occupied_count() >= 1, (
            "the constraint field did not get populated from real conversational "
            "evidence -- nodes should already be admitted onto this lattice via "
            "gw._synthesize() -> consciousness.process() -> lattice.admit() before "
            "tick() ever runs"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
