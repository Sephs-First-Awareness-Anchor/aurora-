from aurora_dream_trainer import RetainedLearningBank, RetainedLearningRecord


def test_generic_strategy_learning_is_not_returned_as_semantic_knowledge(tmp_path):
    bank = RetainedLearningBank(state_dir=str(tmp_path))
    generic = "what creates friction when approached with curious inquiry — it connects to perspective (B-axis, depth 0.34)."
    semantic = "A crystal can preserve coherence through complex relationships."
    assert bank._is_generic_strategy_learning(generic)
    assert not bank._is_generic_strategy_learning(semantic)
    bank._records[bank._key(generic)] = RetainedLearningRecord(text=generic, confidence=0.95, topic_words=["perspective"])
    bank._records[bank._key(semantic)] = RetainedLearningRecord(text=semantic, confidence=0.8, topic_words=["crystal"])
    assert generic not in bank.relevant("general", ["perspective"], limit=4)
    assert bank.relevant("general", ["crystal"], limit=4) == [semantic]
