# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression coverage for MTSL Phase 0 (Plumbing & Continuity Repairs,
2026-07-13) -- the foundational, no-semantic-behavior repairs the
Multiplex Topological Semantics Layer directive requires before any
topology observation work begins.

P0.1 -- persist circulation/deprecation state files past the blanket
        aurora_state/ .gitignore entry (same silent-discard class as
        classroom_corpus_rotation.json, concept_images_fetched.json, etc.)
P0.2 -- persist the CERS deprecation ledger across process restarts;
        MIN_FRAMES_FOR_RECOMMENDATION=150 was unreachable with an
        in-RAM-only ledger that reset to empty every boot.
P0.3 -- repair pytest collection: a bare `pytest` invocation from repo
        root crashed with an INTERNALERROR (confirmed independently
        before fixing) because several ad-hoc debug scripts under
        tests/ execute real work (including full boot_aurora() calls
        and unguarded sys.exit()) at module import time.
P0.4 -- TCL provenance hygiene: the 2026-07-12 audit numbers in
        aurora_toroidal_circulation.py's docstring are historical
        record, not present truth; aurora_flow_audit.py prints a
        generated, self-dating header instead of relying on stale
        docstring counts.
"""
import ast
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── P0.1 ────────────────────────────────────────────────────────────────────

def test_workflow_force_adds_all_four_mtsl_state_files():
    path = os.path.join(_ROOT, ".github", "workflows", "aurora-autonomous-run.yml")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for fname in (
        "toroidal_circulation_state.json",
        "topology_tracker_state.json",
        "semantic_variant_index.json",
        "cers_deprecation_ledger.json",
    ):
        assert re.search(rf"git add -f aurora_state/{re.escape(fname)}", content), (
            f"workflow must force-add aurora_state/{fname} -- it is a "
            "brand-new file under the blanket aurora_state/ gitignore"
        )


# ── P0.2 ────────────────────────────────────────────────────────────────────

from aurora_internal.dual_strata.cers_deprecation import (
    SubsystemDeprecationLedger,
    MIN_FRAMES_FOR_RECOMMENDATION,
    PERSISTED_WINDOW_CAP,
)


def test_deprecation_ledger_without_state_dir_behaves_as_before(tmp_path):
    """Backward compatibility: no state_dir means pure in-memory, exactly
    the pre-fix behavior -- construction must not require a state_dir."""
    ledger = SubsystemDeprecationLedger()
    ledger.record({"agrees_with_legacy": True, "conflicts": []})
    rec = ledger.evaluate()
    assert rec.frames_evaluated == 1


def test_deprecation_ledger_reaches_threshold_across_a_restart(tmp_path):
    """The exact real-world case: 150 frames is unreachable if the ledger
    resets every process boot. Persisting across a simulated restart must
    let the threshold actually be reached."""
    first = SubsystemDeprecationLedger(state_dir=str(tmp_path))
    for _ in range(100):
        first.record({"agrees_with_legacy": True, "conflicts": []})
    assert first.evaluate().status == "insufficient_data"

    second = SubsystemDeprecationLedger(state_dir=str(tmp_path))
    assert len(second._entries) == 100, "a fresh instance must rehydrate prior entries from disk"
    for _ in range(60):
        second.record({"agrees_with_legacy": True, "conflicts": []})
    rec = second.evaluate()
    assert rec.frames_evaluated >= MIN_FRAMES_FOR_RECOMMENDATION
    assert rec.status != "insufficient_data"


def test_deprecation_ledger_persists_latest_trial_state(tmp_path):
    first = SubsystemDeprecationLedger(state_dir=str(tmp_path))
    first.record({
        "agrees_with_legacy": True,
        "conflicts": [],
        "actively_trialing_potential": ["some_channel"],
    })
    second = SubsystemDeprecationLedger(state_dir=str(tmp_path))
    assert second._latest_actively_trialing == ["some_channel"]


def test_deprecation_ledger_persisted_window_is_capped(tmp_path):
    ledger = SubsystemDeprecationLedger(state_dir=str(tmp_path))
    for _ in range(PERSISTED_WINDOW_CAP + 50):
        ledger.record({"agrees_with_legacy": True, "conflicts": []})
    reloaded = SubsystemDeprecationLedger(state_dir=str(tmp_path))
    assert len(reloaded._entries) <= PERSISTED_WINDOW_CAP


def test_deprecation_ledger_corrupt_file_does_not_block_construction(tmp_path):
    path = tmp_path / "cers_deprecation_ledger.json"
    path.write_text("not valid json {{{")
    ledger = SubsystemDeprecationLedger(state_dir=str(tmp_path))
    assert len(ledger._entries) == 0


def test_cers_bridge_wires_state_dir_into_deprecation_ledger():
    from aurora_internal.dual_strata.cers_bridge import CERSBridge
    bridge = CERSBridge()
    assert bridge.deprecation_ledger._path is not None
    assert str(bridge.state_dir) in bridge.deprecation_ledger._path


# ── P0.3 ────────────────────────────────────────────────────────────────────

def test_repo_wide_pytest_collection_succeeds():
    """The actual gate: a bare `pytest --collect-only` from repo root must
    exit 0 and collect real tests, not crash with an INTERNALERROR."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=_ROOT, capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, (
        f"repo-wide pytest collection must succeed.\nstdout:\n{result.stdout[-3000:]}\n"
        f"stderr:\n{result.stderr[-2000:]}"
    )
    assert "INTERNALERROR" not in result.stdout
    assert "tests collected" in result.stdout


def test_ad_hoc_debug_scripts_guard_their_executable_body():
    """Every ad-hoc script under tests/ (and the root-level
    test_constraint_reasoner.py) that has no top-level def/class must gate
    its executable body behind `if __name__ == "__main__":` -- otherwise
    pytest's import-time collection runs it for real."""
    candidates = [
        os.path.join(_ROOT, "test_constraint_reasoner.py"),
        os.path.join(_ROOT, "tests", "test_alignment.py"),
        os.path.join(_ROOT, "tests", "test_emitter_crash.py"),
        os.path.join(_ROOT, "tests", "test_oets.py"),
        os.path.join(_ROOT, "tests", "test_oets_conf.py"),
        os.path.join(_ROOT, "tests", "test_up.py"),
        os.path.join(_ROOT, "tests", "_engine_integration_test.py"),
        os.path.join(_ROOT, "tests", "_pipeline_test.py"),
    ]
    for path in candidates:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        has_main_guard = any(
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            for node in tree.body
        )
        assert has_main_guard, f"{path} must gate its executable body behind if __name__ == '__main__':"


# ── P0.4 ──────────────────────────────────────────────────────────────────

def test_tcl_docstring_labels_audit_numbers_as_historical():
    with open(os.path.join(_ROOT, "aurora_toroidal_circulation.py"), "r", encoding="utf-8") as f:
        content = f.read()
    assert "HISTORICAL SNAPSHOT" in content
    assert "aurora_flow_audit.py" in content


def test_flow_audit_prints_a_generated_header():
    result = subprocess.run(
        [sys.executable, "aurora_flow_audit.py"],
        cwd=_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0
    assert "run at:" in result.stdout
    assert "genealogy files:" in result.stdout
    assert "manifolds found:" in result.stdout
    assert "surface log lines:" in result.stdout
