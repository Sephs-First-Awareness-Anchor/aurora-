# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression tests for two gaps found by checking Aurora after her first
scheduled runs post-merge of the fitness-collapse/concept-imager/classroom-
staleness fixes (2026-07-12): concept_images_ingested was still 0 and the
classroom curriculum was still repeating the same content, even though the
code fixes were live.

1. aurora_concept_imager.fetch_concept_image() imports `requests`, but
   requirements-core.txt (what the scheduled CI workflow actually installs)
   never declared it -- every fetch silently no-op'd
   ("[IMAGER] requests not available") before ever reaching the
   already-fixed ingest_concept_image() path, and every SEMANTIC+ candidate
   got permanently marked "failed".

2. aurora_state/classroom_corpus_rotation.json (the per-dimension rotation
   cursor persisted by aurora_classroom.py's select_curriculum()) is a
   brand-new file under the repo's blanket `aurora_state/` .gitignore entry.
   The scheduled workflow's commit step only stages already-tracked
   modified files (`git diff --name-only`) plus a short explicit list of
   force-added brand-new files (classroom_log.jsonl,
   concept_images_fetched.json, vision_seeds/, cers_snapshot.json, etc.) --
   the rotation file was missing from that list, so it was silently
   recreated from scratch and discarded every run, and the curriculum kept
   re-picking the same front-of-pool example.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_requirements_core_declares_requests():
    """fetch_concept_image() needs `requests` to reach Wikipedia -- the
    scheduled CI runner only installs requirements-core.txt, so it must be
    declared there (not just in the broader current_requirements.txt)."""
    path = os.path.join(_ROOT, "requirements-core.txt")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = [
        line.strip() for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    requests_lines = [line for line in lines if line.split("==")[0].strip() == "requests"]
    assert requests_lines, (
        "requirements-core.txt must declare `requests` -- "
        "aurora_concept_imager.fetch_concept_image() imports it directly, "
        "and its absence silently no-ops every concept-image fetch on the "
        "scheduled CI runner"
    )
    assert "==" in requests_lines[0], "requests should be version-pinned like every other entry in this file"


def test_scheduled_workflow_force_adds_classroom_rotation_state():
    """classroom_corpus_rotation.json falls under the blanket aurora_state/
    .gitignore entry (same as classroom_log.jsonl, concept_images_fetched.json,
    cers_snapshot.json, etc.) -- the workflow's commit step must force-add it
    or the rotation cursor never survives between scheduled runs."""
    path = os.path.join(_ROOT, ".github", "workflows", "aurora-autonomous-run.yml")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert re.search(
        r"git add -f aurora_state/classroom_corpus_rotation\.json",
        content,
    ), (
        "aurora-autonomous-run.yml's commit step must force-add "
        "aurora_state/classroom_corpus_rotation.json -- it is a brand-new "
        "file under the blanket aurora_state/ gitignore, invisible to "
        "`git diff --name-only`, so without an explicit force-add the "
        "curriculum rotation cursor is silently discarded every run"
    )


def test_blanket_aurora_state_gitignore_still_present():
    """Sanity check the premise: aurora_state/ really is blanket-ignored,
    which is why force-adding brand-new files under it is necessary at all
    (not a workaround for some other, already-fixed problem)."""
    path = os.path.join(_ROOT, ".gitignore")
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.read().splitlines()]
    assert "aurora_state/" in lines
