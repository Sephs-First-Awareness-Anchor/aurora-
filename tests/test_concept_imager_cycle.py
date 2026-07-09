# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Coverage for run_concept_image_cycle()'s candidate-selection logic -- the
real-image grounding route now wired into scripts/aurora_ci_segment.py as
the sensory substitute for a live camera/mic in headless CI (see
requirements-core.txt's opencv-python-headless addition). Network calls and
cv2 aren't exercised here (no hardware/network dependency in this test);
this locks in that the function degrades safely and only selects genuinely
eligible candidates.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_concept_imager import run_concept_image_cycle


class _FakeNode:
    def __init__(self, scaffolding_level, ontological_depth=0.0):
        self.scaffolding_level = scaffolding_level
        self.ontological_depth = ontological_depth


class _FakeWeb:
    def __init__(self, nodes):
        self.nodes = nodes


class _FakeOets:
    def __init__(self, nodes):
        self.web = _FakeWeb(nodes)


def test_no_oets_web_returns_zero():
    class _NoWeb:
        pass

    assert run_concept_image_cycle(_NoWeb(), None, None, "/tmp") == 0


def test_no_semantic_level_candidates_returns_zero(tmp_path):
    oets = _FakeOets({
        "apple": _FakeNode(scaffolding_level=0),
        "run": _FakeNode(scaffolding_level=1),
    })
    assert run_concept_image_cycle(oets, None, None, tmp_path) == 0


def test_already_grounded_candidates_are_skipped(tmp_path, monkeypatch):
    import aurora_concept_imager as imager

    tracker_path = tmp_path / "concept_images_fetched.json"
    tracker_path.write_text('{"fetched": ["ocean"], "failed": [], "grounded": ["ocean"]}')

    oets = _FakeOets({"ocean": _FakeNode(scaffolding_level=2, ontological_depth=0.8)})

    calls = []
    monkeypatch.setattr(imager, "fetch_concept_image", lambda word, state_dir: calls.append(word) or None)

    result = run_concept_image_cycle(oets, None, None, tmp_path)

    assert result == 0
    assert calls == [], "an already-grounded concept must not be re-fetched"


def test_eligible_candidate_is_attempted(tmp_path, monkeypatch):
    import aurora_concept_imager as imager

    oets = _FakeOets({"ocean": _FakeNode(scaffolding_level=2, ontological_depth=0.8)})

    calls = []
    monkeypatch.setattr(imager, "fetch_concept_image", lambda word, state_dir: calls.append(word) or None)

    result = run_concept_image_cycle(oets, None, None, tmp_path, max_per_run=6)

    assert calls == ["ocean"]
    assert result == 0  # fetch returned None (no real network here) -> nothing ingested
