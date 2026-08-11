# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 1:
aurora_daemon.py::_run_code_mutation_cycle() previously accepted a
mutation purely on compile + import-reload + QAO surface-integrity
success, never calling CodeEvolutionChamber's measured-relief
acceptance formula -- compilation/import success is viability evidence,
not fitness evidence (Build 646 Requirement 6.1). This tests the repair
directly against the real daemon function (not a reimplementation of
its logic), isolated to a synthetic repo via a monkeypatched
aurora_daemon._BASE_DIR so no real repository file is touched, with
CodeAutoEvolver.apply_operator() stubbed only to control WHAT content
change is proposed (which specific content-generating operator produces
a change is Build 646/an unrelated autoevolver concern) while
CodeEvolutionChamber.evaluate_mutation() runs for real and unmocked --
it alone decides acceptance.
"""
import os
import shutil
import sys
import tempfile
import textwrap
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_daemon
from aurora_internal.aurora_code_autoevolver import CodeAutoEvolver


def _complex_source() -> str:
    src = "def hot_surface_fn(x):\n"
    for i in range(30):
        src += f"    if x == {i}:\n        x = x + {i}\n"
    src += "    return x\n"
    return src


class _StubGenealogy:
    """Only needs to satisfy the MIN_LINKS gate at the top of the cycle."""
    link_count = 100
    links: dict = {}


def _make_synthetic_repo() -> str:
    scratch = tempfile.mkdtemp(prefix="aurora_daemon_evidence_")
    target_dir = os.path.join(scratch, "aurora_internal")
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, "aurora_evolved_surfaces.py")
    with open(target, "w", encoding="utf-8") as f:
        f.write(_complex_source())
    return scratch


def _run_cycle_with_stubbed_operator(scratch: str, new_content: str):
    """
    Runs the real _run_code_mutation_cycle against the synthetic repo.
    apply_operator is stubbed only to write new_content to the daemon's
    fixed target file and report it as changed -- exactly what a real
    operator's return contract looks like -- so the ONLY thing under
    test is the daemon's post-viability evaluation gate.
    """
    target = os.path.join(scratch, "aurora_internal", "aurora_evolved_surfaces.py")

    def _stub_apply_operator(self, operator_key, target_files):
        with open(target, "r", encoding="utf-8") as f:
            original = f.read()
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {
            "operator_key": operator_key,
            "changed_files": [target],
            "change_count": 1,
            "backups": {target: original},
            "details": [{"file": target, "change": "test stub"}],
            "rejected": [],
            "rejected_count": 0,
        }

    def _stub_plan_operator(self, operator_key, target_files):
        return [target]

    systems = {"genealogy": _StubGenealogy(), "function_lineage": None}
    with patch.object(aurora_daemon, "_BASE_DIR", __import__("pathlib").Path(scratch)), \
         patch.object(aurora_daemon, "_select_discovery_driven_operator", return_value="architectural_reflection"), \
         patch.object(aurora_daemon, "_qao_check_surface_integrity", return_value=True), \
         patch.object(aurora_daemon, "_run_assimilation_cycle", return_value=None), \
         patch.object(CodeAutoEvolver, "apply_operator", _stub_apply_operator), \
         patch.object(CodeAutoEvolver, "plan_operator", _stub_plan_operator):
        aurora_daemon._run_code_mutation_cycle(systems)
    return systems, target


class TestNoMeasuredReliefIsRejectedAndRolledBack:
    def test_compiles_and_imports_but_no_relief_rolls_back(self):
        scratch = _make_synthetic_repo()
        try:
            target = os.path.join(scratch, "aurora_internal", "aurora_evolved_surfaces.py")
            with open(target, "r", encoding="utf-8") as f:
                original = f.read()

            # Cosmetic-only change: compiles fine, imports fine, QAO stubbed
            # to pass -- but produces essentially no measured pressure
            # relief over the real 30-branch function.
            cosmetic = original + "\n# a harmless trailing comment\n"
            systems, target = _run_cycle_with_stubbed_operator(scratch, cosmetic)

            with open(target, "r", encoding="utf-8") as f:
                after = f.read()
            assert after == original, "no-relief mutation must be rolled back to original content"

            chamber = systems.get("code_chamber")
            assert chamber is not None
            assert chamber.rejected_count >= 1
            assert any(
                rec.get("accepted") is False
                for rec in chamber._mutation_lineage.values()
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


class TestGenuineReliefSurvives:
    def test_real_complexity_reduction_is_accepted_and_kept(self):
        scratch = _make_synthetic_repo()
        try:
            simplified = "def hot_surface_fn(x):\n    return x\n"
            systems, target = _run_cycle_with_stubbed_operator(scratch, simplified)

            with open(target, "r", encoding="utf-8") as f:
                after = f.read()
            assert after == simplified, "genuinely relieving mutation must survive, not be rolled back"

            chamber = systems.get("code_chamber")
            assert chamber is not None
            assert chamber.accepted_count >= 1
            assert any(
                rec.get("accepted") is True
                for rec in chamber._mutation_lineage.values()
            )
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
