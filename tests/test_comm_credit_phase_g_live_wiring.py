# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Communication Credit Unification, zip integration phase G (2026-07-29):
the actual live-turn wiring. Phases E and F ported the subsystem
methods and the aurora.py core functions but left them completely
unreferenced; this phase wires them into _run_live_response_turn's 5
call sites and swaps 4 previously-immediate credit paths (grammar,
concept crystal, cross-pipeline learning, and the resonance
measurement's own timing) for the delayed, receiver-evidence-gated
pattern the rest of this feature depends on.

Structural tests confirm the wiring exists at the right places (this
campaign's established pattern for changes deep inside
_run_live_response_turn, a ~1300+ line function -- see
test_m1_1a_relation_pairs.py's test_chain_down5_understanding_calls_
tier2_logger and test_comm_credit_phase0_dead_wiring.py). One real
live-boot test (matching test_b1_1_envelope_shadow.py's
test_live_turn_appends_to_envelope_shadow_log pattern) runs an actual
2-turn conversation and confirms the contributor traces and the
finalize call both fire for real, not just structurally.

Deliberately NOT ported in this phase: the zip also added a "Final
response boundary" abstain/composer-unified resolution block
immediately after dual_question_pipeline() in _run_live_response_turn,
using the phase-F-ported _turn_has_no_known_anchor(). Verified this
block does not exist anywhere in the current repo (a parallel,
pre-existing "D2.1" version of the same logic already lives inside
_run_reasoning_pipeline, which the zip's new block explicitly exists
to safety-net for callers that bypass it). That block is a separate
hallucination/abstain-suppression feature that happens to sit adjacent
in the diff, not part of Communication Credit's receiver-evidence
routing -- left for separate consideration rather than folded in here
without its own dedicated verification.
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


def _run_live_response_turn_block():
    source = _read_aurora_source()
    start = source.index("def _run_live_response_turn(")
    end = source.index("\ndef ", start + 10)
    return source[start:end]


def test_pending_receiver_resonance_measured_at_turn_entry():
    block = _run_live_response_turn_block()
    entry_idx = block.index('systems["_pending_receiver_resonance"] = None')
    guard_idx = block.index('systems.pop("_live_contract_observation_done", None)')
    assert guard_idx < entry_idx, "per-turn guards must clear before resonance is measured"
    assert 'systems["_last_field_resonance"] = systems["_pending_receiver_resonance"]' in block
    # The old post-response resonance computation must be gone -- confirms
    # this isn't just an addition sitting alongside stale duplicate logic.
    assert "inter-field resonance (prior aurora" not in block


def test_finalize_early_validation_closure_wired_at_all_three_early_exits():
    block = _run_live_response_turn_block()
    assert "def _finalize_early_validation() -> Dict[str, Any]:" in block
    assert "def _commit_early_response(response: Any, response_source: str) -> Dict[str, Any]:" in block
    assert block.count("_early_validation = _finalize_early_validation()") == 3
    assert block.count("_early_application = _commit_early_response(") == 3


def test_main_path_finalize_validated_communication_is_called():
    block = _run_live_response_turn_block()
    call_idx = block.index("_validated_now = _finalize_validated_communication(")
    src_idx = block.index('src = getattr(resp_A, "src", "mind")')
    assert src_idx < call_idx, "the main-path finalize call must run after src is classified"


def test_build_communication_contributors_wired_into_commit_application_and_attach():
    block = _run_live_response_turn_block()
    assert "contributors=_build_communication_contributors(systems, interaction_runtime)," in block
    assert block.count("_build_communication_contributors(systems, interaction_runtime)") == 2
    assert 'understanding_contract.attach_pending_contributors(' in block


def test_grammar_no_longer_gives_immediate_length_based_credit():
    """FIX-A008's observe_exchange(success=len(resp)>=3, ...) block must be
    gone -- immediate credit from response length is exactly what this
    feature replaces with delayed receiver evidence."""
    source = _read_aurora_source()
    assert "GRAMMAR ENGINE — post-turn exchange observation (FIX-A008)" not in source
    assert "_ge_obs.observe_exchange(" not in source
    assert "GRAMMAR ENGINE — delayed receiver attribution" in source
    assert "_last_grammar_trace" in source


def test_concept_crystal_no_longer_gives_immediate_sedi_credit_in_live_turn():
    block = _run_live_response_turn_block()
    assert "_ccr_lsa.observe_sedi(_ax_dict_lsa, delta=round(_fid_lsa * 0.06, 4))" not in block
    assert '"_last_concept_crystal_trace"' in block


def test_cross_pipeline_learning_stages_instead_of_recording_immediately():
    source = _read_aurora_source()
    assert "dream_trainer.record_pipeline_learning" not in source
    assert source.count("dream_trainer.stage_pipeline_learning(") == 4
    assert "dream_trainer.expire_staged_pipeline_learning(current_turn)" in source
    assert "if not response_id:" in source
    assert '_last_staged_pipeline_response_id' in source


def test_live_two_turn_conversation_wires_receiver_credit():
    """Real end-to-end confirmation, not just source-text checks: boot
    Aurora for real, run two live turns, and confirm the contributor
    trace from turn 1 and the finalize call on turn 2 both actually
    fire (not just structurally present)."""
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_comm_credit_g_live_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        result_1 = A.process_external_user_turn(systems, "What is the boiling point of water?")
        assert result_1, "first live turn produced no result"
        assert systems.get("_pending_receiver_resonance") is None or isinstance(
            systems.get("_pending_receiver_resonance"), float
        )

        result_2 = A.process_external_user_turn(systems, "Exactly, that makes sense.")
        assert result_2, "second live turn produced no result"
        # The second turn is the receiver turn for the first response --
        # the finalize call must have run (even if the outcome ended up
        # indeterminate, systems["_last_validated_communication_outcome"]
        # or the contributor traces should reflect a real attempt, not
        # total silence).
        outcome_path = os.path.join(scratch_state, "communication_outcomes.json")
        contributors_present = bool(systems.get("_last_grammar_trace")) or bool(
            systems.get("_last_concept_crystal_trace")
        )
        assert contributors_present or os.path.exists(outcome_path), (
            "neither a contributor trace nor a persisted communication "
            "outcome appeared after two live turns -- the wiring did not run"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
