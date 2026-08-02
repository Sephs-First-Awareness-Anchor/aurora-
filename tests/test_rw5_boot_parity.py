# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
RW5 -- Boot-spine unification (closes F9), wiring audit 2026-07-20
(`wiring_audit.md`).

F9 found `PrimitiveExtractor` mounted only in `aurora_runtime.py`'s
`boot_stack` (the offline/batch CLI stack behind `AuroraRuntime`),
never in `aurora.py`'s `boot_aurora` (the live daemon spine) -- "every
organ mounted in exactly one spine is silently absent from the other
... a standing generator of 'I wired this already' incidents."

RW5's two deliverables:
1. Mount `PrimitiveExtractor` in `boot_aurora` too (the one case the
   audit byte-verified as needing both spines).
2. A `BOOT_PARITY` table (`aurora_internal/aurora_boot_parity.py`)
   checked by a test that diffs the two spines' mounted-key sets, so a
   *future* one-spine-only mount gets caught here instead of
   rediscovered by a future audit.

This test does not assert every organ is mounted in both spines --
`boot_stack` is a smaller, purpose-built stack, not a live-serving
path, and most of `boot_aurora`'s ~80 organs have no reason to exist
there. It asserts the tracked divergence stays *exactly* the
documented, reviewed set: any newly silent one-spine-only mount (not
already in `KNOWN_BOOT_STACK_ONLY` or `RECONCILED`) fails the test.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_boot_parity import (  # noqa: E402
    KNOWN_BOOT_STACK_ONLY,
    RECONCILED,
    boot_parity_report,
    extract_boot_aurora_organs,
    extract_boot_stack_organs,
)


def test_primitive_extractor_mounted_in_both_spines():
    aurora_organs = extract_boot_aurora_organs()
    stack_organs = extract_boot_stack_organs()
    assert "primitive_extractor" in aurora_organs, (
        "RW5's confirmed case regressed: PrimitiveExtractor must be "
        "mounted in boot_aurora (the live daemon spine)"
    )
    assert "primitive_extractor" in stack_organs, (
        "PrimitiveExtractor unexpectedly removed from boot_stack"
    )


def test_boot_aurora_mounts_primitive_extractor_from_real_genealogy_object():
    """Structural check: the mount must reuse the same genealogy logger
    boot_aurora already built (not construct a second one), matching
    boot_stack's own pattern (systems.primitive_extractor =
    PrimitiveExtractor(systems.genealogy))."""
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    start = source.index("\ndef boot_aurora(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    assert "systems['primitive_extractor'] = PrimitiveExtractor(_genealogy)" in body


def test_no_unexpected_one_spine_only_organs():
    """The core parity check: every organ mounted in exactly one spine
    must already be accounted for (reconciled, or a documented known
    gap awaiting its own architecture call). A newly diverged mount
    that isn't in either bucket fails here -- this is the standing
    regression guard RW5 exists to add."""
    report = boot_parity_report()
    assert report["unexpected_stack_only"] == [], (
        f"New boot_stack-only organ(s) not tracked in "
        f"KNOWN_BOOT_STACK_ONLY or RECONCILED: {report['unexpected_stack_only']}"
    )


def test_known_stack_only_set_is_still_accurate():
    """If a KNOWN_BOOT_STACK_ONLY organ gets mounted into boot_aurora
    too, it should graduate to RECONCILED (documentation hygiene, not
    a behavioral bug) -- this catches a stale table entry."""
    report = boot_parity_report()
    stale_entries = set(KNOWN_BOOT_STACK_ONLY) - set(report["stack_only"])
    assert not stale_entries, (
        f"KNOWN_BOOT_STACK_ONLY entries no longer stack-only (now in "
        f"both spines -- move to RECONCILED): {stale_entries}"
    )


def test_reconciled_set_is_actually_present_in_both_spines():
    report = boot_parity_report()
    assert set(RECONCILED) == set(report["reconciled_present_in_both"]), (
        "RECONCILED claims an organ is mounted in both spines, but the "
        "current source no longer shows it in both"
    )


def test_boot_parity_report_shape():
    report = boot_parity_report()
    for key in (
        "aurora_organs", "stack_organs", "stack_only",
        "aurora_only", "unexpected_stack_only", "reconciled_present_in_both",
    ):
        assert key in report
    assert len(report["aurora_organs"]) > len(report["stack_organs"]), (
        "boot_aurora is the live production spine and should carry "
        "substantially more organs than boot_stack's smaller batch stack"
    )


def test_real_boot_aurora_mounts_a_working_primitive_extractor():
    """Real end-to-end confirmation, not just source inspection: boot
    Aurora for real and confirm systems['primitive_extractor'] is an
    actual PrimitiveExtractor wired to the real genealogy logger."""
    import shutil
    import tempfile

    import aurora as A
    from aurora_internal.aurora_primitive_extractor import PrimitiveExtractor

    scratch = tempfile.mkdtemp(prefix="aurora_rw5_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        extractor = systems.get("primitive_extractor")
        assert isinstance(extractor, PrimitiveExtractor), (
            "boot_aurora did not mount a real PrimitiveExtractor "
            f"(got {type(extractor)!r})"
        )
        assert extractor._g is systems.get("genealogy"), (
            "PrimitiveExtractor must share boot_aurora's own genealogy "
            "logger, not a separate instance"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
