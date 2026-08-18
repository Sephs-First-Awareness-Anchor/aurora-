from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import aurora
from aurora_habitat import HabitatEntity, HabitatRuntime, _entity_renderability
from aurora_habitat_motivation import _creation_instance
from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
from aurora_manifold_directory.noncomp_field import NoncompField, REFERENCE_AXIS_PRESSURE
from aurora_sedimemory import SediMemory
from aurora_simulation_engine import (
    ConversationObservation,
    ConsciousLearner,
    ResponseConcept,
    ConceptualResponse,
    SimulationSession,
)


class _Entry:
    def __init__(self, word, meaning, valence=0.0):
        self.word = word
        self.meaning = meaning
        self.role = "verb"
        self.emotional_valence = valence


class _FakeNode:
    def __init__(self, word, meaning):
        self.word = word
        self.role = "noun"
        self.emotional_valence = 0.0
        self.lineage = ""
        self.definitions = [{"text": meaning, "confidence": 0.8}]
        self.senses = {}

    def best_definition(self):
        return self.definitions[0]["text"]


class _FakeWeb:
    def __init__(self):
        self.nodes = {}

    def add_node(self, word, role, valence=0.0, meaning="", lineage=""):
        node = self.nodes.get(word)
        if node is None:
            node = _FakeNode(word, meaning)
            node.role = role
            node.emotional_valence = valence
            node.lineage = lineage
            self.nodes[word] = node
        return node

    def _remove_node(self, word):
        self.nodes.pop(word, None)


class _FakeOETS:
    def __init__(self):
        self.web = _FakeWeb()


def test_noncomp_profile_retains_existing_generalized_semantic_root():
    field = NoncompField()
    profile = next(p for p in field.all_profiles() if p.key.nc_name == "Agentive_Difference_of_Existence")
    summary = profile.semantic_summary()
    assert "gap" in summary.lower()
    assert "actually carried" in summary.lower()


def test_local_coordinates_have_distinct_semantic_ancestry_without_predefining_descendants():
    a_diff = aurora._manifold_coordinate_summary("X", "A", "DIFFERENCE")
    b_diff = aurora._manifold_coordinate_summary("X", "B", "DIFFERENCE")
    assert a_diff and b_diff
    assert a_diff != b_diff
    # Same broad target, different participating constraint ancestry.
    assert "gap" in a_diff.lower()


def test_semantic_ancestry_discriminates_only_between_already_local_candidates():
    basis = [aurora._manifold_coordinate_summary("X", "A", "DIFFERENCE")]
    fitting = _Entry("lack", "a gap between what should be present and what is actually carried")
    unrelated = _Entry("sparkle", "decorative visual brightness and glitter")
    assert aurora._local_semantic_fit(fitting, basis) > aurora._local_semantic_fit(unrelated, basis)


def test_seed_prompt_no_longer_gets_regex_semantic_identity():
    session = SimulationSession.__new__(SimulationSession)
    t1 = session._topic_from_seed_prompt("[AFTERTHOUGHT] How are you?", {})
    t2 = session._topic_from_seed_prompt("[AFTERTHOUGHT] What's your name?", {})
    assert t1["prompt"] == "How are you?"
    assert t2["prompt"] == "What's your name?"
    assert t1["semantic_topic"] == ""
    assert t2["semantic_topic"] == ""
    assert t1["topic_resolution_status"] == "unresolved"
    assert t2["topic_resolution_status"] == "unresolved"


def test_response_outcome_is_structured_evidence_not_semantic_prose():
    learner = ConsciousLearner()
    response = ConceptualResponse(primary_concept=ResponseConcept.DIRECT_CLARITY)
    obs = ConversationObservation(connection_felt_stronger=True)
    shard = learner.observe_outcome(response, obs, "practical", topic_word="How are you?", episode_source="afterthought")
    assert shard is not None
    assert shard.evidence_kind == "response_outcome"
    assert shard.understanding == ""
    assert shard.evidence["outcome"] == "connection_stronger"
    assert learner.check_admission(shard)[1] == "nonsemantic_outcome_evidence"
    assert learner.inject_into_oets(_FakeOETS()) == 0


def test_explicit_semantic_claim_can_still_be_admitted_without_outcome_template():
    learner = ConsciousLearner()
    shard = learner.propose_shard("continuity persists across observed change", confidence=0.8)
    assert shard is not None
    assert shard.evidence_kind == "semantic_claim"
    ok, reason = learner.check_admission(shard)
    assert ok, reason
    assert learner.inject_into_oets(_FakeOETS()) == 1


