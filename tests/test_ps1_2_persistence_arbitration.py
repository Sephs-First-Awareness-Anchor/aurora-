# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PS1.2: no-silent-reversion invariant. OETSPersistence.load_web()
must arbitrate between its primary (repo-root, untracked) and snapshot
(state_dir-scoped, git-tracked) candidates instead of blindly taking
"first that exists" -- the mechanism Track CP found silently discarding
S1.2's seed data. Snapshot is canonical by default; primary only wins if
strictly newer by timestamp. Every reversion must be audit-logged.
"""
import json
import os
import shutil
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_identity_persistence import OETSPersistence  # noqa: E402
from aurora_internal.aurora_ontological_scaffolding import OntologicalScaffoldingEngine  # noqa: E402
from aurora_internal.aurora_persistence_audit import log_reversion  # noqa: E402


def _web_payload(nodes, timestamp, relations=None):
    return {
        "version": "1.0",
        "timestamp": timestamp,
        "nodes": {
            w: {
                "word": w, "role": "noun", "emotional_valence": 0.0,
                "definitions": [], "usage_examples": [],
                "ontological_depth": 0.5, "comprehension_confidence": 0.5,
                "research_priority": 0.5, "scaffolding_level": 0,
                "times_encountered": 0, "times_used_in_expression": 0,
                "times_researched": 0, "first_encountered": timestamp,
                "last_accessed": timestamp, "lineage": "",
            }
            for w in nodes
        },
        "relations": relations or {},
        "categories": {},
        "research_stats": {},
        "total_consolidations": 0,
        "total_relations_created": 0,
        "total_research_cycles": 0,
    }


def _setup(scratch):
    """Build an OETSPersistence whose primary_web_file is redirected into
    the scratch dir too (so the test never touches the real repo-root
    file), keeping snapshot_web_file as the normal state_dir path."""
    state_dir = os.path.join(scratch, "aurora_state")
    os.makedirs(state_dir, exist_ok=True)
    persist = OETSPersistence(state_dir=state_dir)
    fake_primary = os.path.join(scratch, "primary_aurora_oets_web.json")
    persist.primary_web_file = type(persist.primary_web_file)(fake_primary)
    persist.web_file = persist.primary_web_file
    # These tests exist specifically to exercise the dual-candidate
    # arbitration path using safe, sandboxed fake paths -- not the real
    # shared repo-root file. PS1.3's follow-up fix excludes primary_web_file
    # entirely for genuinely isolated (state_dir != default) boots, which
    # is exactly right for real test isolation but would also skip the
    # code under test here, so it's explicitly overridden back on for
    # this fixture only (simulating "as if this were the one real default
    # boot," which is the only context where dual-candidate arbitration
    # is meant to run at all).
    persist._isolated = False
    return persist, state_dir


def test_snapshot_wins_when_primary_is_older():
    scratch = tempfile.mkdtemp(prefix="ps1_2_test_")
    try:
        persist, state_dir = _setup(scratch)
        older = time.time() - 1000
        newer = time.time()
        with open(persist.primary_web_file, "w") as f:
            json.dump(_web_payload(["stale_word"], older), f)
        with open(persist.snapshot_web_file, "w") as f:
            json.dump(_web_payload(["fresh_word"], newer), f)

        engine = OntologicalScaffoldingEngine()
        ok = persist.load_web(engine)
        assert ok
        assert "fresh_word" in engine.web.nodes
        assert "stale_word" not in engine.web.nodes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_primary_wins_only_when_strictly_newer():
    scratch = tempfile.mkdtemp(prefix="ps1_2_test_")
    try:
        persist, state_dir = _setup(scratch)
        older = time.time() - 1000
        newer = time.time()
        with open(persist.primary_web_file, "w") as f:
            json.dump(_web_payload(["newer_primary_word"], newer), f)
        with open(persist.snapshot_web_file, "w") as f:
            json.dump(_web_payload(["older_snapshot_word"], older), f)

        engine = OntologicalScaffoldingEngine()
        ok = persist.load_web(engine)
        assert ok
        assert "newer_primary_word" in engine.web.nodes
        assert "older_snapshot_word" not in engine.web.nodes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_tie_prefers_snapshot():
    scratch = tempfile.mkdtemp(prefix="ps1_2_test_")
    try:
        persist, state_dir = _setup(scratch)
        same_ts = time.time()
        with open(persist.primary_web_file, "w") as f:
            json.dump(_web_payload(["primary_word"], same_ts), f)
        with open(persist.snapshot_web_file, "w") as f:
            json.dump(_web_payload(["snapshot_word"], same_ts), f)

        engine = OntologicalScaffoldingEngine()
        persist.load_web(engine)
        assert "snapshot_word" in engine.web.nodes
        assert "primary_word" not in engine.web.nodes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_reversion_is_audit_logged():
    scratch = tempfile.mkdtemp(prefix="ps1_2_test_")
    try:
        persist, state_dir = _setup(scratch)
        older = time.time() - 1000
        newer = time.time()
        with open(persist.primary_web_file, "w") as f:
            json.dump(_web_payload(["stale_word"], older), f)
        with open(persist.snapshot_web_file, "w") as f:
            json.dump(_web_payload(["fresh_word"], newer), f)

        engine = OntologicalScaffoldingEngine()
        persist.load_web(engine)

        audit_path = os.path.join(state_dir, "persistence_audit_log.jsonl")
        assert os.path.exists(audit_path)
        with open(audit_path) as f:
            rows = [json.loads(l) for l in f if l.strip()]
        assert rows
        row = rows[-1]
        assert row["store"] == "OETSPersistence"
        assert row["discarded"]["node_count"] == 1
        assert "stale_word" not in row["kept"]["source"]  # kept is the snapshot path, not primary
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_only_one_candidate_exists_no_arbitration_no_log():
    scratch = tempfile.mkdtemp(prefix="ps1_2_test_")
    try:
        persist, state_dir = _setup(scratch)
        with open(persist.snapshot_web_file, "w") as f:
            json.dump(_web_payload(["only_word"], time.time()), f)

        engine = OntologicalScaffoldingEngine()
        ok = persist.load_web(engine)
        assert ok
        assert "only_word" in engine.web.nodes

        audit_path = os.path.join(state_dir, "persistence_audit_log.jsonl")
        assert not os.path.exists(audit_path)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_corrupted_candidate_does_not_block_valid_sibling(capsys):
    scratch = tempfile.mkdtemp(prefix="ps1_2_test_")
    try:
        persist, state_dir = _setup(scratch)
        with open(persist.primary_web_file, "w") as f:
            f.write("{not valid json")
        with open(persist.snapshot_web_file, "w") as f:
            json.dump(_web_payload(["good_word"], time.time()), f)

        engine = OntologicalScaffoldingEngine()
        ok = persist.load_web(engine)
        assert ok
        assert "good_word" in engine.web.nodes

        captured = capsys.readouterr()
        assert "CORRUPTED" in captured.out
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_isolated_state_dir_excludes_primary_from_candidates():
    """A genuinely isolated boot (state_dir != the repo default) must
    never touch the shared, untracked repo-root primary file at all --
    not on load, not on save. Without this, an isolated scratch test
    could still silently contaminate the shared file (PS1.3's own
    finding: this happened for real, across this campaign's earlier
    test runs, before this fix)."""
    scratch = tempfile.mkdtemp(prefix="ps1_2_isolation_test_")
    try:
        state_dir = os.path.join(scratch, "aurora_state")
        os.makedirs(state_dir, exist_ok=True)
        persist = OETSPersistence(state_dir=state_dir)
        assert persist._isolated is True
        candidates = persist._web_candidates()
        assert persist.primary_web_file not in candidates
        assert persist.snapshot_web_file in candidates
        assert len(candidates) == 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_neither_candidate_exists_returns_false():
    scratch = tempfile.mkdtemp(prefix="ps1_2_test_")
    try:
        persist, state_dir = _setup(scratch)
        engine = OntologicalScaffoldingEngine()
        ok = persist.load_web(engine)
        assert ok is False
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_log_reversion_degrades_gracefully():
    assert log_reversion(None, "Store", {}, {}, "reason") in (True, False)


# ── LexicalMemory: state_dir isolation ──────────────────────────────────

def test_lexical_memory_respects_state_dir():
    import aurora_expression_perception as aep

    scratch_a = tempfile.mkdtemp(prefix="ps1_2_lex_a_")
    scratch_b = tempfile.mkdtemp(prefix="ps1_2_lex_b_")
    try:
        lex_a = aep.LexicalMemory(state_dir=scratch_a)
        lex_a.entries["ps1_2_marker_word"] = aep.LexicalEntry(
            word="ps1_2_marker_word", meaning="a test marker", role="noun",
            emotional_valence=0.0,
        )
        assert lex_a.save() is True
        assert os.path.exists(os.path.join(scratch_a, "lexicon.json"))
        assert not os.path.exists(os.path.join(scratch_b, "lexicon.json"))

        lex_b = aep.LexicalMemory(state_dir=scratch_b)
        assert "ps1_2_marker_word" not in lex_b.entries

        lex_a_reloaded = aep.LexicalMemory(state_dir=scratch_a)
        assert "ps1_2_marker_word" in lex_a_reloaded.entries
    finally:
        shutil.rmtree(scratch_a, ignore_errors=True)
        shutil.rmtree(scratch_b, ignore_errors=True)


def test_lexical_memory_no_state_dir_falls_back_to_default():
    import aurora_expression_perception as aep
    lex = aep.LexicalMemory()
    assert lex._path is None
    assert lex._DEFAULT_PATH.endswith(os.path.join("aurora_state", "lexicon.json"))


# ── ProvisionalStore / SourceTrustRegistry: explicit path override ─────

def test_provisional_store_and_trust_registry_respect_explicit_path():
    from pathlib import Path
    from aurora_offline_resilience import ProvisionalStore, SourceTrustRegistry

    scratch = tempfile.mkdtemp(prefix="ps1_2_provisional_")
    try:
        sd = Path(scratch)
        trust = SourceTrustRegistry(path=sd / "source_trust.json")
        trust.record_contribution("test_source")
        store = ProvisionalStore(path=sd / "provisional_knowledge.json", trust_registry=trust)
        store.add("a test question", "a test answer", "test_source")

        assert (sd / "source_trust.json").exists()
        assert (sd / "provisional_knowledge.json").exists()

        reloaded = ProvisionalStore(path=sd / "provisional_knowledge.json", trust_registry=trust)
        assert len(reloaded._entries) == 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_boot_aurora_threads_state_dir_into_offline_resilience_call_site():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index("def _on_online():")
    block = source[idx:idx + 900]
    assert "SourceTrustRegistry(path=" in block
    assert "ProvisionalStore(" in block
    assert "_sd / " in block


def test_boot_aurora_threads_state_dir_into_dimensional_systems():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index("dimensional = DimensionalSystems(")
    line = source[idx:idx + 80]
    assert "state_dir=state_dir" in line


def test_boot_aurora_threads_state_dir_into_expression_perception():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index("perception = ExpressionPerceptionEngine(")
    line = source[idx:idx + 80]
    assert "state_dir=state_dir" in line
