"""A reply is a claim made in a representational FORM, and is wrong in that form
when it claims more than the input's representational state supports.

These pin the machinery that reconciles D2 Condition 2 (gibberish -> honest
abstain) with Build 769's communicative floor: they are not competing rules, each
is the right form for a different state of the input.
"""
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402
from aurora_turn_ledger import TurnLedger  # noqa: E402


class _Detector:
    """Stands in for the comprehension-gap detector: the existing measurement of the
    existence ladder (tokens with neither lexical nor ontological existence)."""

    def __init__(self, unknown):
        self._unknown = set(unknown)
        self.calls = 0

    def detect(self, text, lexicon=None, oets=None):
        self.calls += 1
        return {"unknown_words": [w for w in str(text).lower().split() if w.strip("?.,!") in self._unknown]}


def _systems(unknown, extra=None):
    s = {"comprehension_gap_system": SimpleNamespace(detector=_Detector(unknown)),
         "perception": SimpleNamespace(lexicon=None, oets=None)}
    s.update(extra or {})
    return s


# ---- one measurement, taken from the existing detector ---------------------------

def test_wholly_unrepresented_input_is_measured_as_such():
    st = A._input_representation_state(
        _systems({"zqxvornmal", "threbicultan"}),
        {"topic_words": ["zqxvornmal", "threbicultan"], "entities": []},
        "zqxvornmal threbicultan")
    assert st["overall"] == "unrepresented"
    assert st["unrepresented"] == ["threbicultan", "zqxvornmal"]
    assert st["off_ladder_ratio"] == 1.0


def test_partly_represented_input_is_partial_not_unrepresented():
    st = A._input_representation_state(
        _systems({"path"}), {"topic_words": ["stable", "path"], "entities": []}, "stable path")
    assert st["overall"] == "partial"
    assert st["unrepresented"] == ["path"]
    assert st["words"]["stable"] == "represented"


def test_ordinary_words_are_not_flagged_just_for_lacking_a_web_node():
    """The first version re-derived the rung from web nodes and called real words like
    "ancient" and "paths" unrepresented; the detector also consults the lexicon."""
    st = A._input_representation_state(
        _systems(set()), {"topic_words": ["ancient", "paths"], "entities": []}, "ancient paths")
    assert st["overall"] == "represented" and st["unrepresented"] == []


def test_no_content_and_unmeasured_never_gate():
    assert A._input_representation_state(_systems(set()), {"topic_words": [], "entities": []}, "")["overall"] == "no_content"
    # detector unavailable -> fail OPEN, distinguishable from "nothing to measure"
    st = A._input_representation_state({}, {"topic_words": ["x"], "entities": []}, "x")
    assert st["overall"] == "unmeasured" and st["unrepresented"] == []


def test_older_gate_reuses_the_turns_measurement_instead_of_measuring_again():
    measured = {"overall": "unrepresented", "words": {"asdf": "unrepresented", "qwerty": "unrepresented"},
                "unrepresented": ["asdf", "qwerty"], "off_ladder_ratio": 1.0}
    systems = _systems(set(), {"_turn_input_state": measured})
    r = A._utterance_representational_state(systems, SimpleNamespace(parsed={}), "asdf qwerty")
    assert r["state"] == "missing_representation" and r["off_ladder"] == ["asdf", "qwerty"]
    assert systems["comprehension_gap_system"].detector.calls == 0, "must not re-measure"


def test_older_gate_still_measures_when_no_turn_record_exists():
    systems = _systems({"asdf"})
    r = A._utterance_representational_state(
        systems, SimpleNamespace(parsed={"topic_words": ["asdf"], "entities": []}), "asdf")
    assert r["state"] == "missing_representation"
    assert systems["comprehension_gap_system"].detector.calls == 1


# ---- reply forms ----------------------------------------------------------------

def test_reply_form_classification():
    f = A._reply_form
    assert f("constraint_abstain", "I do not know.") == "boundary"
    assert f("constraint_communication_baseline", "My best read on that is it's about x.") == "hedged_read"
    assert f("constraint_communication_baseline", "I understand what you are saying about x.") == "acknowledgement"
    assert f("constraint_communication_baseline", "I hear that you are saying something about x, but I do not yet have a grounded representation of it.") == "boundary"
    assert f("composer_unified", "Photosynthesis converts light to energy.") == "assertion"


# ---- honest acknowledgement form -------------------------------------------------

def _assertion_state():
    return {
        "relational_form": {
            "raw_text": "Threbicultan mip fost.", "subject": "threbicultan", "relation": "fost",
            "obj": "", "complement": "", "question": False, "directive": False,
            "negated": False, "confidence": 0.8,
        },
        "axis_activation": {"X": 0.5, "T": 0.4, "N": 0.3, "B": 0.6, "A": 0.2},
        "emergent_operation": {"operation_id": "op", "status": "provisional"},
    }