def test_legacy_generated_outcome_prose_is_quarantined_on_import():
    learner = ConsciousLearner()
    learner.import_state({"shards": [{
        "shard_id": "old", "response_concept": "direct_clarity",
        "observation_summary": "", "understanding": "how built connection when approached with direct clarity",
        "context_type": "practical", "confidence": 0.9, "observation_count": 5,
        "episode_source": "afterthought", "semantic_topic": "how",
        "topic_resolution_status": "resolved", "outcome_axis": "A-axis relief",
    }]})
    shard = learner.shards["old"]
    assert shard.evidence_kind == "response_outcome"
    assert learner.check_admission(shard)[0] is False


def test_afterthought_deeper_work_does_not_block_surface_and_retains_cause():
    class Sim:
        def run_episode(self, **kwargs):
            time.sleep(0.20)
            return SimpleNamespace(episode_id="ep-later")
    gateway = SimpleNamespace(simulation=Sim())
    systems = {
        "aurora": SimpleNamespace(gateway=gateway),
        "ExistenceMode": SimpleNamespace(BOUNDED="bounded"),
        "_current_turn_id": "turn-77",
    }
    started = time.perf_counter()
    thread = aurora._dispatch_afterthought_subsurface(
        systems, "A difficult question?", session_id="s", turn_tick=77,
    )
    elapsed = time.perf_counter() - started
    assert thread is not None
    assert elapsed < 0.12
    assert systems["_last_afterthought_dispatch"]["nonblocking"] is True
    assert systems["_last_afterthought_dispatch"]["cause"]["turn_id"] == "turn-77"
    thread.join(timeout=1.0)
    assert systems["_last_afterthought_result"]["cause"]["turn_id"] == "turn-77"
    assert systems["_last_afterthought_result"]["episode_id"] == "ep-later"


def test_immediate_reentry_cannot_claim_understanding_before_receiver_validation(tmp_path):
    contract = RuntimeUnderstandingContract(state_dir=str(tmp_path), persist=False)
    contract._compute_tension = lambda *_args, **_kw: {"total": 0.0}
    contract._attempt_reconciliation = lambda _tension: (True, [])
    cascades = []
    contract._trigger_downward_cascade = lambda systems, understanding: cascades.append(understanding)
    result = contract.run_reflection_cycle({}, "question", "provisional reply", allow_understanding=False)
    assert result["reached_understanding"] is False
    assert result["reflection_step"] == "RECONCILED_PENDING_RECEIVER"
    assert cascades == []


def test_receiver_permitted_reflection_uses_existing_downward_cascade(tmp_path):
    contract = RuntimeUnderstandingContract(state_dir=str(tmp_path), persist=False)
    contract._compute_tension = lambda *_args, **_kw: {"total": 0.0}
    contract._attempt_reconciliation = lambda _tension: (True, [])
    contract._emit_understanding = lambda **_kw: {"resolved_accuracy": 0.9, "tension_total": 0.0}
    cascades = []
    contract._trigger_downward_cascade = lambda systems, understanding: cascades.append(understanding)
    result = contract.run_reflection_cycle({}, "confirmed", "prior reply", allow_understanding=True)
    assert result["reached_understanding"] is True
    assert len(cascades) == 1


def test_pressure_relief_moves_excess_toward_native_reference_without_undershoot():
    field = NoncompField()
    field.ingest_external_input({"X": 1.0}, intensity=1.0, source="test")
    before = field.axis_pressure(0)
    assert before > REFERENCE_AXIS_PRESSURE
    for _ in range(20):
        field.reset_pressure_topology({"resolved_accuracy": 1.0})
    after = field.axis_pressure(0)
    assert REFERENCE_AXIS_PRESSURE <= after < before


def test_sedimemory_fragment_count_reads_canonical_column_stats():
    mem = SediMemory()
    mem._column.stats = lambda: {"total_active_frags": 17}
    assert mem.fragment_count() == 17


def test_autonomous_create_candidates_are_physically_complete():
    for _ in range(30):
        params, _sources = _creation_instance("space", {"native_dimensions": {}})
        entity = HabitatEntity(
            id="x", entity_type=params["entity_type"], creator="aurora", owner="shared",
            territory="space", position=params["position"], dimensions=params["dimensions"],
            orientation=params["orientation"], visual_properties=params["visual_properties"],
            content=dict(params.get("content") or {}),
        )
        ok, reason = _entity_renderability(entity)
        assert ok, (params, reason)
        assert entity.entity_type in {"shape", "mark_path"}


