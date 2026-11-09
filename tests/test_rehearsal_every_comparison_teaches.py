# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A108 -- every comparison with Sunni's real reply adjusts her
understanding: a two-sided diagnosis (meaning / expression), no dropped
partials, silence judged too, his words passed as the receiver's."""
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "flutter_app", "android", "app", "src", "main", "python"))
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

import aurora  # noqa: E402
import aurora_historical_experience_environment as H  # noqa: E402

FORM = {"subject": "you", "relation": "like", "obj": "music"}
REAL = "Honestly I love music, especially old soul records on a slow night."


def test_on_topic_word_list_is_meaning_right_expression_not_formed():
    out = H.rehearsal_comparison("music. records.", REAL, FORM, expression_score=0.0)
    assert out["meaning_positive"] is True and out["expression_positive"] is False
    assert out["label"] == "rehearsal_partial"


def test_on_topic_formed_reply_is_a_match():
    out = H.rehearsal_comparison("I love old soul music.", REAL, FORM, expression_score=0.8)
    assert out["label"] == "rehearsal_match"


def test_off_topic_is_a_mismatch_and_silence_is_its_own_outcome():
    assert H.rehearsal_comparison("Clouds drift north.", REAL, FORM, expression_score=0.9)["label"] == "rehearsal_mismatch"
    silent = H.rehearsal_comparison("", REAL, FORM)
    assert silent["label"] == "rehearsal_silent" and silent["meaning_positive"] is False


def test_expression_score_is_her_own_grammaticality_measure():
    pending = {"contributors": {"expression": {"grammaticality": 0.0}, "grammar_motif": {"constraint_fit": 0.66}}}
    assert H.rehearsal_expression_score(pending) == 0.66
    assert H.rehearsal_expression_score({"contributors": {}}) is None


def test_classifier_reads_both_sides_and_ignores_the_real_replys_wording():
    obs = {"accuracy": {"label": "rehearsal_partial", "score": 0.5, "rehearsal": True,
                        "meaning_positive": True, "expression_positive": False, "expression_score": 0.0}}
    out = aurora._classify_validated_communication({}, obs, "what do you mean by that? I don't understand")
    assert out["outcome_kind"] == "negative" and out["meaning_issue"] is False and out["expression_issue"] is True
    assert out["meaning_positive"] is True and out["expression_positive"] is False


class Rec:
    def __init__(self):
        self.calls = []

    def record_motif_outcome(self, motif, polarity, **kw):
        self.calls.append(("grammar", polarity, kw.get("context_text")))
        return True

    def record_evidence_outcome(self, **kw):
        self.calls.append(("lexical", kw["outcome_kind"]))
        return {"recorded": True}

    def record_receiver_outcome(self, *args, **kw):
        if "positive" in kw:
            self.calls.append(("crystal", kw["positive"]))
            return True
        self.calls.append(("verdict", args[1]))
        return {}


def _systems(rec):
    return {"grammar_engine": rec, "lexical_grounding": rec, "_concept_crystal_registry": rec,
            "reasoning_paths": rec, "unformed_patterns": rec, "state_dir": "/tmp/aurora_fix_a108"}


def _pending():
    return {"response_id": "U:1", "contributors": {"grammar_motif": {"motif_id": "m1"},
                                                    "lexical_grounding": [{"candidate_id": "c", "evidence_id": "e"}],
                                                    "concept_crystal": {"crystal_id": "x"}}}


def test_partial_teaches_meaning_organs_positively_and_expression_organs_negatively():
    rec = Rec()
    obs = {"validated_response": _pending(),
           "accuracy": {"label": "rehearsal_partial", "score": 0.5, "rehearsal": True, "meaning_positive": True,
                        "expression_positive": False, "expression_score": 0.0}}
    aurora._finalize_validated_communication(_systems(rec), obs, REAL, session_id="rehearsal_E1")
    assert ("grammar", "negative", REAL) in rec.calls            # expression side, with his words
    assert ("lexical", "positive") in rec.calls                   # meaning side
    assert ("crystal", True) in rec.calls
    assert rec.calls.count(("verdict", "positive")) == 2          # paths + unformed: meaning side


def test_a_mismatch_now_reaches_the_meaning_organs():
    rec = Rec()
    obs = {"validated_response": _pending(),
           "accuracy": {"label": "rehearsal_mismatch", "score": 0.05, "rehearsal": True, "meaning_positive": False,
                        "expression_positive": True, "expression_score": 0.7}}
    aurora._finalize_validated_communication(_systems(rec), obs, REAL, session_id="rehearsal_E1")
    assert ("lexical", "negative") in rec.calls and ("crystal", False) in rec.calls
    assert ("grammar", "positive", REAL) in rec.calls


def test_live_turns_keep_their_gating():
    rec = Rec()
    obs = {"validated_response": _pending(), "accuracy": {"label": "unresolved", "score": 0.1}}
    aurora._finalize_validated_communication(_systems(rec), obs, "ok", session_id="praxis:dm:x")
    assert not any(c[0] in ("grammar", "lexical", "crystal") for c in rec.calls)


def test_silence_with_a_registered_understanding_is_still_judged():
    class Contract:
        def __init__(self):
            self.state = {"pending_validation": {}}

        def snapshot(self):
            return {"pending_validation": dict(self.state["pending_validation"])}

        def _activate_session_pending(self, session):
            pass

    finalized = []

    class FakeAurora:
        def process_external_user_turn(self, systems, text, **kw):
            systems["understanding_contract"].state["pending_validation"] = {"response_id": "U:9", "contributors": {}}
            return {"resp_A": SimpleNamespace(content="")}

        def _finalize_validated_communication(self, systems, observation, user_text, *, session_id=""):
            finalized.append((observation["accuracy"], user_text))
            return {"outcome_kind": "negative"}

    systems = {"understanding_contract": Contract(), "_last_pipeline_state": {"relational_form": FORM}}
    env = object.__new__(H.HistoricalExperienceEnvironment)
    env.systems, env.rehearse, env._rehearsal, env.last_rehearsal = systems, True, None, {}
    env.skip_absorbed, env._absorbed_episodes = False, set()
    env.rehearsal_counters = {k: 0 for k in ("rehearsed", "silent", "compared", "match", "partial", "mismatch",
                                             "fanned_out", "errors", "lived_by_clones", "silent_judged")}
    fake = FakeAurora()
    env._rehearse_reply(fake, "Do you like music?", "E1", {"event_id": "x"})
    assert env._rehearsal and env._rehearsal["reply"] == ""
    env._compare_rehearsal(fake, REAL)
    assert finalized[0][0]["label"] == "rehearsal_silent" and finalized[0][1] == REAL
    assert env.rehearsal_counters["silent_judged"] == 1 and env.rehearsal_counters["fanned_out"] == 1
