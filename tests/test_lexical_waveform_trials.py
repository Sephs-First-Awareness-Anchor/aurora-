# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Bare-minimum checks: lexicon channels derived from crystals, the input's waveform distribution,
repair of mode-default flat signatures, and relation-trial use/outcome sourcing.
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concept_crystal import ConceptCrystalRegistry, _DPSCrystal, repair_flat_signatures  # noqa: E402
from aurora_internal.aurora_lexical_crystals import LexicalCrystals  # noqa: E402
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger  # noqa: E402


def _lexicon_class():
    import aurora_expression_perception as ep
    return next(c for c in vars(ep).values() if isinstance(c, type) and hasattr(c, "find_by_noncomp") and hasattr(c, "associate"))


class _Entry:
    def __init__(self, word, noncomp_id, valence=0.0):
        self.word, self.noncomp_id, self.emotional_valence = word, noncomp_id, valence


def _stub(words):
    return SimpleNamespace(
        entries={w: _Entry(w, nc) for w, nc in words.items()},
        NONCOMP_AXES=("X", "T", "N", "B", "A"),
        NONCOMP_CHARACTERS=("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE"),
        _invalidate_noncomp_index=lambda: None, _ensure_noncomp_index=lambda: None, _noncomp_index={},
    )


def test_lexicon_channels_are_derived_from_the_crystals():
    Lex = _lexicon_class()
    registry = ConceptCrystalRegistry()
    registry.bind({}, {})
    stub = _stub({"warm": "N:POLARITY", "cold": "N:POLARITY", "now": "T:OPERATOR"})
    sink = LexicalCrystals(registry)
    assert sink.attach(stub) == 3
    crystal = registry.query({"X": 0.0, "T": 0.0, "N": 1.0, "B": 0.0, "A": 0.0})
    facets = [f for f in crystal.facets.values() if f.role == "word" and "_wc_POLARITY_" in f.facet_id]
    assert {str(f.content) for f in facets} == {"warm", "cold"}
    for entry in stub.entries.values():                       # prove the answer no longer comes from the entries
        entry.noncomp_id = None
    assert {e.word for e in Lex.find_by_noncomp(stub, "N:POLARITY")} == {"warm", "cold"}
    fresh = LexicalCrystals(registry)                          # a new session derives the same view from crystals alone
    fresh.rebuild_index()
    assert fresh.words("N:POLARITY") == ["cold", "warm"] and fresh.words("T:OPERATOR") == ["now"]
    stub.entries["warm"].noncomp_id = "N:POLARITY"
    Lex.associate(stub, "warm", "N:MAGNITUDE")                 # a word moving channels moves on the crystals
    assert "warm" not in sink.words("N:POLARITY") and "warm" in sink.words("N:MAGNITUDE")


def test_the_input_waveform_is_the_actors_own_distribution_not_a_default():
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=2)
    for i in range(300):
        ledger.observe_event(event_index=i, event_id=f"e{i}", episode_id="ep", actor="external_user" if i % 2 == 0 else "responder",
                             text_length=100 + (i % 7) * 10, elapsed_seconds=5.0)
    ledger.observe_event(event_index=300, event_id="brief", episode_id="ep", actor="external_user", text_length=3, elapsed_seconds=5.0)
    brief = ledger.last_waveform()
    ledger.observe_event(event_index=301, event_id="long", episode_id="ep", actor="responder", text_length=100000, elapsed_seconds=5.0)
    long_ = ledger.last_waveform()
    assert len(brief) == 5 and brief[2] < 0.1 and long_[2] > 0.9
    assert brief != long_ and not all(abs(v - brief[0]) < 1e-9 for v in brief)


def test_flat_mode_default_signatures_are_repaired_and_real_ones_untouched():
    flat = _DPSCrystal(crystal_id="flat", concept="c1", constraint_signature={"X": 0.7, "T": 0.7, "N": 0.7, "B": 0.7, "A": 0.0})
    real = _DPSCrystal(crystal_id="real", concept="c2", constraint_signature={"X": 0.9, "T": 0.2, "N": 0.6, "B": 0.1, "A": 0.3})
    store = {"flat": flat, "real": real}
    assert repair_flat_signatures(store) == 1
    assert flat.constraint_signature is None and real.constraint_signature["X"] == 0.9
    assert any(f.role == "meta:flat_signature" for f in flat.facets.values())       # original kept
    assert repair_flat_signatures(store) == 0                                        # idempotent


def test_relation_trials_get_outcomes_from_the_webs_own_consequences():
    from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb, RelationType
    web = OntologicalWeb()
    comp = SimpleNamespace(component_id="c1", axis_profile={"X": 0.5})
    web._integrate_warp(comp)
    kind = web._open_kinds["c1"]
    web.record_relation_trial_use("c1")
    web._note_trial_reinforcement(SimpleNamespace(relation_type=kind))                # independently observed again: held up
    web._note_trial_reinforcement(SimpleNamespace(relation_type=RelationType.IS_A))   # a seed type is not a trial: no effect
    assert web._relation_trial_usage["c1"] == {"uses": 1, "successes": 1}
    assert abs(web._score_trial(comp) - 0.9) < 1e-9
    web.record_relation_trial_outcome("c1", False)
    assert web._relation_trial_usage["c1"]["failures"] == 1


def test_the_waveform_provider_is_wired_to_the_extractor_and_gated_to_real_inputs():
    from aurora_internal.aurora_live_experience import _wire_waveform_and_lexicon
    ledger = SimpleNamespace(last_waveform=lambda: (0.9, 0.1, 0.2, 0.8, 0.5))
    extractor = SimpleNamespace()
    systems = {"dimensional": SimpleNamespace(concept_extractor=extractor)}
    _wire_waveform_and_lexicon(systems, ledger)
    assert extractor.input_waveform_provider() is None                  # not a conversation input: no stamp
    systems["_historical_witnessing"] = True
    assert extractor.input_waveform_provider() == [0.9, 0.1, 0.2, 0.8, 0.5]
    systems["_historical_witnessing"] = False
    systems["_live_turn_depth"] = 1
    assert extractor.input_waveform_provider() == [0.9, 0.1, 0.2, 0.8, 0.5]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as exc:
                failures += 1; print("FAIL", name, type(exc).__name__, str(exc)[:240])
    sys.exit(1 if failures else 0)
