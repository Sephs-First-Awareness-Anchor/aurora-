"""
tests/test_variant_transition_predictor.py
=============================================
MTSL Phase 7 (2026-07-13): VariantTransitionPredictor -- learns
SV-a -> SV-b -> outcome transition chains. New territory (no prior
transition-chain learner existed in the repo); no authority, purely
descriptive/predictive plumbing.
"""
from aurora_internal.dual_strata.variant_transition_predictor import (
    TransitionPrediction,
    TransitionRecord,
    VariantTransitionPredictor,
)


# ---- observe(): chain formation ----

def test_first_observation_has_no_prior_and_records_nothing():
    pred = VariantTransitionPredictor(state_dir=None)
    result = pred.observe("sv_A")
    assert result is None
    assert pred.last_variant_id == "sv_A"


def test_second_observation_records_a_transition():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    rec = pred.observe("sv_B")
    assert rec is not None
    assert rec.from_variant_id == "sv_A"
    assert rec.to_variant_id == "sv_B"
    assert rec.observation_count == 1


def test_none_variant_breaks_the_chain_without_error():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    result = pred.observe(None)
    assert result is None
    assert pred.last_variant_id is None
    # next real observation starts a fresh chain, not linked across the gap
    result2 = pred.observe("sv_B")
    assert result2 is None
    assert pred.get_transition("sv_A", "sv_B") is None


def test_repeated_transition_accumulates_observation_count():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    for _ in range(5):
        pred.observe("sv_B")
        pred.observe("sv_A")
    rec = pred.get_transition("sv_A", "sv_B")
    assert rec.observation_count == 5


# ---- outcome tracking ----

def test_positive_outcome_increments_positive_count():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=True)
    rec = pred.get_transition("sv_A", "sv_B")
    assert rec.outcome_positive == 1
    assert rec.outcome_negative == 0
    assert rec.outcome_support == 1.0


def test_negative_outcome_increments_negative_count():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=False)
    rec = pred.get_transition("sv_A", "sv_B")
    assert rec.outcome_negative == 1
    assert rec.outcome_support == 0.0


def test_no_outcome_given_leaves_neutral_prior():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    pred.observe("sv_B")
    rec = pred.get_transition("sv_A", "sv_B")
    assert rec.outcome_positive == 0 and rec.outcome_negative == 0
    assert rec.outcome_support == 0.5


def test_outcome_support_reflects_mixed_results():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=True)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=True)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=False)
    rec = pred.get_transition("sv_A", "sv_B")
    assert rec.observation_count == 3
    assert rec.outcome_positive == 2 and rec.outcome_negative == 1
    assert rec.outcome_support == round(2 / 3, 4)


# ---- predict_next(): ranking ----

def test_predict_next_empty_for_unknown_variant():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    pred.observe("sv_B")
    assert pred.predict_next("sv_never_seen") == []


def test_predict_next_ranks_by_observation_share():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    for _ in range(8):
        pred.observe("sv_B")
        pred.observe("sv_A")
    for _ in range(2):
        pred.observe("sv_C")
        pred.observe("sv_A")
    preds = pred.predict_next("sv_A")
    assert len(preds) == 2
    assert preds[0].to_variant_id == "sv_B"
    assert preds[0].probability == 0.8
    assert preds[1].to_variant_id == "sv_C"
    assert preds[1].probability == 0.2
    assert round(sum(p.probability for p in preds), 4) == 1.0


def test_predict_next_respects_limit():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    for target in ["sv_B", "sv_C", "sv_D", "sv_E", "sv_F", "sv_G"]:
        pred.observe(target)
        pred.observe("sv_A")
    preds = pred.predict_next("sv_A", limit=3)
    assert len(preds) == 3


def test_predict_next_tiebreaks_on_outcome_support():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    # sv_B and sv_C both get 2 observations (equal probability), but
    # sv_B has better outcome support
    pred.observe("sv_B", positive=True)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=True)
    pred.observe("sv_A")
    pred.observe("sv_C", positive=False)
    pred.observe("sv_A")
    pred.observe("sv_C", positive=False)
    pred.observe("sv_A")
    preds = pred.predict_next("sv_A")
    assert preds[0].to_variant_id == "sv_B"
    assert preds[0].observation_count == preds[1].observation_count == 2
    assert preds[0].outcome_support > preds[1].outcome_support


# ---- persistence ----

def test_state_round_trips_through_save_and_reload(tmp_path):
    state_dir = str(tmp_path)
    pred = VariantTransitionPredictor(state_dir=state_dir)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=True)
    pred.observe("sv_A")
    pred.observe("sv_B", positive=False)
    assert pred.save() is True

    reloaded = VariantTransitionPredictor(state_dir=state_dir)
    rec = reloaded.get_transition("sv_A", "sv_B")
    assert rec is not None
    assert rec.observation_count == 2
    assert rec.outcome_positive == 1 and rec.outcome_negative == 1
    assert reloaded.last_variant_id == pred.last_variant_id
    assert reloaded.transition_count() == pred.transition_count()


def test_save_without_dirty_state_returns_false(tmp_path):
    pred = VariantTransitionPredictor(state_dir=str(tmp_path))
    assert pred.save() is False


def test_no_state_dir_never_persists_but_still_functions():
    pred = VariantTransitionPredictor(state_dir=None)
    pred.observe("sv_A")
    rec = pred.observe("sv_B")
    assert rec is not None
    assert pred.save() is False


# ---- dataclass shape ----

def test_transition_record_to_dict_from_dict_round_trip():
    rec = TransitionRecord(
        from_variant_id="sv_A", to_variant_id="sv_B",
        observation_count=3, outcome_positive=2, outcome_negative=1,
        first_seen=100.0, last_seen=200.0,
    )
    restored = TransitionRecord.from_dict(rec.to_dict())
    assert restored == rec


def test_transition_prediction_to_dict_shape():
    p = TransitionPrediction(to_variant_id="sv_B", probability=0.8, outcome_support=0.9, observation_count=4)
    d = p.to_dict()
    assert set(d.keys()) == {"to_variant_id", "probability", "outcome_support", "observation_count"}