def test_habitat_rejects_incomplete_text_creation_and_reports_legacy_incomplete(tmp_path):
    habitat = HabitatRuntime(tmp_path)
    denied = habitat.act(actor="aurora", territory="space", operation="create",
                         parameters={"entity_type": "text", "position": [0.5, 0.5]})
    assert denied.success is False
    assert "incomplete_entity" in denied.rejected_reason
    legacy = HabitatEntity(id="legacy", entity_type="text", creator="aurora", owner="shared",
                           territory="space", content={})
    habitat._entities[legacy.id] = legacy
    report = habitat.integrity_report()
    assert report["incomplete_live_count"] == 1
    assert report["surface_renderable_count"] == report["entity_count"] - 1
    assert report["incomplete_live_entities"][0]["id"] == "legacy"


def test_habitat_flutter_surface_observes_autonomous_changes_without_human_gesture():
    source = Path("flutter_app/lib/habitat/habitat_gesture_layer.dart").read_text()
    assert "Timer.periodic" in source
    assert "_stateRefreshTimer?.cancel()" in source


def test_hub_telemetry_names_actual_concept_crystal_registry():
    bridge = Path("flutter_app/android/app/src/main/python/aurora_bridge.py").read_text()
    hub = Path("flutter_app/lib/screens/hub_screen.dart").read_text()
    assert '_systems.get("_concept_crystal_registry")' in bridge
    assert 'Concept Crystals' in hub
    assert "_systems.get(\"sensory_crystal\")" not in bridge[bridge.find("# ── Concept Crystals"):bridge.find("# ── EvolutionaryChamber")]


def test_receiver_validated_relief_is_local_to_participating_noncomp_region():
    field = NoncompField()
    region = next(
        p for p in field.all_profiles()
        if p.key.nc_law_c == 0 and p.key.nc_target == 0
    )
    field.ingest_external_input({"X": 1.0, "N": 1.0}, intensity=1.0, source="test")
    x_before = field.axis_pressure(0)
    n_before = field.axis_pressure(2)
    field.reset_pressure_topology({
        "resolved_accuracy": 1.0,
        "resolved_noncomp_regions": [{"nc_name": region.key.nc_name}],
    })
    assert field.axis_pressure(0) < x_before
    assert field.axis_pressure(2) == pytest.approx(n_before)


def test_legacy_oets_outcome_prose_can_be_migrated_at_boot_boundary():
    learner = ConsciousLearner()
    oets = _FakeOETS()
    old = oets.web.add_node(
        "how", role="learned_behavior", lineage="learner:afterthought"
    )
    old.definitions = [{
        "text": "how built connection when approached with direct clarity",
        "confidence": 0.9,
    }]
    assert learner.purge_legacy_semantic_contamination(oets) == 1
    assert "how" not in oets.web.nodes


class _LocalOETSWeb:
    def get_relation_between(self, *_args):
        return None


class _LocalOETS:
    def __init__(self, nodes):
        self.web = _LocalOETSWeb()
        self._nodes = list(nodes)

    def get_nodes_by_noncomp(self, _noncomp_id):
        return list(self._nodes)


class _LocalPerception:
    def __init__(self, nodes):
        self.oets = _LocalOETS(nodes)
        self.lexicon = None


class _LocalDimensional:
    def get_constraint_aggregate(self):
        return {"X": 0.8, "T": 0.1, "N": 0.2, "B": 0.3, "A": 0.9}


def _local_manifold_state():
    return SimpleNamespace(
        emotional_state={"intensity": 0.5},
        understood={}, pipeline_state={}, semantic_pressure=0.0,
    )


def _agentive_difference_binding():
    return {
        "nc_name": "Agentive_Difference_of_Existence",
        "score": 0.9,
        "summary": aurora._manifold_coordinate_summary("X", "A", "DIFFERENCE"),
    }


