# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Asserts on aurora_build714_resolution_canaries.py's five live canaries
(directive Section 31). See that module for the narrative/executable form."""
import tempfile
from pathlib import Path

from aurora_build714_resolution_canaries import (
    canary_1_stable_coarse_history,
    canary_2_divergent_history,
    canary_3_refinement_pays_off,
    canary_4_refinement_does_not_pay_off,
    canary_5_habitat_discovery,
)


def _root(tmp_path_factory, name):
    return tmp_path_factory.mktemp(name)


def test_canary_1_same_input_same_adequate_history(tmp_path_factory):
    result = canary_1_stable_coarse_history(_root(tmp_path_factory, "c1"))
    assert result["passed"], result


def test_canary_2_same_input_divergent_history(tmp_path_factory):
    result = canary_2_divergent_history(_root(tmp_path_factory, "c2"))
    assert result["passed"], result


def test_canary_3_refinement_pays_off(tmp_path_factory):
    result = canary_3_refinement_pays_off(_root(tmp_path_factory, "c3"))
    assert result["passed"], result


def test_canary_4_refinement_does_not_pay_off(tmp_path_factory):
    result = canary_4_refinement_does_not_pay_off(_root(tmp_path_factory, "c4"))
    assert result["passed"], result


def test_canary_5_habitat_discovery(tmp_path_factory):
    result = canary_5_habitat_discovery(_root(tmp_path_factory, "c5"))
    assert result["passed"], result
