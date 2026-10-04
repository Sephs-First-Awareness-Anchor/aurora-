# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The renderer's crystal selection: whole-distribution match, polarity veto, strongest facets first."""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora_expression_perception import _crystal_waveform_match, _crystal_word_facets  # noqa: E402

OPEN = {"X": 0.0, "T": 0.5, "N": 0.0, "B": 0.5, "A": 0.0}
BRIEF = {"X": 0.0, "T": 0.0, "N": -0.5, "B": 0.0, "A": 0.0}


def test_without_a_live_waveform_the_original_axis_share_rule_is_unchanged():
    assert abs(_crystal_waveform_match(OPEN, "T", None) - 0.5) < 1e-9
    assert _crystal_waveform_match(OPEN, "N", None) == 0.0


def test_the_whole_distribution_counts_not_only_the_dominant_axis():
    live = {"X": 0.0, "T": 0.9, "N": 0.0, "B": 0.9, "A": 0.0}
    assert _crystal_waveform_match(OPEN, "T", live) > 0.99                     # same waveform
    assert _crystal_waveform_match(OPEN, "N", {"N": 1.0}) == 0.0                # a different one


def test_signed_live_activation_vetoes_the_opposite_pole_but_unsigned_does_not():
    assert _crystal_waveform_match(BRIEF, "N", {"N": 1.0}) > 0.99               # unsigned: no polarity information
    assert _crystal_waveform_match(BRIEF, "N", {"N": 1.0, "T": -0.1}) == 0.0    # signed and opposite: no resonance
    assert _crystal_waveform_match(BRIEF, "N", {"N": -1.0, "T": 0.1}) > 0.99    # signed and matching


def test_word_facets_come_strongest_first_and_faded_relics_are_skipped():
    def facet(content, confidence, coherence, state="FacetState.ACTIVE", role="word"):
        return SimpleNamespace(role=role, content=content, confidence=confidence, coherence=coherence, state=state)
    crystal = SimpleNamespace(facets={
        "a": facet("weak", 0.3, 0.3), "b": facet("strong", 0.9, 0.9), "c": facet("faded", 0.95, 0.95, "FacetState.RELIC"),
        "d": facet("not-a-word", 0.99, 0.99, role="lsa:res:x"),
    })
    assert [str(f.content) for f in _crystal_word_facets(crystal)] == ["strong", "weak"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as exc:
                failures += 1; print("FAIL", name, type(exc).__name__, str(exc)[:200])
    sys.exit(1 if failures else 0)