def test_real_manifold_externalization_uses_semantic_ancestry_on_only_local_candidates():
    fitting = _FakeNode("lack", "a gap between what should be present and what is actually carried")
    unrelated = _FakeNode("sparkle", "decorative visual brightness and glitter")
    systems = {
        "_native_meaning": {"law_bindings": [_agentive_difference_binding()]},
        "perception": _LocalPerception([unrelated, fitting]),
        "dimensional": _LocalDimensional(),
    }
    state = _local_manifold_state()
    # A single lexical token is correctly rejected by the existing final surface
    # quality gate; this test exercises the semantic selection stage itself.
    aurora._generate_from_manifold(systems, "novel wording", state)
    trace = systems["_manifold_semantic_resolution"][0]
    assert trace["selected_word"] == "lack"
    assert trace["source"] == "oets_local_semantic_fit"
    assert trace["candidate_count"] == 2
    assert trace["resolution_scope"] == "active_noncomp_subposition"
    assert trace["candidate_noncomp_id"] == "A:DIFFERENCE"
    assert len(trace["semantic_ancestry"]) <= 3


def test_real_manifold_local_semantic_miss_preserves_unresolved_pressure_instead_of_guessing():
    unrelated = _FakeNode("sparkle", "decorative visual brightness and glitter")
    systems = {
        "_native_meaning": {"law_bindings": [_agentive_difference_binding()]},
        "perception": _LocalPerception([unrelated]),
        "dimensional": _LocalDimensional(),
    }
    state = _local_manifold_state()
    aurora._generate_from_manifold(systems, "another novel wording", state)
    trace = systems["_manifold_semantic_resolution"][0]
    assert trace["selected_word"] == ""
    assert trace["source"] == "unresolved_local_semantic_gap"
    assert state.semantic_pressure > 0.5


def test_afterthought_waits_offthread_for_surface_boundary_then_runs_real_deeper_episode():
    calls = []

    class Sim:
        def run_episode(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(episode_id="ep-after-surface")

    systems = {
        "aurora": SimpleNamespace(gateway=SimpleNamespace(simulation=Sim())),
        "ExistenceMode": SimpleNamespace(BOUNDED="bounded"),
        "_current_turn_id": "turn-surface",
        "_live_turn_depth": 1,
    }
    started = time.perf_counter()
    thread = aurora._dispatch_afterthought_subsurface(
        systems, "keep thinking", session_id="s", turn_tick=9,
    )
    assert time.perf_counter() - started < 0.12
    time.sleep(0.03)
    assert calls == []
    systems["_live_turn_depth"] = 0
    thread.join(timeout=1.0)
    assert len(calls) == 1
    assert systems["_last_afterthought_result"]["episode_id"] == "ep-after-surface"


def test_oets_initialization_preserves_lexicons_exact_noncomp_coordinate():
    from aurora_internal.aurora_ontological_scaffolding import OntologicalScaffoldingEngine

    engine = OntologicalScaffoldingEngine()
    entry = SimpleNamespace(
        meaning="a learned semantic relation",
        role="noun",
        emotional_valence=0.0,
        lineage="test",
        noncomp_id="A:DIFFERENCE",
    )
    entries = {"distinctive": entry}
    engine.initialize_from_lexicon(entries)
    assert engine.web.nodes["distinctive"].noncomp_id == "A:DIFFERENCE"
    # Persistence can rehydrate an older coarse coordinate; boot-time
    # reconciliation must restore the exact lexical identity without inference.
    engine.web.nodes["distinctive"].noncomp_id = "X:POLARITY"
    assert engine.reconcile_noncomp_ids_from_lexicon(entries) == 1
    assert engine.web.nodes["distinctive"].noncomp_id == "A:DIFFERENCE"


def test_oets_local_candidate_lookup_uses_existing_node_identity_without_new_api():
    node = _FakeNode("lack", "gap in what is carried")
    node.noncomp_id = "A:DIFFERENCE"
    oets = SimpleNamespace(web=SimpleNamespace(nodes={"lack": node}))
    assert aurora._oets_nodes_for_noncomp(oets, "A:DIFFERENCE") == [node]
    assert aurora._oets_nodes_for_noncomp(oets, "B:DIFFERENCE") == []


def test_learned_one_hop_semantic_relation_can_bridge_nonliteral_wording_locally():
    basis = ["Captures the gap between expected and actual carried state."]
    candidate = _Entry("hesitant", "not yet settled", 0.0)

    relation = SimpleNamespace(strength=0.9, confidence=0.8)
    class Web:
        def get_relation_between(self, a, b):
            if {a, b} == {"hesitant", "gap"}:
                return relation
            return None

    literal = aurora._local_semantic_fit(candidate, basis)
    combined, lexical, relational = aurora._local_semantic_evidence(candidate, basis, Web())
    assert literal == lexical
    assert relational == pytest.approx(0.72)
    assert combined == pytest.approx(0.72)
    assert combined > literal
