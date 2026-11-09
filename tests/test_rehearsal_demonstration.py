# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A110 -- Sunni's real reply is a demonstration, not just a verdict."""
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "flutter_app", "android", "app", "src", "main", "python"))
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

from aurora_internal.aurora_reasoning_paths import (ReasoningPaths, DEMONSTRATION_WEIGHT, compare,  # noqa: E402
                                                    MAX_ABILITY_LEAN)
from aurora_grammar_engine import GrammarEngine  # noqa: E402
from aurora_internal.aurora_lexical_grounding import AuroraLexicalGrounding  # noqa: E402
import aurora_historical_experience_environment as H  # noqa: E402

SIG = {"shape": "you|like|music|q", "axes": {"X": 0.1, "T": 0.2, "N": 0.9, "B": 0.3, "A": 0.1}}
DEMO = {"meaning_label": "affinity", "meaning_signature": "s", "dominant_axis": "N",
        "action": "respond_to_him", "operation": "answer", "emotion": "warm", "bias": "b",
        "abilities": ["N:SOUL", "N:WARMTH"], "concepts": ["music"]}


def test_a_demonstrated_path_carries_his_landing_not_her_choices(tmp_path):
    rp = ReasoningPaths(state_dir=str(tmp_path))
    out = rp.carve_demonstration(SIG, DEMO)
    path = rp.paths[out["path_id"]]
    assert path["weight"] == DEMONSTRATION_WEIGHT and path["demonstrations"] == 1
    assert path["landings"]["action"] == "" and path["landings"]["operation"] == ""
    assert path["landings"]["abilities"] == ["N:SOUL", "N:WARMTH"]
    again = rp.carve_demonstration(SIG, DEMO)
    assert again["deepened"] == out["path_id"] and rp.paths[out["path_id"]]["weight"] > DEMONSTRATION_WEIGHT


def test_next_time_that_pressure_comes_her_selection_leans_toward_his_abilities(tmp_path):
    rp = ReasoningPaths(state_dir=str(tmp_path))
    rp.carve_demonstration(SIG, DEMO)
    rp.offer = {"signature": SIG, "path": rp.recall(SIG)}
    assert rp.offer["path"] is not None
    assert 0.0 < rp.ability_lean("N:SOUL") <= MAX_ABILITY_LEAN
    assert rp.ability_lean("B:OTHER") == 0.0


def test_a_path_that_does_not_name_a_landing_does_not_constrain_it():
    demo = {**DEMO, "action": "", "operation": "", "emotion": "", "bias": ""}
    live = {**DEMO, "action": "explain", "operation": "evaluate_proposition"}
    assert compare(demo, live)["agrees"] is True
    assert compare({**demo, "meaning_label": "other"}, live)["agrees"] is False


def test_his_sentences_are_credited_as_structure_that_worked(tmp_path):
    eng = GrammarEngine(state_dir=str(tmp_path))
    before = sum(m.success_count for m in eng._lineage._motifs.values())
    n = eng.observe_demonstration("I love old soul records. They feel like home on a slow night.",
                                  context_text="Do you like music?")
    after = sum(m.success_count for m in eng._lineage._motifs.values())
    assert n >= 1 and after - before == n


def test_the_word_his_reply_turned_on_is_validated_and_kept_out_of_her_next_turn(tmp_path):
    lg = AuroraLexicalGrounding(state_dir=str(tmp_path), persist=True)
    lg._derive_relation_and_form = lambda raw: ("love", {"relation": "love", "subject": "i", "obj": "records",
                                                         "raw_text": raw})
    first = None
    for _ in range(6):                      # found the trial, then match it
        first = lg.observe_demonstration(raw_text="I love old soul records.", context_text="Do you like music?",
                                         demonstration_id="evt:1")
    assert first["admitted"] is True
    assert lg.drain_turn_consumption_trace() == []
    validated = [e for c in lg._candidates.values() for e in c.evidence
                 if e.get("provenance") == "demonstration" and e.get("validated")]
    if any(c.word == "love" for c in lg._candidates.values()):
        assert validated and all(e["outcome_kind"] == "positive" for e in validated)


def test_after_each_comparison_she_listens_to_his_reply_and_learns_where_it_lands(tmp_path):
    rp = ReasoningPaths(state_dir=str(tmp_path))
    calls = []

    class Contract:
        def __init__(self):
            self.state = {"pending_validation": {}}

        def snapshot(self):
            return {"pending_validation": dict(self.state["pending_validation"])}

        def _activate_session_pending(self, session):
            calls.append(("retire", session))

    class Grammar:
        def observe_demonstration(self, text, *, context_text="", max_sentences=4):
            calls.append(("grammar", text, context_text, max_sentences))
            return 2

    class Lexical:
        def observe_demonstration(self, *, raw_text, context_text="", demonstration_id="", demonstrated_by="sunni"):
            calls.append(("lexical", raw_text, demonstration_id, demonstrated_by))
            return {"admitted": True, "validated": True}

    systems = {"reasoning_paths": rp, "understanding_contract": Contract(), "grammar_engine": Grammar(),
               "lexical_grounding": Lexical()}

    class FakeAurora:
        def process_external_user_turn(self, systems_, text, **kw):
            calls.append(("listen", text, kw["source_label"], kw["session_id"]))
            systems_["_last_pipeline_state"] = {"meaning_label": "affinity", "dominant_axis": "N",
                                                "selected_conscious_action": "her_choice"}
            systems_["_last_active_ability_ids"] = ["N:SOUL"]
            return {"resp_A": SimpleNamespace(content="whatever")}

    env = object.__new__(H.HistoricalExperienceEnvironment)
    env.systems, env.demonstrate = systems, True
    env.rehearsal_counters = {}
    # The verdict has already consumed the turn's path record: the
    # signature is held from the rehearsal itself.
    held = {"session": "rehearsal_E1", "pending": {"response_id": "U:1"}, "heard": "Do you like music?",
            "event_id": "evt:1", "path_signature": SIG}
    out = env._demonstrate(FakeAurora(), held, "I love old soul records.")
    assert ("listen", "I love old soul records.", "historical_demonstration", "demo_rehearsal_E1") in calls
    assert ("retire", "demo_rehearsal_E1") in calls
    path = rp.paths[out["path"]["path_id"]]
    assert path["landings"]["abilities"] == ["N:SOUL"] and path["landings"]["action"] == ""
    assert path["shape"] == SIG["shape"]
    assert out["motifs"] == 2 and out["word"]["validated"] is True
    assert env.rehearsal_counters["demonstrated"] == 1 and env.rehearsal_counters["demo_paths"] == 1
