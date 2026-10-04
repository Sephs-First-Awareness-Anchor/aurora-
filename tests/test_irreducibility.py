# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Representational irreducibility: a deeper or alternative path is only a new discovery if it makes a
distinction no other path already makes.  Paths that divide the observations the same way (an
axis can be removed or substituted without changing the prediction) are one equivalence family:
a single canonical representation that carries the others as shared ancestry.
"""
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger  # noqa: E402


def _stream(n, mode, seed=21):
    """One long episode.  mode "same": T and N are two views of ONE hidden persistent state.
    mode "swap": each is driven by the OTHER's previous value (genuinely different distinctions)."""
    rng = random.Random(seed)
    b, t_prev, n_prev = 0, 0, 0
    for i in range(n):
        if mode == "same":
            if rng.random() > 0.9:
                b = int(rng.random() < 0.5)
            t_now = n_now = b
        else:
            t_now = n_prev if rng.random() < 0.9 else int(rng.random() < 0.5)
            n_now = t_prev if rng.random() < 0.9 else int(rng.random() < 0.5)
        t_prev, n_prev = t_now, n_now
        yield dict(
            event_index=i, event_id=f"e{i}", episode_id="ep0", actor="a" if i % 2 == 0 else "b",
            text_length=int(400 * rng.uniform(0.7, 1.3)) if n_now else int(20 * rng.uniform(0.7, 1.3)),
            elapsed_seconds=120.0 if t_now else 2.0, episode_gap_seconds=None,
        )


def _run(mode, n=9000):
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    for ev in _stream(n, mode):
        ledger.observe_event(**ev)
    return ledger


def test_same_family_judges_by_predictive_distinction_not_by_label():
    same = AuroraResolutionLedger._same_family
    base = [0.2 if i % 2 else 0.8 for i in range(200)]
    assert same(base, list(base))                                         # identical distinctions
    assert same(base, [p + 0.001 for p in base])                          # essentially identical
    assert not same(base, [0.8 if i % 2 else 0.2 for i in range(200)])    # same cells, opposite predictions
    assert not same(base, [0.5] * 200)                                    # one makes a distinction, the other none
    assert not same(base[:30], base[:30])                                 # too little evidence to judge: held apart


def test_paths_that_divide_the_observations_identically_are_one_family_not_several_discoveries():
    ledger = _run("same")
    for subject in ledger.status()["subjects"]:
        everything = [r["path"] for r in ledger.discovered(subject, include_aliases=True)]
        canonical = ledger.discovered(subject)
        into_n = [r for r in canonical if r["path"].endswith(">N")]
        assert len([p for p in everything if p.endswith(">N")]) >= 2, everything      # several paths were significant...
        assert len(into_n) == 1, [r["path"] for r in canonical]                      # ...but they are one representation
        assert into_n[0]["length"] == 2 and into_n[0]["family"], into_n                # the simplest member, carrying the rest
        assert ledger.family_of(subject, into_n[0]["path"]) == into_n[0]["family"]
        aliases = [r for r in ledger.discovered(subject, include_aliases=True) if not r["canonical"]]
        assert all(r["alias_of"].split(">")[-1] == r["path"].split(">")[-1] for r in aliases)   # never across targets


def test_genuinely_different_distinctions_stay_separate_representations():
    ledger = _run("swap")
    for subject in ledger.status()["subjects"]:
        canonical = {r["path"] for r in ledger.discovered(subject)}
        assert {"T>N", "N>T"} <= canonical, canonical                                 # different targets: both stand
        # lag-2 variants driven by the same information are not extra discoveries of N
        assert len([p for p in canonical if p.endswith(">N")]) == 1, canonical


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as exc:
                failures += 1; print("FAIL", name, type(exc).__name__, str(exc)[:300])
    sys.exit(1 if failures else 0)
