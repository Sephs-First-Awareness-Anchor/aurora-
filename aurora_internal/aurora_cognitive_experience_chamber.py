"""
aurora_cognitive_experience_chamber.py
=======================================

Recursive Causal Experience Chamber (Build 598) -- Stage 1 of 6: World &
Hidden Rule Substrate.

Everything from here to Stage 6 rests on one distinction: a world that
produces consequences Aurora must discover, versus a scenario that
demonstrates a lesson she can imitate. This module builds the former, and
only the former.

No component here may contain a labeled answer that a later stage could
accidentally leak (no field named ``answer``, ``correct_relation``, or
similar) -- the hidden rule is only ever observable through consequence,
never through inspection of world state.

This stage is standalone: it does not wire into ``boot_aurora()``, the live
response pipeline, or any other Aurora system, and it does not evaluate
anything. It is a world, and nothing more.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Bounded, explicit primitive catalog -- mirrors PrimitiveSpec's pattern in
# aurora_internal/aurora_operational_synthesis.py (a small, enumerable set of
# named specs collected into a module-level dict) so early worlds stay small
# enough and legible enough to debug by hand.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PropertySpec:
    name: str
    value_type: str  # "numeric" | "bool" | "enum"
    domain: Optional[Tuple[Any, ...]] = None
    default: Any = None


PROPERTIES: Dict[str, PropertySpec] = {
    "energy": PropertySpec("energy", "numeric", default=0),
    "sealed": PropertySpec("sealed", "bool", default=False),
    "color": PropertySpec("color", "enum", domain=("red", "blue", "green", "neutral"), default="neutral"),
    "charge": PropertySpec("charge", "enum", domain=("positive", "negative", "neutral"), default="neutral"),
    "temperature": PropertySpec("temperature", "numeric", default=0),
}


@dataclass(frozen=True)
class EntityTypeSpec:
    name: str
    properties: Tuple[str, ...]


ENTITY_TYPES: Dict[str, EntityTypeSpec] = {
    "vessel": EntityTypeSpec("vessel", ("energy", "sealed", "color")),
    "conduit": EntityTypeSpec("conduit", ("charge", "sealed")),
    "sensor": EntityTypeSpec("sensor", ("temperature",)),
}


@dataclass(frozen=True)
class RelationTypeSpec:
    name: str
    description: str


RELATION_TYPES: Dict[str, RelationTypeSpec] = {
    "connected_to": RelationTypeSpec("connected_to", "structural adjacency permitting transfer"),
    "adjacent_to": RelationTypeSpec("adjacent_to", "spatial adjacency with no transfer implication"),
}


@dataclass(frozen=True)
class ActionTypeSpec:
    name: str
    arity: int
    description: str


ACTION_TYPES: Dict[str, ActionTypeSpec] = {
    "add_energy": ActionTypeSpec("add_energy", 1, "increase the target's energy by one unit"),
    "remove_energy": ActionTypeSpec("remove_energy", 1, "decrease the target's energy by one unit, floored at zero"),
    "seal": ActionTypeSpec("seal", 1, "seal the target"),
    "unseal": ActionTypeSpec("unseal", 1, "unseal the target"),
    "connect": ActionTypeSpec("connect", 2, "connect two entities"),
    "disconnect": ActionTypeSpec("disconnect", 2, "disconnect two entities"),
    "wait": ActionTypeSpec("wait", 0, "advance one tick with no direct manipulation"),
}

_ACTION_REQUIRED_PROPERTY: Dict[str, str] = {
    "add_energy": "energy",
    "remove_energy": "energy",
    "seal": "sealed",
    "unseal": "sealed",
}


# ---------------------------------------------------------------------------
# World state
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    entity_id: str
    entity_type: str
    properties: Dict[str, Any]


@dataclass(frozen=True)
class Relationship:
    relation_type: str
    source_id: str
    target_id: str


@dataclass(frozen=True)
class ActionInvocation:
    action_type: str
    target_ids: Tuple[str, ...] = ()


@dataclass
class PendingEffect:
    resolve_tick: int
    target_entity_id: str
    target_property: str
    delta: Any


@dataclass
class WorldState:
    tick: int
    entities: Dict[str, Entity]
    relationships: List[Relationship]
    agents: Tuple[str, ...]
    property_history: Dict[Tuple[str, str], List[Tuple[int, Any]]] = field(default_factory=dict)
    pending_effects: List[PendingEffect] = field(default_factory=list)

    def clone(self) -> "WorldState":
        return copy.deepcopy(self)


def _set_property(state: WorldState, entity_id: str, prop: str, value: Any) -> None:
    state.entities[entity_id].properties[prop] = value
    state.property_history.setdefault((entity_id, prop), []).append((state.tick, value))


def _apply_delta(current: Any, delta: Any) -> Any:
    if isinstance(delta, (int, float)) and isinstance(current, (int, float)) and not isinstance(delta, bool):
        return current + delta
    return delta


# ---------------------------------------------------------------------------
# WorldGenerator
# ---------------------------------------------------------------------------

class WorldGenerator:
    """Builds a small typed world from the bounded catalogs above: entities,
    properties, relationships, actions, and state-transition slots. Supports
    multiple agents/viewpoints for later perspective-dependent observation."""

    def __init__(self, rng: Optional[random.Random] = None):
        self._rng = rng if rng is not None else random.Random()

    def build_world(
        self,
        seed: Optional[int] = None,
        num_entities: int = 3,
        agents: Sequence[str] = ("agent_a",),
        entity_types: Optional[Sequence[str]] = None,
        connect_chain: bool = True,
    ) -> WorldState:
        rng = random.Random(seed) if seed is not None else self._rng
        available_types = list(entity_types) if entity_types else list(ENTITY_TYPES)
        if not available_types:
            raise ValueError("no entity types available to build a world")

        entities: Dict[str, Entity] = {}
        property_history: Dict[Tuple[str, str], List[Tuple[int, Any]]] = {}
        counts: Dict[str, int] = {}
        for _ in range(max(num_entities, 2)):
            etype = rng.choice(available_types)
            counts[etype] = counts.get(etype, 0) + 1
            entity_id = f"{etype}_{counts[etype] - 1}"
            spec = ENTITY_TYPES[etype]
            props = {p: PROPERTIES[p].default for p in spec.properties}
            entities[entity_id] = Entity(entity_id=entity_id, entity_type=etype, properties=dict(props))
            for prop_name, value in props.items():
                property_history[(entity_id, prop_name)] = [(0, value)]

        relationships: List[Relationship] = []
        if connect_chain and len(entities) >= 2:
            ids = list(entities.keys())
            for a, b in zip(ids, ids[1:]):
                relationships.append(Relationship("connected_to", a, b))

        return WorldState(
            tick=0,
            entities=entities,
            relationships=relationships,
            agents=tuple(agents),
            property_history=property_history,
        )


# ---------------------------------------------------------------------------
# HiddenRuleEngine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _HiddenRule:
    """Private rule object. Never exposed to any caller outside this module
    except through consequence resolution (HiddenRuleEngine.step())."""
    family: str
    trigger_action: str
    source_entity_id: str
    target_entity_id: str
    target_property: str
    effect_delta: Any
    delay_ticks: int = 0
    source_property: Optional[str] = None
    threshold_value: Optional[float] = None
    threshold_direction: str = "upward"
    condition_entity_id: Optional[str] = None
    condition_property: Optional[str] = None
    condition_value: Any = None
    # A distractor that fires whenever trigger_action occurs, independent of
    # whether the true rule condition holds -- gives worlds a coincidental,
    # non-causal correlation for Stage 3's causal-discrimination scoring.
    decoy_entity_id: Optional[str] = None
    decoy_property: Optional[str] = None
    decoy_delta: Any = 1


def _apply_base_action(state: WorldState, action: ActionInvocation) -> None:
    spec = ACTION_TYPES.get(action.action_type)
    if spec is None:
        raise ValueError(f"unknown action type: {action.action_type!r}")
    if len(action.target_ids) != spec.arity:
        raise ValueError(
            f"action {action.action_type!r} requires {spec.arity} target(s), got {len(action.target_ids)}"
        )
    required_prop = _ACTION_REQUIRED_PROPERTY.get(action.action_type)
    if required_prop and action.target_ids:
        target = state.entities[action.target_ids[0]]
        if required_prop not in target.properties:
            raise ValueError(f"{action.action_type!r} is not applicable to entity type {target.entity_type!r}")

    if action.action_type == "add_energy":
        target = state.entities[action.target_ids[0]]
        _set_property(state, target.entity_id, "energy", _apply_delta(target.properties["energy"], 1))
    elif action.action_type == "remove_energy":
        target = state.entities[action.target_ids[0]]
        new_value = max(0, target.properties["energy"] - 1)
        _set_property(state, target.entity_id, "energy", new_value)
    elif action.action_type == "seal":
        _set_property(state, action.target_ids[0], "sealed", True)
    elif action.action_type == "unseal":
        _set_property(state, action.target_ids[0], "sealed", False)
    elif action.action_type == "connect":
        a, b = action.target_ids
        if not any(r.source_id == a and r.target_id == b and r.relation_type == "connected_to" for r in state.relationships):
            state.relationships.append(Relationship("connected_to", a, b))
    elif action.action_type == "disconnect":
        a, b = action.target_ids
        state.relationships = [
            r for r in state.relationships
            if not (r.source_id == a and r.target_id == b and r.relation_type == "connected_to")
        ]
    elif action.action_type == "wait":
        pass


def _build_rule(world: WorldState, rng: random.Random, family: str) -> _HiddenRule:
    entity_ids = list(world.entities.keys())
    if len(entity_ids) < 2:
        raise ValueError("HiddenRuleEngine requires at least two entities to generate a rule")

    triggerable_actions = [a for a, spec in ACTION_TYPES.items() if spec.arity == 1]
    rng.shuffle(triggerable_actions)
    trigger_action = None
    eligible_sources: List[str] = []
    for candidate in triggerable_actions:
        required_prop = _ACTION_REQUIRED_PROPERTY[candidate]
        matches = [eid for eid, e in world.entities.items() if required_prop in e.properties]
        if matches:
            trigger_action = candidate
            eligible_sources = matches
            break
    if trigger_action is None:
        raise ValueError("world has no entities compatible with any single-target action; cannot generate a rule")

    source_id = rng.choice(eligible_sources)
    remaining = [e for e in entity_ids if e != source_id] or entity_ids
    target_id = rng.choice(remaining)

    numeric_props = [p for p in world.entities[target_id].properties if PROPERTIES[p].value_type == "numeric"]
    other_props = [p for p in world.entities[target_id].properties if PROPERTIES[p].value_type != "numeric"]
    if numeric_props:
        target_property = rng.choice(numeric_props)
        effect_delta: Any = rng.choice([1, 2, -1])
    else:
        target_property = rng.choice(other_props)
        spec = PROPERTIES[target_property]
        if spec.value_type == "enum" and spec.domain:
            current_value = world.entities[target_id].properties[target_property]
            choices = [v for v in spec.domain if v != current_value] or list(spec.domain)
            effect_delta = rng.choice(choices)
        else:
            effect_delta = True

    decoy_candidates = [
        (eid, p) for eid, e in world.entities.items() for p in e.properties
        if PROPERTIES[p].value_type == "numeric" and not (eid == target_id and p == target_property)
    ]
    decoy_entity_id = decoy_property = None
    if decoy_candidates:
        decoy_entity_id, decoy_property = rng.choice(decoy_candidates)

    rule_kwargs: Dict[str, Any] = dict(
        family=family,
        trigger_action=trigger_action,
        source_entity_id=source_id,
        target_entity_id=target_id,
        target_property=target_property,
        effect_delta=effect_delta,
        decoy_entity_id=decoy_entity_id,
        decoy_property=decoy_property,
    )

    if family == "delayed_trigger":
        rule_kwargs["delay_ticks"] = rng.randint(1, 3)
    elif family == "threshold_trigger":
        numeric_owners = [
            eid for eid, e in world.entities.items()
            if any(PROPERTIES[p].value_type == "numeric" for p in e.properties)
        ]
        threshold_source = rng.choice(numeric_owners) if numeric_owners else source_id
        threshold_prop_choices = [p for p in world.entities[threshold_source].properties if PROPERTIES[p].value_type == "numeric"]
        rule_kwargs["source_entity_id"] = threshold_source
        rule_kwargs["source_property"] = rng.choice(threshold_prop_choices) if threshold_prop_choices else None
        rule_kwargs["threshold_value"] = float(rng.randint(2, 4))
        rule_kwargs["threshold_direction"] = "upward"
    elif family == "conditional_on_third_variable":
        third_candidates = [e for e in entity_ids if e not in (source_id, target_id)] or entity_ids
        condition_entity_id = rng.choice(third_candidates)
        condition_props = [
            p for p in world.entities[condition_entity_id].properties if PROPERTIES[p].value_type != "numeric"
        ] or list(world.entities[condition_entity_id].properties)
        condition_property = rng.choice(condition_props)
        spec = PROPERTIES[condition_property]
        if spec.value_type == "enum" and spec.domain:
            condition_value: Any = rng.choice(spec.domain)
        elif spec.value_type == "bool":
            condition_value = True
        else:
            condition_value = spec.default
        rule_kwargs["condition_entity_id"] = condition_entity_id
        rule_kwargs["condition_property"] = condition_property
        rule_kwargs["condition_value"] = condition_value

    return _HiddenRule(**rule_kwargs)


class HiddenRuleEngine:
    """Generates and privately holds the world's governing mechanic. Exposes
    only step(world_state, action) -> world_state: a deterministic
    consequence, never a description of what happened or a field naming the
    relation."""

    RULE_FAMILIES: Tuple[str, ...] = (
        "direct_trigger",
        "delayed_trigger",
        "threshold_trigger",
        "conditional_on_third_variable",
    )

    def __init__(self, rule: _HiddenRule, rng: Optional[random.Random] = None):
        self._rule = rule
        self._rng = rng if rng is not None else random.Random()

    @classmethod
    def generate(
        cls,
        world: WorldState,
        rng: Optional[random.Random] = None,
        family: Optional[str] = None,
    ) -> "HiddenRuleEngine":
        rng = rng if rng is not None else random.Random()
        family = family if family is not None else rng.choice(cls.RULE_FAMILIES)
        if family not in cls.RULE_FAMILIES:
            raise ValueError(f"unknown rule family: {family!r}")
        rule = _build_rule(world, rng, family)
        return cls(rule, rng)

    def step(self, world_state: WorldState, action: ActionInvocation) -> WorldState:
        prior_state = world_state
        new_state = world_state.clone()
        new_state.tick += 1
        _apply_base_action(new_state, action)
        self._apply_decoy(new_state, action)
        self._apply_rule(prior_state, new_state, action)
        self._resolve_pending(new_state)
        return new_state

    def _apply_decoy(self, state: WorldState, action: ActionInvocation) -> None:
        rule = self._rule
        if rule.decoy_entity_id and action.action_type == rule.trigger_action:
            current = state.entities[rule.decoy_entity_id].properties[rule.decoy_property]
            _set_property(state, rule.decoy_entity_id, rule.decoy_property, _apply_delta(current, rule.decoy_delta))

    def _apply_rule(self, prior_state: WorldState, new_state: WorldState, action: ActionInvocation) -> None:
        rule = self._rule
        if rule.family in ("direct_trigger", "delayed_trigger"):
            if action.action_type == rule.trigger_action and rule.source_entity_id in action.target_ids:
                if rule.family == "direct_trigger":
                    self._fire(new_state, rule)
                else:
                    new_state.pending_effects.append(PendingEffect(
                        resolve_tick=new_state.tick + rule.delay_ticks,
                        target_entity_id=rule.target_entity_id,
                        target_property=rule.target_property,
                        delta=rule.effect_delta,
                    ))
        elif rule.family == "threshold_trigger":
            if rule.source_property is None:
                return
            prior_value = prior_state.entities[rule.source_entity_id].properties[rule.source_property]
            new_value = new_state.entities[rule.source_entity_id].properties[rule.source_property]
            if rule.threshold_direction == "upward":
                crossed = prior_value < rule.threshold_value <= new_value
            else:
                crossed = prior_value > rule.threshold_value >= new_value
            if crossed:
                self._fire(new_state, rule)
        elif rule.family == "conditional_on_third_variable":
            if action.action_type == rule.trigger_action and rule.source_entity_id in action.target_ids:
                third_value = new_state.entities[rule.condition_entity_id].properties[rule.condition_property]
                if third_value == rule.condition_value:
                    self._fire(new_state, rule)

    def _fire(self, state: WorldState, rule: _HiddenRule) -> None:
        current = state.entities[rule.target_entity_id].properties[rule.target_property]
        _set_property(state, rule.target_entity_id, rule.target_property, _apply_delta(current, rule.effect_delta))

    def _resolve_pending(self, state: WorldState) -> None:
        still_pending: List[PendingEffect] = []
        for pending in state.pending_effects:
            if pending.resolve_tick <= state.tick:
                current = state.entities[pending.target_entity_id].properties[pending.target_property]
                _set_property(state, pending.target_entity_id, pending.target_property, _apply_delta(current, pending.delta))
            else:
                still_pending.append(pending)
        state.pending_effects = still_pending


# ---------------------------------------------------------------------------
# ObservationBoundary
# ---------------------------------------------------------------------------

_UNKNOWN = object()


def _value_at(state: WorldState, entity_id: str, prop: str, at_tick: int) -> Any:
    if at_tick < 0:
        return _UNKNOWN
    history = state.property_history.get((entity_id, prop))
    if not history:
        return _UNKNOWN
    result = _UNKNOWN
    for tick, value in history:
        if tick <= at_tick:
            result = value
        else:
            break
    return result


@dataclass(frozen=True)
class VisibilityRule:
    """A single scoping rule. None fields mean 'applies regardless of'."""
    agent_id: Optional[str] = None
    entity_id: Optional[str] = None
    property_name: Optional[str] = None
    visible: bool = True
    delay_ticks: int = 0


@dataclass(frozen=True)
class ObservedEntity:
    entity_id: str
    entity_type: str
    properties: Dict[str, Any]


@dataclass(frozen=True)
class ObservedWorldState:
    tick: int
    agent_id: str
    entities: Dict[str, ObservedEntity]
    relationships: Tuple[Relationship, ...]


@dataclass
class ObservationBoundary:
    """Filters full world state down to what an observer is permitted to see
    at a given moment. Supports hidden intermediate state (visible=False),
    delayed visibility (delay_ticks > 0), and perspective-dependent views
    (agent_id-scoped rules)."""
    rules: Tuple[VisibilityRule, ...] = ()

    def _resolve(self, agent_id: str, entity_id: str, property_name: str) -> VisibilityRule:
        best: Optional[VisibilityRule] = None
        best_score = -1
        for rule in self.rules:
            if rule.agent_id is not None and rule.agent_id != agent_id:
                continue
            if rule.entity_id is not None and rule.entity_id != entity_id:
                continue
            if rule.property_name is not None and rule.property_name != property_name:
                continue
            score = int(rule.agent_id is not None) + int(rule.entity_id is not None) + int(rule.property_name is not None)
            if score >= best_score:
                best_score = score
                best = rule
        return best if best is not None else VisibilityRule()

    def observe(self, world_state: WorldState, agent_id: str) -> ObservedWorldState:
        observed_entities: Dict[str, ObservedEntity] = {}
        for entity_id, entity in world_state.entities.items():
            visible_props: Dict[str, Any] = {}
            for prop, value in entity.properties.items():
                rule = self._resolve(agent_id, entity_id, prop)
                if not rule.visible:
                    continue
                if rule.delay_ticks:
                    delayed_value = _value_at(world_state, entity_id, prop, world_state.tick - rule.delay_ticks)
                    if delayed_value is _UNKNOWN:
                        continue
                    value = delayed_value
                visible_props[prop] = value
            observed_entities[entity_id] = ObservedEntity(entity_id, entity.entity_type, visible_props)
        return ObservedWorldState(
            tick=world_state.tick,
            agent_id=agent_id,
            entities=observed_entities,
            relationships=tuple(world_state.relationships),
        )


# ---------------------------------------------------------------------------
# describe_observation() -- manual-testing renderer only. Plain, factual,
# non-leading sentences describing observable state. Never mentions the
# hidden rule, its family, or any relation name.
# ---------------------------------------------------------------------------

_ENTITY_TYPE_LABELS = {"vessel": "Vessel", "conduit": "Conduit", "sensor": "Sensor"}

DENYLIST_TOKENS: Tuple[str, ...] = (
    "rule", "hidden", "trigger", "because", "cause", "causes", "caused",
    "direct_trigger", "delayed_trigger", "threshold_trigger",
    "conditional_on_third_variable", "correlat", "decoy", "mechanic",
    "answer", "correct_relation",
)


def _entity_label(entity: ObservedEntity) -> str:
    prefix = _ENTITY_TYPE_LABELS.get(entity.entity_type, entity.entity_type.capitalize())
    suffix = entity.entity_id.split("_")[-1]
    return f"{prefix} {suffix.upper()}"


def _render_property(label: str, prop: str, value: Any) -> Optional[str]:
    if prop == "energy":
        if value == 0:
            return f"{label} is empty."
        return f"{label} contains {value} energy."
    if prop == "sealed":
        return f"{label} is sealed." if value else f"{label} is unsealed."
    if prop == "color":
        return f"{label} is {value}."
    if prop == "charge":
        return f"{label} carries a {value} charge."
    if prop == "temperature":
        return f"{label} reads {value} temperature."
    return None


def describe_observation(observed: ObservedWorldState) -> str:
    sentences: List[str] = []
    for entity_id in sorted(observed.entities):
        entity = observed.entities[entity_id]
        label = _entity_label(entity)
        for prop in sorted(entity.properties):
            sentence = _render_property(label, prop, entity.properties[prop])
            if sentence:
                sentences.append(sentence)
    for rel in observed.relationships:
        sentences.append(f"{rel.source_id} is {rel.relation_type.replace('_', ' ')} {rel.target_id}.")
    return " ".join(sentences) if sentences else "Nothing is currently observable."
