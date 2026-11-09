# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A112 -- she rehearses both positions: Sunni's (judged by his real reply)
and GPT's (judged by GPT's real reply, long and well-formed)."""
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "flutter_app", "android", "app", "src", "main", "python"))
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

import aurora_historical_experience_environment as H  # noqa: E402

USER, GPT = "historical_user", "historical_other_assistant"


class Contract:
    def __init__(self):
        self.state = {"pending_validation": {}}

    def snapshot(self):
        return {"pending_validation": dict(self.state["pending_validation"])}

    def _activate_session_pending(self, session):
        pass


class FakeAurora:
    def __init__(self):
        self.turns, self.finalized, self.n = [], [], 0

    def process_external_user_turn(self, systems, text, **kw):
        self.turns.append((kw["source_label"], kw["session_id"], text))
        self.n += 1
        systems["understanding_contract"].state["pending_validation"] = {"response_id": f"U:{self.n}",
                                                                         "contributors": {}}
        return {"resp_A": SimpleNamespace(content=f"reply {self.n} about music")}

    def _finalize_validated_communication(self, systems, observation, user_text, *, session_id=""):
        self.finalized.append((session_id, user_text))
        return {"outcome_kind": "negative"}


def make_env(fake):
    systems = {"understanding_contract": Contract(), "_last_pipeline_state": {"relational_form": {}},
               "aurora_module": fake}
    env = H.HistoricalExperienceEnvironment.__new__(H.HistoricalExperienceEnvironment)
    env.systems, env.rehearse, env._rehearsal, env.last_rehearsal = systems, True, None, {}
    env.skip_absorbed, env._absorbed_episodes, env.demonstrate = False, set(), False
    env.positions = dict(H.REHEARSAL_POSITIONS)
    env.rehearsal_counters = {k: 0 for k in ("rehearsed", "silent", "compared", "match", "partial", "mismatch",
                                             "fanned_out", "errors", "lived_by_clones", "silent_judged")}
    env.rehearsal_by_position = {"sunni": {}, "assistant": {}}
    return env


def ev(actor, text):
    return {"actor": actor, "text": text, "event_id": f"e:{text[:6]}"}


def test_she_takes_both_positions_in_turn():
    fake = FakeAurora()
    env = make_env(fake)
    env._rehearse(ev(USER, "Do you like music?"), USER, "E1", True)
    assert fake.turns[-1][1] == "rehearsal_gpt_E1"                       # answering Sunni, as GPT
    out = env._rehearse(ev(GPT, "Absolutely, music is wonderful, especially soul."), GPT, "E1", False)
    assert out["compared"] is True                                        # GPT's real reply judged her
    assert fake.finalized[-1] == ("rehearsal_gpt_E1", "Absolutely, music is wonderful, especially soul.")
    assert fake.turns[-1][1] == "rehearsal_E1" and out["position"] == "sunni"   # now answering GPT, as Sunni
    out = env._rehearse(ev(USER, "I love old soul records."), USER, "E1", False)
    assert out["compared"] is True and fake.finalized[-1] == ("rehearsal_E1", "I love old soul records.")
    assert env.rehearsal_by_position["assistant"]["compared"] == 1
    assert env.rehearsal_by_position["sunni"]["compared"] == 1
    assert env.rehearsal_by_position["assistant"]["rehearsed"] == 2


def test_a_reply_from_the_same_speaker_does_not_judge_the_rehearsal():
    fake = FakeAurora()
    env = make_env(fake)
    env._rehearse(ev(USER, "Do you like music?"), USER, "E1", True)
    out = env._rehearse(ev(USER, "Also, what about films?"), USER, "E1", False)
    assert "compared" not in out and fake.finalized == []
    assert fake.turns[-1][2] == "Also, what about films?"


def test_sunni_only_still_works_when_gpt_position_is_off():
    fake = FakeAurora()
    env = make_env(fake)
    env.positions = {GPT: "sunni"}
    assert env._rehearse(ev(USER, "Do you like music?"), USER, "E1", True) == {}
    assert fake.turns == []


def test_gpt_demonstrations_credit_more_of_its_long_replies():
    assert H.DEMONSTRATION_SENTENCES["assistant"] > H.DEMONSTRATION_SENTENCES["sunni"]
