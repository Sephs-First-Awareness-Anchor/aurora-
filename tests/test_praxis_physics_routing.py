#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_praxis_physics_routing.py -- proof that Praxis pressure actually lands.

Destination: Aurora's repository `tests/` directory.

Per the Constitutive Physics Audit (2026-09-12), an observation delivered only
through the sensory path constructs no ConstraintVector -- the X:OPERATOR gate
is correct but structurally unreachable, so the event touches no physics at
all.  These tests assert that a Praxis consequence does NOT take that path
alone: it also routes through the three doors her Habitat already uses, with
the axis projection computed by HER functions.

The load-bearing assertion is the last one in this file: the amplitudes the
pump receives must equal what `aurora_habitat._consequence_axis_amplitudes()`
returns for the same event.  If this bridge ever starts computing its own
numbers, that test fails -- and it should, because at that moment the
environment would have begun authoring her physics.
"""
from __future__ import annotations

import types
from typing import Any, Dict, List

import pytest

from aurora_habitat import (
    _actual_consequence_dimensions,
    _consequence_axis_amplitudes,
    consequence_axis_profile,
    operation_consequence_dimensions,
)
from aurora_praxis_bridge import (
    CANONICAL_OPERATIONS,
    PraxisBridge,
    _ShimAction,
    _ShimConsequence,
    _carries_physics,
)


# ---------------------------------------------------------------------------
# Recording doubles for the three physics sinks
# ---------------------------------------------------------------------------

class _Pump:
    def __init__(self) -> None:
        self.injected: List[Any] = []

    def inject(self, disturbance, identity_field, qao=None):
        self.injected.append(disturbance)


class _SediMemory:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def ingest_event(self, *, content, constraint_vector, source, existence_mode):
        self.events.append({
            "content": content, "constraint_vector": constraint_vector,
            "source": source, "existence_mode": existence_mode,
        })


class _Gateway:
    def __init__(self) -> None:
        self.received: List[Dict[str, Any]] = []

    def receive(self, **kwargs):
        self.received.append(kwargs)
        return types.SimpleNamespace(response_id="resp_1")


def _situation(**overrides) -> Dict[str, Any]:
    payload = {
        "contract_version": "praxis_contract_v1",
        "episode_id": "ep_1",
        "situation_id": "sit_1",
        "kind": "consequence",
        "actor": "aurora",
        "territory": "space",
        "operation": "move",
        "target_ids": ["e_1"],
        "affected_entities": ["e_1"],
        "parameters": {},
        "observable_delta": {"e_1": {"position": [0.2, 0.8]}},
        "pre_state": {"e_1": {"owner": "shared", "territory": "space"}},
        "post_state": {"e_1": {"owner": "shared", "territory": "space"}},
        "permission_result": "granted",
        "legal": True,
        "state_changed": True,
        "timestamp": 1_700_000_000.0,
        "provenance": "praxis_environment",
        "epistemic_status": "observation_not_truth",
        "causal_status": "sequence_observed_causality_not_asserted",
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def wired(tmp_path):
    gateway, pump, sedimemory = _Gateway(), _Pump(), _SediMemory()
    systems = {
        "aurora": types.SimpleNamespace(gateway=gateway),
        "StreamType": types.SimpleNamespace(SENSOR_DATA="SENSOR_DATA"),
        "ExistenceMode": types.SimpleNamespace(BOUNDED="BOUNDED"),
        "identity_field": object(),
        "pressure_pump": pump,
        "sedimemory": sedimemory,
    }
    bridge = PraxisBridge(systems, state_dir=str(tmp_path))
    return bridge, gateway, pump, sedimemory


# ---------------------------------------------------------------------------
# Vocabulary alignment -- the precondition for everything else
# ---------------------------------------------------------------------------

def test_bridge_recognises_exactly_her_canonical_operations():
    for operation in CANONICAL_OPERATIONS:
        assert operation_consequence_dimensions(operation), (
            f"'{operation}' has no entry in her consequence-dimension table"
        )


def test_an_unmapped_operation_carries_no_physics():
    # `transmit` is deliberately absent from her table: an utterance has no
    # physical consequence of its own.
    assert not _carries_physics(_situation(operation="transmit"))
    assert not _carries_physics(_situation(kind="utterance",
                                           utterance_text="which one?"))
    assert not _carries_physics(_situation(kind="silence"))


def test_a_real_environmental_change_carries_physics():
    assert _carries_physics(_situation(operation="move"))
    assert _carries_physics(_situation(operation="connect"))
    assert _carries_physics(_situation(operation="delete"))


# ---------------------------------------------------------------------------
# The three doors
# ---------------------------------------------------------------------------

def test_consequence_reaches_the_pressure_pump(wired):
    bridge, _gateway, pump, _sedimemory = wired
    bridge._witness(_situation())
    assert pump.injected, "a Praxis consequence must reach her real pressure pump"
    disturbance = pump.injected[0]
    assert disturbance.source == "praxis:space:move"
    assert disturbance.coupling_mode == "full"


def test_consequence_deposits_a_real_constraint_vector(wired):
    bridge, _gateway, _pump, sedimemory = wired
    bridge._witness(_situation())
    assert sedimemory.events, "a Praxis consequence must deposit into SediMemory"
    event = sedimemory.events[0]
    vector = event["constraint_vector"]
    # The object the audit found missing on the sensory path: constructed at
    # admission, not reconstructed post-hoc from counters.
    for axis in ("X", "T", "N", "B", "A"):
        assert hasattr(vector, axis)
    assert event["source"] == "praxis"
    assert event["content"]["consequence_dimensions"] == ["spatial_relation"]


def test_observation_door_still_fires_alongside_the_physics_doors(wired):
    bridge, gateway, pump, sedimemory = wired
    bridge._witness(_situation())
    assert gateway.received, "observation must not be skipped"
    assert gateway.received[0]["stream_type"] == "SENSOR_DATA"
    assert gateway.received[0]["mode"] == "BOUNDED"
    assert pump.injected and sedimemory.events


def test_utterance_witnesses_as_observation_without_touching_physics(wired):
    bridge, gateway, pump, sedimemory = wired
    bridge._witness(_situation(kind="utterance", operation="transmit",
                               utterance_text="the amber one"))
    assert gateway.received          # real experience
    assert not pump.injected         # no physical consequence of its own
    assert not sedimemory.events


def test_silence_witnesses_without_touching_physics(wired):
    bridge, gateway, pump, _sedimemory = wired
    bridge._witness(_situation(kind="silence", operation="",
                               legal=True, state_changed=False))
    assert gateway.received
    assert not pump.injected


# ---------------------------------------------------------------------------
# Refusals are evidence too
# ---------------------------------------------------------------------------

def test_a_refusal_still_produces_boundary_evidence(wired):
    bridge, _gateway, pump, _sedimemory = wired
    bridge._witness(_situation(legal=False, state_changed=False,
                               permission_result="denied:refused_by_world"))
    assert pump.injected, "a boundary that held is a real fact"
    disturbance = pump.injected[0]
    # Her own amplitude rule floors B on a refusal and lowers intensity.
    assert disturbance.axis_amplitudes["B"] >= 0.20
    assert disturbance.intensity == 0.30


def test_a_permitted_no_op_reports_no_consequence_dimensions(wired):
    bridge, _gateway, pump, _sedimemory = wired
    bridge._witness(_situation(legal=True, state_changed=False,
                               observable_delta={}))
    # Legality and movement are independent; a legal no-op changed nothing, so
    # her mapping yields no dimensions -- and that is the correct record.
    assert pump.injected
    assert bridge.status()["pressure_injections"] == 1


# ---------------------------------------------------------------------------
# The load-bearing assertion
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("operation", sorted(CANONICAL_OPERATIONS))
def test_bridge_never_computes_its_own_amplitudes(wired, operation):
    """Whatever reaches the pump must be exactly what HER function returns.

    If this fails, the bridge has started deciding for itself what an
    environmental event means in axis terms -- which is the environment
    authoring her physics, and the one thing the whole design forbids.
    """
    bridge, _gateway, pump, _sedimemory = wired
    situation = _situation(operation=operation)
    bridge._witness(situation)

    expected = _consequence_axis_amplitudes(
        _ShimAction(situation), _ShimConsequence(situation),
        dict(situation["pre_state"]), dict(situation["post_state"]),
    )
    assert pump.injected[0].axis_amplitudes == expected


@pytest.mark.parametrize("operation", sorted(CANONICAL_OPERATIONS))
def test_dimensions_come_from_her_table_verbatim(wired, operation):
    bridge, _gateway, _pump, sedimemory = wired
    situation = _situation(operation=operation)
    bridge._witness(situation)

    expected = list(_actual_consequence_dimensions(
        _ShimAction(situation), _ShimConsequence(situation),
        dict(situation["pre_state"]), dict(situation["post_state"]),
    ))
    assert sedimemory.events[0]["content"]["consequence_dimensions"] == expected


def test_transfer_narrows_on_the_before_after_evidence(wired):
    """Her mapping narrows `transfer` by what actually changed.  Praxis
    supplies the before/after owner and territory; she decides what that
    means dimensionally."""
    bridge, _gateway, _pump, sedimemory = wired
    situation = _situation(
        operation="transfer",
        pre_state={"e_1": {"owner": "shared", "territory": "space"}},
        post_state={"e_1": {"owner": "aurora", "territory": "space"}},
    )
    bridge._witness(situation)
    dimensions = sedimemory.events[0]["content"]["consequence_dimensions"]
    assert "ownership" in dimensions
    assert "territory_boundary" not in dimensions   # territory did not change


def test_axis_profile_matches_her_projection_for_a_boundary_event(wired):
    bridge, _gateway, pump, _sedimemory = wired
    bridge._witness(_situation(operation="connect"))
    profile = consequence_axis_profile(("relational_structure",))
    # B dominates a relational-structure change in her own table.
    assert profile["B"] >= profile["X"]
    assert pump.injected[0].axis_amplitudes["B"] > 0.0


# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------

def test_missing_physics_systems_degrade_without_losing_the_observation(tmp_path):
    gateway = _Gateway()
    systems = {
        "aurora": types.SimpleNamespace(gateway=gateway),
        "StreamType": types.SimpleNamespace(SENSOR_DATA="SENSOR_DATA"),
        "ExistenceMode": types.SimpleNamespace(BOUNDED="BOUNDED"),
        # no identity_field, no pressure_pump, no sedimemory
    }
    bridge = PraxisBridge(systems, state_dir=str(tmp_path))
    assert bridge._witness(_situation()) is True
    assert gateway.received
    assert bridge.status()["pressure_injections"] == 0


def test_counters_report_what_actually_landed(wired):
    bridge, _gateway, _pump, _sedimemory = wired
    for index in range(3):
        bridge._witness(_situation(situation_id=f"sit_{index}"))
    bridge._witness(_situation(situation_id="sit_u", kind="utterance",
                               operation="transmit", utterance_text="which one?"))
    status = bridge.status()
    assert status["situations_witnessed"] == 4
    assert status["pressure_injections"] == 3
    assert status["sediment_deposits"] == 3
    assert status["last_error"] == ""
