# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Discovery research lives on the crystals as hypotheses: no file of the ledger's own, resumed
through the REAL dimensional crystal persistence, never counted as semantic grounding, never
faded by decay, pole words on pole crystals, and replayed events never recounted.
"""
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker  # noqa: E402
from aurora_internal.aurora_representation_crystals import HypothesisCrystals, RepresentationCrystals  # noqa: E402
from aurora_internal.aurora_representation_exchange import AuroraRepresentationExchange  # noqa: E402
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger  # noqa: E402
from concept_crystal import ConceptCrystalRegistry  # noqa: E402
from test_resolution_ledger import _stream  # noqa: E402


def _events(n, seed=11):
    for ev in _stream(n, "pair", seed=seed):
        yield dict(ev, actor="external_user" if ev["actor"] == "a" else "responder")


def _tokens(ev):
    return ["the", "big" if ev["text_length"] > 100 else "small"]


def _store():
    cps = CrystalProcessingSystem(EvolutionTracker())
    registry = ConceptCrystalRegistry()
    registry.bind(cps.crystals, cps.concept_index)
    return cps, registry


def _pipeline(registry, directory=None, known_word=None):
    ledger = AuroraResolutionLedger(state_dir=directory or tempfile.mkdtemp(), persist=bool(directory), max_path=3)
    ledger.attach_crystals(HypothesisCrystals(registry))
    exchange = AuroraRepresentationExchange(ledger, state_dir=directory or tempfile.mkdtemp(), persist=bool(directory))
    exchange.attach_crystals(RepresentationCrystals(registry), known_word=known_word)
    return ledger, exchange


def _feed(ledger, exchange, events):
    for ev in events:
        ledger.observe_event(**ev)
        exchange.after_event(ev["event_index"], tokens=_tokens(ev))


def _paths(ledger):
    return {r["path"] for s in ledger.status()["subjects"] for r in ledger.discovered(s)}


def test_research_state_lives_on_crystals_and_resumes_through_the_real_crystal_persistence():
    cps, registry = _store()
    directory = tempfile.mkdtemp()
    ledger, exchange = _pipeline(registry, directory)
    events = list(_events(9000))
    _feed(ledger, exchange, events[:6000])
    assert ledger.save(force=True) is True and exchange.save() is True
    assert not (Path(directory) / "resolution_ledger.json").exists()                 # no log of its own
    assert not (Path(directory) / "representation_exchange.json").exists()
    roles = {f.role for c in registry.all_crystals() for f in c.facets.values()}
    assert "hyp:cal:ledger" in roles and "hyp:res:external_user:T>N" in roles and "lsa:res:external_user:T>N" in roles

    path = str(Path(tempfile.mkdtemp()) / "dps_crystals.json")
    assert cps.save_crystals(path)                                                   # the real persistence path
    cps2 = CrystalProcessingSystem(EvolutionTracker())
    assert cps2.load_crystals(path) > 0
    registry2 = ConceptCrystalRegistry()
    registry2.bind(cps2.crystals, cps2.concept_index)
    ledger2 = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    assert ledger2.attach_crystals(HypothesisCrystals(registry2)) > 20               # hypotheses restored, nothing recomputed
    exchange2 = AuroraRepresentationExchange(ledger2, state_dir=tempfile.mkdtemp(), persist=False)
    assert exchange2.attach_crystals(RepresentationCrystals(registry2)) >= 1
    assert ledger2.status()["observations"] == ledger.status()["observations"]

    _feed(ledger, exchange, events[6000:])                                           # both continue the same stream
    _feed(ledger2, exchange2, events[6000:])
    assert "T>N" in _paths(ledger2) and _paths(ledger2) == _paths(ledger)
    assert any(v["path"] == "T>N" and v["status"] == "earned" for v in exchange2.representations())


def test_hypotheses_never_count_as_semantic_grounding():
    _, registry = _store()
    store = HypothesisCrystals(registry)
    ax = RepresentationCrystals.coordinate("T>N")
    assert store.write({"v": 1}, [{"subject": "external_user", "path": "T>N", "st": {"n": 5.0}, "tab": {}}]) == 2
    assert registry.query(ax) is not None and registry.query_grounded(ax) is None


def test_facets_are_touched_so_decay_never_fades_live_research():
    _, registry = _store()
    store = HypothesisCrystals(registry)
    rec = {"subject": "external_user", "path": "T>N", "st": {}, "tab": {}}
    store.write({"v": 1}, [rec])
    crystal = registry.query(RepresentationCrystals.coordinate("T>N"))
    facet = next(f for f in crystal.facets.values() if f.role == "hyp:res:external_user:T>N")
    facet.last_accessed = time.time() - 7 * 24 * 3600                                # untouched for a week
    store.write({"v": 1}, [rec])
    before = facet.confidence
    facet.decay(rate=0.01)
    assert abs(facet.confidence - before) < 1e-3


def test_pole_words_land_on_pole_crystals_and_both_poles_resonate():
    _, registry = _store()
    ledger, exchange = _pipeline(registry, known_word=lambda w: w in {"big", "small", "the"})
    _feed(ledger, exchange, list(_events(9000)))
    exchange.crystallize()
    high = registry.query({"X": 0.0, "T": 0.5, "N": 0.5, "B": 0.0, "A": 0.0})
    low = registry.query({"X": 0.0, "T": 0.5, "N": -0.5, "B": 0.0, "A": 0.0})
    words = lambda c: {str(f.content) for f in c.facets.values() if f.role == "word"}
    assert high.crystal_id != low.crystal_id
    assert "big" in words(high) and "small" not in words(high)
    assert "small" in words(low) and "big" not in words(low)
    for crystal in (high, low):                                                       # the renderer's rule: abs share >= 0.3
        sig = crystal.constraint_signature
        assert abs(sig["N"]) / sum(abs(v) for v in sig.values()) >= 0.3


def test_a_restored_exchange_never_recounts_replayed_events():
    _, registry = _store()
    ledger, exchange = _pipeline(registry)
    events = list(_events(4000))
    _feed(ledger, exchange, events)
    exchange.crystallize()
    ledger2 = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    ledger2.attach_crystals(HypothesisCrystals(registry))
    exchange2 = AuroraRepresentationExchange(ledger2, state_dir=tempfile.mkdtemp(), persist=False)
    exchange2.attach_crystals(RepresentationCrystals(registry))
    assert exchange2.after_event(3000)["processed"] is False                          # already counted before the save
    assert exchange2.after_event(10**6)["processed"] is True


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:
                failures += 1
                print("FAIL", name, type(exc).__name__, str(exc)[:260])
    sys.exit(1 if failures else 0)
