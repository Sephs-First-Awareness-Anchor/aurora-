from aurora_expression_perception import ExpressionPerceptionEngine


def test_evolved_none_metadata_is_not_treated_as_emotion_shard(tmp_path):
    engine = ExpressionPerceptionEngine(state_dir=str(tmp_path))
    engine.cascade.energy_to_shard = lambda channels, mode: {
        "kind": "reflection",
        "payload_present": True,
    }
    result = engine.perceive({"text": "ordinary input"})
    assert result["shard"] is None
    assert result["seed"] is None
    assert result["consciousness_point"] is None
