# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Representations live inside the crystals: recorded as facets at their path's coordinate,
restored without recomputation, consequence applied to the facet itself, words placed as
`word` facets for composition to find, and no file of the exchange's own.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from concept_crystal import ConceptCrystalRegistry  # noqa: E402
from aurora_internal.aurora_representation_crystals import ROLE_PREFIX, RepresentationCrystals  # noqa: E402
from aurora_internal.aurora_representation_exchange import AuroraRepresentationExchange  # noqa: E402
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger  # noqa: E402
from test_resolution_ledger import _stream  # noqa: E402


def _events(n, mode="pair", seed=11):
    for ev in _stream(n, mode, seed=seed):
        yield dict(ev, actor="external_user" if ev["actor"] == "a" else "responder")


def _tokens(ev):
    return ["the", "big" if ev["text_length"] > 100 else "small"]


def _run(n=9000, registry=None, directory=None, known_word=None):
    registry = registry if registry is not None else ConceptCrystalRegistry()
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    exchange = AuroraRepresentationExchange(ledger, state_dir=directory or tempfile.mkdtemp(), persist=bool(directory))
    store = RepresentationCrystals(registry)
    exchange.attach_crystals(store, known_word=known_word)
    for ev in _events(n):
        ledger.observe_event(**ev)
        exchange.after_event(ev["event_index"], tokens=_tokens(ev))
    return registry, ledger, exchange, store


def _tn_crystal(registry):
    crystal = registry.query({"X": 0.0, "T": 0.5, "N": 0.5, "B": 0.0, "A": 0.0})
    facet = next(f for f in crystal.facets.values() if f.role == "lsa:res:external_user:T>N")
    return crystal, facet


def test_an_earned_representation_is_a_facet_on_the_crystal_at_its_coordinate():
    registry, _, exchange, _ = _run()
    assert exchange.crystallize() > 0
    crystal, facet = _tn_crystal(registry)
    assert facet.role.startswith(ROLE_PREFIX) and len(facet.role) <= 4 + 30
    import json
    record = json.loads(facet.content)
    assert record["path"] == "T>N" and record["status"] == "earned" and record["uni"]["n"] > 1000
    assert record["tab"]["ctx"] and record["z"] >= 3.0
    # Positional shapes (X/B only) are not recorded on crystals.
    assert not any(f.role.startswith("lsa:res:") and set(f.role.split(":")[-1].split(">")) <= {"X", "B"}
                   for c in registry.all_crystals() for f in c.facets.values())


def test_a_fresh_session_restores_from_the_crystals_without_recomputing():
    registry, _, exchange, store = _run()
    exchange.crystallize()
    before = {v["id"]: v for v in exchange.representations()}["REPR:external_user:T>N"]
    ledger2 = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    exchange2 = AuroraRepresentationExchange(ledger2, state_dir=tempfile.mkdtemp(), persist=False)
    assert exchange2.attach_crystals(store) >= 1
    after = {v["id"]: v for v in exchange2.representations()}["REPR:external_user:T>N"]
    assert after["status"] == "earned" and after["expectations_scored"] == before["expectations_scored"]
    assert abs(after["z"] - before["z"]) < 0.01
    assert store.recall(subject="external_user", path="T>N")[0]["id"] == "REPR:external_user:T>N"
    # The adopted expectation table resumes at once: a few live events and it is offered again.
    for i, ev in enumerate(list(_events(3, "pair", seed=5))):
        ledger2.observe_event(**dict(ev, event_index=None, event_id=f"R{i}", episode_id="live", stream="live"))
    subject, _ = ledger2.last_bits("live")
    assert subject == "external_user"
    assert any(e["path"] == "T>N" for e in ledger2.expectations(subject, "live"))


def test_consequence_is_applied_to_the_facet_itself():
    registry, ledger, exchange, _ = _run(n=6000)
    exchange.crystallize()
    _, facet = _tn_crystal(registry)
    first = facet.coherence
    for ev in list(_events(9000, "pair"))[6000:]:
        ledger.observe_event(**ev)
        exchange.after_event(ev["event_index"], tokens=_tokens(ev))
    exchange.crystallize()
    assert first < facet.coherence <= 1.0               # confirmed expectations strengthen the facet


def test_words_tied_to_the_shape_become_word_facets_for_composition_to_find():
    lexicon = {"big", "small", "the"}
    registry, _, exchange, _ = _run(known_word=lambda w: w in lexicon)
    exchange.crystallize()
    crystal, _ = _tn_crystal(registry)
    words = {str(f.content) for f in crystal.facets.values() if f.role == "word"}
    assert "big" in words and "small" not in words and "the" not in words   # high pole only, not filler
    _, _, exchange2, _ = _run(known_word=lambda w: False)                   # a word outside her lexicon is never written
    exchange2.crystallize()
    registry3, _, exchange3, _ = _run(known_word=lambda w: w == "nothing")
    exchange3.crystallize()
    crystal3, _ = _tn_crystal(registry3)
    assert not [f for f in crystal3.facets.values() if f.role == "word"]


def test_records_survive_the_crystals_own_persistence_path():
    registry, _, exchange, _ = _run()
    exchange.crystallize()
    crystal, facet = _tn_crystal(registry)
    restored = type(crystal).from_dict(crystal.to_dict())
    twin = next(f for f in restored.facets.values() if f.role == facet.role)
    assert twin.content == facet.content


def test_the_exchange_keeps_no_file_of_its_own_when_crystals_are_the_record():
    directory = tempfile.mkdtemp()
    _, _, exchange, _ = _run(directory=directory)
    assert exchange.save() is True
    assert not (Path(directory) / "representation_exchange.json").exists()


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
