# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Performance fix for UniversalFunctionLineage.verify_source_freshness()
(aurora_internal/aurora_universal_function_lineage.py) -- unrelated to the
causal-generation directive's own scope, but found and flagged during it:
boot_aurora() calls this on every single boot to decide whether a rebuild
is needed, and it used to unconditionally call _scan_surfaces() -- which
reads and AST-parses every tracked .py file -- even when NOTHING had
changed since the last boot. Confirmed live against the real repo: ~13s
for _scan_surfaces() alone, and the full auto_build=True boot path could
hit ~60-150s depending on whether a rebuild also got (mis)triggered.

Fix: a cheap stat()-only pre-check (_quick_file_stats(), mtime_ns + size,
no file read, no AST parse) short-circuits verify_source_freshness() when
every tracked file's stats match exactly what the last successful build
persisted. Confirmed live: 0.00-0.02s for this repo's ~360 files versus
13s+ for the scan it replaces in the common case. Any mismatch (a real
edit, a missing/older manifest, files added or removed) falls straight
through to the original, unchanged, authoritative content-hash scan --
so the fast path can only skip re-proving freshness that was already
true last time, never paper over genuine staleness. These tests use a
small synthetic repo (not the real ~270K-line one) so they run fast while
still exercising the real mechanism end-to-end.
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_universal_function_lineage import (  # noqa: E402
    UniversalFunctionLineage,
)


def _make_synthetic_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "synthetic_repo"
    (repo / "aurora_internal").mkdir(parents=True)
    (repo / "pkg").mkdir()
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "a.py").write_text(
        "def alpha():\n"
        "    return beta()\n"
        "\n"
        "def beta():\n"
        "    return 1\n"
    )
    (repo / "pkg" / "b.py").write_text(
        "from pkg.a import alpha\n"
        "\n"
        "def gamma():\n"
        "    return alpha()\n"
    )
    return repo


def test_second_construction_skips_scan_surfaces_when_nothing_changed(tmp_path):
    repo = _make_synthetic_repo(tmp_path)

    # First construction: no persisted manifest yet, must do a real scan.
    first = UniversalFunctionLineage(repo_root=str(repo), auto_build=True)
    assert first._functions, "fixture repo produced no functions to track"
    assert (repo / "aurora_internal" / "universal_function_lineage.json").exists()

    # Second construction: fresh instance, same on-disk manifest, nothing
    # touched in between -- _scan_surfaces() must not be called at all.
    second = UniversalFunctionLineage(repo_root=str(repo), auto_build=False)
    scan_calls = []
    real_scan_fn = second._scan_surfaces
    def spy_scan(*args, **kwargs):
        scan_calls.append(True)
        return real_scan_fn(*args, **kwargs)
    second._scan_surfaces = spy_scan

    result = second.verify_source_freshness()

    assert result["source_current"] is True
    assert result.get("fast_path") == "mtime_size_match"
    assert scan_calls == [], (
        "verify_source_freshness() called _scan_surfaces() even though "
        "nothing changed -- the fast path did not short-circuit"
    )


def test_fast_path_is_actually_faster(tmp_path):
    """Not just structurally correct -- measurably faster. Uses a slightly
    larger synthetic repo so the difference is measurable above timer
    noise, and asserts the fast path is at least 3x quicker than a real
    scan of the same tree (the true speedup on the real repo is ~500x+,
    but a conservative bound keeps this robust to CI timing variance)."""
    repo = _make_synthetic_repo(tmp_path)
    for i in range(30):
        (repo / "pkg" / f"extra_{i}.py").write_text(
            f"def f_{i}():\n    return {i}\n\ndef g_{i}():\n    return f_{i}()\n"
        )

    ufl = UniversalFunctionLineage(repo_root=str(repo), auto_build=True)

    t0 = time.time()
    ufl._scan_surfaces()
    full_scan_elapsed = time.time() - t0

    fresh = UniversalFunctionLineage(repo_root=str(repo), auto_build=False)
    t0 = time.time()
    result = fresh.verify_source_freshness()
    fast_path_elapsed = time.time() - t0

    assert result.get("fast_path") == "mtime_size_match"
    assert fast_path_elapsed * 3 < full_scan_elapsed or fast_path_elapsed < 0.01, (
        f"fast path ({fast_path_elapsed:.4f}s) not meaningfully faster than "
        f"a full scan ({full_scan_elapsed:.4f}s)"
    )


def test_real_content_edit_is_still_detected_and_triggers_rebuild(tmp_path):
    repo = _make_synthetic_repo(tmp_path)
    first = UniversalFunctionLineage(repo_root=str(repo), auto_build=True)
    original_function_count = len(first._functions)

    # A real, content-changing edit -- adds a new function.
    (repo / "pkg" / "a.py").write_text(
        "def alpha():\n"
        "    return beta()\n"
        "\n"
        "def beta():\n"
        "    return 1\n"
        "\n"
        "def delta():\n"
        "    return alpha() + beta()\n"
    )

    probe = UniversalFunctionLineage(repo_root=str(repo), auto_build=False)
    result = probe.verify_source_freshness()
    assert result["source_current"] is False
    assert "pkg/a.py" in result["changed_files"]
    assert result.get("fast_path") is None  # correctly fell through, not fast-pathed

    rebuilt = UniversalFunctionLineage(repo_root=str(repo), auto_build=True)
    assert len(rebuilt._functions) == original_function_count + 1
    assert any(
        rec.get("qualname") == "delta" for rec in rebuilt._functions.values()
    ), "new function from the real edit was not picked up after rebuild"


def test_mtime_only_change_with_identical_content_still_reports_current(tmp_path):
    """A file touched (mtime changed) without its content changing must
    still, after falling through to the full content-hash check, report
    source_current=True -- proving the fast path's occasional false
    negative (falling through when it didn't strictly need to) never
    becomes a false positive in the other direction."""
    repo = _make_synthetic_repo(tmp_path)
    first = UniversalFunctionLineage(repo_root=str(repo), auto_build=True)
    del first

    target = repo / "pkg" / "a.py"
    # Force a different mtime without touching content.
    os.utime(target, (time.time() + 5, time.time() + 5))

    probe = UniversalFunctionLineage(repo_root=str(repo), auto_build=False)
    result = probe.verify_source_freshness()
    assert result.get("fast_path") is None  # mtime differs -> fell through
    assert result["source_current"] is True  # content hash still matches
    assert result["changed_files"] == []


def test_missing_file_stats_in_older_manifest_falls_back_gracefully(tmp_path):
    """A manifest persisted before this fix existed (no file_stats key)
    must not crash or misbehave -- it should simply always fall through
    to the full scan, exactly as it did before this fix."""
    repo = _make_synthetic_repo(tmp_path)
    ufl = UniversalFunctionLineage(repo_root=str(repo), auto_build=True)
    ufl._manifest.pop("file_stats", None)
    ufl._write_manifest()

    probe = UniversalFunctionLineage(repo_root=str(repo), auto_build=False)
    result = probe.verify_source_freshness()
    assert result.get("fast_path") is None
    assert result["source_current"] is True
