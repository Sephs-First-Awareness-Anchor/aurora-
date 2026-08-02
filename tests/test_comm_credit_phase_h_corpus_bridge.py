# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Communication Credit Unification, zip integration phase H (2026-07-29):
the corpus-ingestion bridge. Corpus ingestion (run_corpus_ingestion) is
Aurora's other live-turn-shaped surface -- it calls generate_reply() /
process_external_user_turn() and witness()es truth continuations just
like a real conversation, so it needs the same delayed receiver-credit
treatment phase G gave the interactive live turn:

* witness() now gates every observation through the phase-F-ported
  LearningQualityGate before it is fed to Aurora as knowledge, and
  records the observation (and any missing-context gap) to a bounded
  ledger regardless of eligibility.
* _persist_corpus_observations() atomically persists that ledger plus
  the quality gate's rolling status once, at the end of ingestion.
* _record_corpus_response_pressure() previously computed a real
  pressure signal but had no return statement at all (fell through to
  an implicit None on every call) -- now returns the computed dict so
  callers can use it as receiver evidence.
* pass_responder()/pass_reverse() feed that returned pressure into the
  new _resolve_corpus_response_learning(), which treats the corpus
  truth continuation as receiver evidence for whatever pipeline
  learning candidates staged (phase G/E) under the response's
  response_id -- the same stage/resolve pattern as the interactive
  live turn, not a separate immediate-credit path.

Structural tests confirm the wiring exists at the right places
(matching this campaign's established pattern -- see
test_comm_credit_phase_g_live_wiring.py). One real functional test
runs an actual observer-pass ingestion against a tiny synthetic OpenAI
export against a freshly booted Aurora and confirms the observation
ledger and persisted corpus_observations.json both appear for real.
"""
import json
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _read_aurora_source():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        return f.read()


def _run_corpus_ingestion_block():
    source = _read_aurora_source()
    start = source.index("def run_corpus_ingestion(")
    end = source.index("\ndef ", start + 10)
    return source[start:end]


def test_persist_corpus_observations_called_once_at_end_of_ingestion():
    block = _run_corpus_ingestion_block()
    assert "def _persist_corpus_observations() -> None:" in block
    assert block.count("_persist_corpus_observations()") == 2  # def + the one call site
    call_idx = block.rindex("_persist_corpus_observations()")
    save_idx = block.rindex("_full_save(systems, verbose=verbose)")
    assert call_idx < save_idx, "observations must persist before the final save"


def test_witness_gates_on_quality_before_feeding_knowledge():
    block = _run_corpus_ingestion_block()
    gate_idx = block.index("quality = _corpus_quality_gate.observe(content, role=role)")
    record_idx = block.index("_record_corpus_observation(role, content, quality, source)")
    guard_idx = block.index("if not quality.get('eligible_for_learning'):")
    feed_idx = block.index("stream_type=StreamType.KNOWLEDGE_FEED")
    assert gate_idx < record_idx < guard_idx < feed_idx, (
        "quality must be assessed and the observation recorded before the "
        "eligibility gate decides whether it becomes a knowledge feed"
    )


def test_record_corpus_response_pressure_returns_dict_not_none():
    import aurora as A

    result = A._record_corpus_response_pressure(
        {},
        prompt_text="What is the boiling point of water?",
        aurora_text="Water boils at 100 degrees Celsius at sea level.",
        truth_text="It boils at 100 C at standard atmospheric pressure.",
        phase="test_phase",
    )
    assert isinstance(result, dict)
    for key in (
        "kind", "signal", "threshold", "truth_alignment",
        "prompt_grounding", "length_fit", "counter_pressure", "phase",
    ):
        assert key in result, f"missing key: {key}"
    assert result["phase"] == "test_phase"
    assert 0.0 <= result["signal"] <= 1.0


def test_record_corpus_response_pressure_returns_empty_dict_without_response():
    import aurora as A

    result = A._record_corpus_response_pressure(
        {}, prompt_text="hello", aurora_text="", truth_text="hi", phase="test_phase",
    )
    assert result == {}


def test_resolve_corpus_response_learning_wired_into_both_passes():
    source = _read_aurora_source()
    assert source.count("_resolve_corpus_response_learning(_pressure, ") == 2
    assert "_resolve_corpus_response_learning(_pressure, 'responder')" in source
    assert "_resolve_corpus_response_learning(_pressure, 'reverse')" in source
    assert "dt.resolve_pipeline_learning(" in source


def _write_tiny_openai_export(path):
    mapping = {
        "root": {"id": "root", "parent": None, "children": ["n1"], "message": None},
        "n1": {
            "id": "n1", "parent": "root", "children": ["n2"],
            "message": {
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [
                    "What is the boiling point of water at sea level?"
                ]},
            },
        },
        "n2": {
            "id": "n2", "parent": "n1", "children": [],
            "message": {
                "author": {"role": "assistant"},
                "content": {"content_type": "text", "parts": [
                    "Water boils at one hundred degrees Celsius at sea level pressure."
                ]},
            },
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump([{"mapping": mapping}], f)


def test_observer_pass_persists_corpus_observations_for_real():
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_comm_credit_h_corpus_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        corpus_path = os.path.join(scratch, "corpus.json")
        _write_tiny_openai_export(corpus_path)

        A.run_corpus_ingestion(
            systems,
            corpus_path,
            train_every=999999,
            save_every=999999,
            passes="observer",
            verbose=False,
        )

        assert systems.get("_corpus_observation_ledger"), (
            "observer pass produced no observation ledger entries"
        )
        outcome_path = os.path.join(scratch_state, "corpus_observations.json")
        assert os.path.exists(outcome_path), (
            "_persist_corpus_observations did not write corpus_observations.json"
        )
        with open(outcome_path, "r", encoding="utf-8") as f:
            persisted = json.load(f)
        assert persisted["observations"], "persisted ledger is empty"
        assert "quality_status" in persisted
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
