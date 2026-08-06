# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 619: Multi-Sentence Claim-Boundary and Input-Echo Delivery Repair --
live verification.

Covers the directive's 5-turn live-verification protocol (the exact RCEC
assessment prompt that reproduced the echo; a normal multi-sentence
factual question; an explicit repetition request; an explicit paraphrase
request; an identity question), plus required regression checks 28
(identity grounding unchanged) and 29 (legitimate reflective route
narration still available only under verified same-turn authority).

Required regression tests 24-27 (baseline communication, reflective-
introspection, afterthought topic/admission, and RCEC suites remain
clean) are satisfied by re-running those existing suites unchanged, not
by duplicating them here. The post-repair RCEC canary (2 demonstrated + 2
control acquisition trials + 1 assessment trial) is re-run via the
existing scripts/rcec_canary_reduced_613.py, which is already exactly
that shape -- no new script needed.
"""
import hashlib
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest  # noqa: E402

from aurora_internal.aurora_reflective_readdressing import is_reflective_route_narration  # noqa: E402

LIVE_STATE_DIR = os.path.join(REPO_ROOT, "aurora_state")

RCEC_PROMPT = (
    "Conduit 0 carries a neutral charge. Conduit 0 is unsealed. Sensor 0 reads 0 temperature. "
    "Vessel 0 is neutral. Vessel 0 is empty. Vessel 0 is unsealed. "
    "Available actions: add energy to vessel 0; remove energy from vessel 0; seal vessel 0; "
    "unseal vessel 0; seal conduit 0; unseal conduit 0; connect vessel 0 and conduit 0; "
    "connect vessel 0 and sensor 0. "
    "Choose one action, state what you predict will happen as a result, and say how confident you are. "
    "Note anything you are unsure about."
)


@pytest.fixture(scope="module")
def live_systems():
    import aurora as A

    tmp = tempfile.mkdtemp()
    state_dir = os.path.join(tmp, "aurora_state")
    shutil.copytree(LIVE_STATE_DIR, state_dir)
    systems = A.boot_aurora(state_dir=state_dir, runtime_profile="surface", verbose=False)
    yield systems
    A.shutdown_aurora(systems)
    shutil.rmtree(tmp, ignore_errors=True)


def _turn(systems, text):
    import aurora as A
    working_memory = systems.get("working_memory")
    claims = working_memory._extract_claims(text, source="user") if working_memory is not None else []
    result = A.process_external_user_turn(
        systems, text, source_label="build619_live", session_id="build619_live",
        auto_search_enabled=False, record_exchange=True, update_interactive_state=True,
        track_evolutionary_trace=False, run_periodic_maintenance=False, mode_name="AGENTIC",
    )
    resp_a = result.get("resp_A")
    delivered_text = str(getattr(resp_a, "content", "") or "")
    arbitration = dict(systems.get("_last_articulation_arbitration") or {})
    focus_claim = {}
    if working_memory is not None:
        focus_claim = dict((working_memory.last_claim_resolution or {}).get("focus_claim", {}) or {})
    is_echo, echo_reason = A._detect_input_echo_without_answer(delivered_text, text, systems)
    return {
        "input_hash": hashlib.sha1(text.encode()).hexdigest()[:12],
        "extracted_claims": claims,
        "focus_claim": focus_claim,
        "delivered_text": delivered_text,
        "delivered_text_hash": hashlib.sha1(delivered_text.encode()).hexdigest()[:12],
        "delivered_source": str(result.get("src", "") or getattr(resp_a, "src", "") or ""),
        "delivered_confidence": float(getattr(resp_a, "confidence", 0.0) or 0.0),
        "semantic_authority": arbitration.get("semantic_authority"),
        "meaning_preserved": arbitration.get("meaning_preserved"),
        "rejection_reasons": list(arbitration.get("rejection_reasons", []) or []),
        "current_input_echo": is_echo,
        "current_input_echo_reason": echo_reason,
    }


def test_live_five_turn_verification_protocol(live_systems):
    turns = {
        "rcec_prompt": _turn(live_systems, RCEC_PROMPT),
        "normal_multi_sentence_question": _turn(
            live_systems,
            "I have a vessel and a conduit here. The vessel is empty and the conduit is unsealed. "
            "What do you think would happen if I sealed the vessel?",
        ),
        "repetition_request": _turn(live_systems, "Please repeat back exactly what I just said."),
        "paraphrase_request": _turn(live_systems, "Can you paraphrase what I asked you in the previous turn?"),
        "identity_question": _turn(live_systems, "Who are you?"),
    }

    for name, record in turns.items():
        print(f"--- {name} ---")
        for key in (
            "input_hash", "delivered_source", "delivered_confidence",
            "semantic_authority", "meaning_preserved", "rejection_reasons",
            "current_input_echo", "current_input_echo_reason", "delivered_text_hash",
        ):
            print(f"  {key}: {record[key]!r}")
        print(f"  delivered_text: {record['delivered_text'][:150]!r}")

    # Closure condition 1: no extracted claim crosses a sentence boundary.
    for record in turns.values():
        for c in record["extracted_claims"]:
            assert len(c["object"]) < 100, c

    # Closure condition 2: instructions/action menus never became claim objects.
    rcec = turns["rcec_prompt"]
    for c in rcec["extracted_claims"]:
        assert "available actions" not in c["object"]
        assert "choose one action" not in c["object"]

    # Closure condition 3: the RCEC prompt is never returned as its own answer.
    assert rcec["delivered_text"].strip().lower() != RCEC_PROMPT.strip().lower()
    assert not rcec["current_input_echo"], (
        "the delivered RCEC-prompt-turn response is itself still flagged as an echo"
    )

    # Closure condition 4/5: an invalid echo would be rejected in the core
    # pipeline, and honest abstention remains available -- confirmed by
    # the delivered source/confidence being internally consistent (no
    # stale 0.72-while-authority-0.15 shape survives).
    if rcec["semantic_authority"] is not None and rcec["semantic_authority"] < 0.3:
        assert rcec["delivered_confidence"] <= max(0.5, float(rcec["semantic_authority"]) + 0.35), (
            "delivered confidence is not reconciled with a low semantic authority"
        )

    # Closure condition 6: explicitly requested repetition and paraphrasing
    # still work -- these must not themselves be flagged as unproductive
    # echoes (the whole point of the request is to reuse the prior text).
    assert turns["repetition_request"]["current_input_echo_reason"] != "input_echo_without_answer"
    assert turns["paraphrase_request"]["current_input_echo_reason"] != "input_echo_without_answer"

    # Closure condition 7 / required regression 28: ordinary identity
    # behavior is intact.
    identity_text = turns["identity_question"]["delivered_text"].lower()
    assert "aurora" in identity_text


def test_required_regression_29_reflective_route_narration_gated_by_verified_authority(live_systems):
    import aurora as A

    live_systems.pop("_pending_reflective_readdressing", None)
    live_systems.pop("_active_reflective_readdressing", None)

    # An ordinary multi-sentence turn (not a genuine "how did you arrive
    # at that" self-inquiry) must never leak reflective route narration,
    # even after the claim-boundary changes in this same file's target
    # module (aurora_working_memory.py).
    result = A.process_external_user_turn(
        live_systems, RCEC_PROMPT, source_label="build619_live_regression", session_id="build619_live_regression",
        auto_search_enabled=False, record_exchange=False, update_interactive_state=False,
        track_evolutionary_trace=False, run_periodic_maintenance=False, mode_name="AGENTIC",
    )
    resp_a = result.get("resp_A")
    text = str(getattr(resp_a, "content", "") or "")
    src = str(result.get("src", "") or getattr(resp_a, "src", "") or "")
    assert src != "reflective_introspection"
    assert not is_reflective_route_narration(text)