def test_acknowledgement_names_no_understanding_of_an_unrepresented_focus():
    from aurora_internal.aurora_constraint_semantic_continuity import derive_constraint_grounded_candidate
    systems = {"_turn_input_state": {"overall": "partial", "unrepresented": ["threbicultan"]}}
    cand = derive_constraint_grounded_candidate(_assertion_state(), systems=systems)
    text = str(cand.get("text", ""))
    assert text, "the builder must still produce a communicative floor for an assertion"
    assert "I understand what you are saying" not in text, text
    assert "grounded representation" in text and "threbicultan" in text, text


def test_acknowledgement_form_is_unchanged_when_the_focus_is_represented():
    from aurora_internal.aurora_constraint_semantic_continuity import derive_constraint_grounded_candidate
    systems = {"_turn_input_state": {"overall": "partial", "unrepresented": ["somethingelse"]}}
    cand = derive_constraint_grounded_candidate(_assertion_state(), systems=systems)
    assert "I understand what you are saying about threbicultan" in str(cand.get("text", ""))
    # and with no measured state at all, behavior is exactly what it was
    cand2 = derive_constraint_grounded_candidate(_assertion_state())
    assert "I understand what you are saying about threbicultan" in str(cand2.get("text", ""))


# ---- the form-typed record --------------------------------------------------------

def _resp(src, text):
    return SimpleNamespace(src=src, content=text)


def test_overclaim_against_unrepresented_input_is_recorded_as_form_mismatch():
    led = TurnLedger("Zqxv?")
    sysd = {"_turn_input_state": {"overall": "unrepresented", "words": {"zqxv": "unrepresented"},
                                  "unrepresented": ["zqxv"]}}
    A._record_reply_form_state(sysd, led, _resp("constraint_communication_baseline",
                               "I understand what you are saying about zqxv."), "Zqxv?")
    assert led.form_state["form"] == "acknowledgement"
    assert led.form_state["mismatch"] is True
    assert led.form_state["named_unrepresented"] == ["zqxv"]


def test_abstain_against_unrepresented_input_is_not_a_mismatch():
    led = TurnLedger("Zqxv?")
    sysd = {"_turn_input_state": {"overall": "unrepresented", "words": {"zqxv": "unrepresented"},
                                  "unrepresented": ["zqxv"]}}
    A._record_reply_form_state(sysd, led, _resp("constraint_abstain", "I do not know what that is."), "Zqxv?")
    assert led.form_state["form"] == "boundary"
    assert led.form_state["mismatch"] is False


def test_grounded_answer_to_represented_input_is_not_a_mismatch():
    led = TurnLedger("What is photosynthesis?")
    sysd = {"_turn_input_state": {"overall": "represented", "words": {"photosynthesis": "structural"},
                                  "unrepresented": []}}
    A._record_reply_form_state(sysd, led, _resp("composer_unified", "Photosynthesis converts light to energy."), "What is photosynthesis?")
    assert led.form_state["mismatch"] is False


def test_no_state_means_no_record():
    led = TurnLedger("x")
    A._record_reply_form_state({}, led, _resp("generative", "hi"), "x")
    assert led.form_state == {}


# ---- a prior claim may fill a live slot only through represented content ----------

def _focus_support(cur, foc):
    import aurora_internal.aurora_recursive_causal_reasoning_waveform as R
    return R._focus_claim_support(cur, foc, {})


_COAUTHOR = {"subject": "co-author", "relation": "is", "object": "cael devo",
             "summary": "co-author is cael devo", "topic": ""}


def test_shared_copula_is_not_shared_content():
    """"What is photosynthesis?" was 'supported' by the unrelated claim "co-author is
    Cael Devo" on the strength of the word "is" alone, and backprojection then filled
    the question's empty object with "cael devo"."""
    r = _focus_support({"raw_text": "What is photosynthesis?", "subject": "photosynthesis",
                        "relation": "is", "obj": ""}, _COAUTHOR)
    assert r["supported"] is False
    assert r["direct_overlap"] == []


def test_genuine_shared_content_still_supports():
    r = _focus_support({"raw_text": "Who is Cael Devo?", "subject": "cael devo",
                        "relation": "is", "obj": ""}, _COAUTHOR)
    assert r["supported"] is True
    assert "cael" in r["direct_overlap"]


def test_shared_relation_word_alone_is_not_shared_content():
    claim = {"subject": "growth", "relation": "means", "object": "increase",
             "summary": "growth means increase", "topic": ""}
    assert _focus_support({"raw_text": "Photosynthesis does not mean storms",
                           "subject": "photosynthesis", "relation": "mean", "obj": ""},
                          claim)["supported"] is False
    assert _focus_support({"raw_text": "Growth does not mean decay", "subject": "growth",
                           "relation": "mean", "obj": ""}, claim)["supported"] is True


# ---- degenerate composer output ----------------------------------------------------

def test_identical_repeated_sentence_is_degenerate_at_any_length():
    f = A._composer_text_repeats_itself
    assert f("I am snorbel. I am snorbel.") is True
    assert f("I am that's all for now. I exist that's all for now.") is True
    assert f("Photosynthesis converts light to energy.") is False
    assert f("Cats meow. Dogs bark.") is False
    assert f("Yes. Yes.") is False  # one-word sentences are not the composer's failure mode
