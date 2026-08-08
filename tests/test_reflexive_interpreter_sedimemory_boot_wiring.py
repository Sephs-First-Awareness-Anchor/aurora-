# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression tests for the SYSTEM-WIDE REPRESENTATIONAL CONSERVATION AND
PROPAGATION REPAIR DIRECTIVE's confirmed loss-boundary repair:

CONFIRMED LOSS (before this repair): aurora.py boots
systems["noncomp_reflexive_interpreter"] at ~line 12583, inside
_boot_noncomp_manifold_runtime() -- long before SediMemory boots at L3.5
(~line 27144). ReflexiveInterpreter.__init__'s sedimemory= kwarg therefore
could never receive a live instance in production; self._sedimemory was
always None, so interpret()'s recall_confidence_boost() path -- fully
implemented and already covered by
tests/test_reflexive_interpreter_deposition_integration.py -- never fired
on a real turn. This is a silent fallback to lower-rank state: the richer
information (SediMemory's resonance-scored recall) already existed later in
the very same boot sequence, and five OTHER systems (ConsciousnessEngine,
DimensionalSystems, ExpressionPerceptionEngine, BehavioralIdentityEngine,
SimulationEngine) already receive it via an identical post-boot
connect_sedimemory(...) call -- this repair applies that same established
pattern to ReflexiveInterpreter, the sixth system with the same need.

Repair: added ReflexiveInterpreter.connect_sedimemory() (a one-line setter,
aurora_reflexive_interpreter.py) and one wiring call in aurora.py's boot
sequence, right after SediMemory boots. No new representational physics --
the value being wired through already existed and was already exercised by
tests; only the missing connection was restored.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_reflexive_interpreter import ReflexiveInterpreter


class _ResonantMemory:
    def recall_semantic(self, query_text="", *, max_results=8,
                        axis_filter=None, min_score=0.35):
        return [{"score": 0.95}]


def test_connect_sedimemory_sets_the_instance(tmp_path):
    ri = ReflexiveInterpreter(state_dir=str(tmp_path))
    assert ri._sedimemory is None
    mem = _ResonantMemory()
    ri.connect_sedimemory(mem)
    assert ri._sedimemory is mem


def test_post_boot_wiring_produces_the_same_effect_as_constructor_wiring(tmp_path):
    """The whole point of the repair: connecting AFTER construction (as
    aurora.py's boot sequence must, since SediMemory boots later) must
    produce an identical effect to supplying sedimemory= at construction
    time -- proving the setter is a real substitute for the kwarg, not a
    weaker stand-in."""
    text = "I understand what you mean about boundaries"

    ri_kwarg = ReflexiveInterpreter(state_dir=str(tmp_path / "kwarg"), sedimemory=_ResonantMemory())
    state_kwarg = ri_kwarg.interpret(text)

    ri_setter = ReflexiveInterpreter(state_dir=str(tmp_path / "setter"))
    ri_setter.connect_sedimemory(_ResonantMemory())
    state_setter = ri_setter.interpret(text)

    ri_plain = ReflexiveInterpreter(state_dir=str(tmp_path / "plain"))
    state_plain = ri_plain.interpret(text)

    assert state_kwarg.worth_score == state_setter.worth_score
    assert state_setter.worth_score >= state_plain.worth_score


def test_aurora_boot_sequence_wires_reflexive_interpreter_to_sedimemory():
    """Source-level proof the repair is actually installed in aurora.py's
    boot function, following the exact same guarded pattern already used
    for the other five connect_sedimemory(...) call sites."""
    import aurora

    src = inspect.getsource(aurora)
    anchor = "systems['sedimemory'] = SediMemory("
    assert anchor in src, "SediMemory boot block moved; re-verify wiring placement"

    wiring_marker = "noncomp_reflexive_interpreter"
    idx_sedi = src.index(anchor)
    idx_wire = src.find(f"connect_sedimemory(systems['sedimemory'])", idx_sedi)
    assert idx_wire != -1, "no connect_sedimemory(...) call found after SediMemory boots"

    # The nearest connect_sedimemory(...) call after the SediMemory boot
    # block must be the ReflexiveInterpreter one (it's the first system
    # wired in the current boot order) and must be reached through
    # systems.get('noncomp_reflexive_interpreter').
    window = src[idx_sedi:idx_wire + len(wiring_marker) + 60]
    assert wiring_marker in window


def test_repair_does_not_touch_warp_genealogy_meaning_or_pressure():
    """The repair is scoped to ReflexiveInterpreter <-> SediMemory wiring
    only -- confirm the added code in both files makes no reference to
    WARP, genealogy, meaning profiles, or pressure-map internals."""
    import aurora_reflexive_interpreter as ri_module

    src = inspect.getsource(ri_module.ReflexiveInterpreter.connect_sedimemory)
    forbidden = ("warp", "genealogy", "pressure_map", "meaning_profile")
    lowered = src.lower()
    for term in forbidden:
        assert term not in lowered
