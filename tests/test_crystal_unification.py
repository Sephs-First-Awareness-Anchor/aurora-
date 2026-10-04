# Authors: Sunni (Sir) Morningstar & Cael Devo
"""One crystal store: the concept registry and the dimensional system share the same crystals."""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concept_crystal import ConceptCrystalRegistry, _DPSCrystal, unify_crystal_store  # noqa: E402

AX_FOREIGN = {"X": 0.0, "T": 0.5, "N": 0.5, "B": 0.0, "A": 0.0}
AX_NEW = {"X": 0.9, "T": 0.1, "N": 0.1, "B": 0.9, "A": 0.1}


def _foreign(cid="dps_word_crystal"):
    return _DPSCrystal(crystal_id=cid, concept="word:greet", constraint_signature=dict(AX_FOREIGN))


def test_registry_and_dimensional_system_share_one_dict_and_one_crystal_per_coordinate():
    reg = ConceptCrystalRegistry()
    own = reg.observe_lsa({"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}, "pre_bind_path")
    store, index = {}, {}
    foreign = _foreign()
    store[foreign.crystal_id] = foreign
    report = reg.bind(store, index)
    assert report == {"merged": 1, "store": 2}
    assert reg._nodes is store and own.crystal_id in store and index[own.concept] == own.crystal_id
    # An observation at the coordinate of a crystal the DIMENSIONAL system made lands on that crystal.
    hit = reg.observe_lsa(dict(AX_FOREIGN), "res:external_user:T>N")
    assert hit.crystal_id == foreign.crystal_id
    assert any(f.role == "lsa:res:external_user:T>N" for f in foreign.facets.values())
    # A new coordinate creates its crystal IN the shared store and the concept index.
    fresh = reg.observe_lsa(dict(AX_NEW), "res:responder:A>A")
    assert store[fresh.crystal_id] is fresh and index[fresh.concept] == fresh.crystal_id
    assert reg.bind(store, index) == {"merged": 0, "store": len(store)}     # idempotent


def test_bound_registry_never_culls_and_never_writes_its_own_file():
    reg = ConceptCrystalRegistry()
    store = {}
    reg.bind(store, {})
    reg.MAX_NODES = 2                                   # would cull aggressively if it still could
    for i in range(12):
        reg.observe_lsa({"X": i / 11.0, "T": (i * 3 % 11) / 11.0, "N": 0.5, "B": 0.2, "A": 0.8}, f"p{i}")
    assert len(store) >= 5 and len(reg._nodes) == len(store)
    directory = tempfile.mkdtemp()
    reg.save(directory)
    assert not (Path(directory) / "concept_crystals.json.gz").exists()


def test_index_follows_crystals_the_dimensional_system_adds_later():
    reg = ConceptCrystalRegistry()
    store = {}
    reg.bind(store, {})
    late = _foreign("added_later_by_dps")
    store[late.crystal_id] = late                       # the dimensional system forms a crystal after binding
    assert reg.observe_lsa(dict(AX_FOREIGN), "p").crystal_id == "added_later_by_dps"
    del store["added_later_by_dps"]                     # ...and a crystal it removes cannot leave a dangling index
    assert reg.observe_lsa(dict(AX_FOREIGN), "p").crystal_id != "added_later_by_dps"


def test_unify_crystal_store_binds_the_systems_registry_to_the_dps_crystals_once():
    reg = ConceptCrystalRegistry()
    dps = SimpleNamespace(crystals={}, concept_index={})
    systems = {"_concept_crystal_registry": reg, "dimensional": SimpleNamespace(dps=dps)}
    assert unify_crystal_store(systems) == {"merged": 0, "store": 0, "flat_repaired": 0}
    assert reg._nodes is dps.crystals
    assert unify_crystal_store(systems) == {}                              # already one store
    assert unify_crystal_store({}) == {} and unify_crystal_store({"dimensional": None}) == {}


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:
                failures += 1
                print("FAIL", name, type(exc).__name__, str(exc)[:240])
    sys.exit(1 if failures else 0)
