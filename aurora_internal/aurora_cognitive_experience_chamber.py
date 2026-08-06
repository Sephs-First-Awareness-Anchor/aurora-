"""
aurora_cognitive_experience_chamber.py
=======================================

Recursive Causal Experience Chamber (Build 598).

Stage 1: World & Hidden Rule Substrate. A world that produces consequences
Aurora must discover, versus a scenario that demonstrates a lesson she can
imitate. No component here may contain a labeled answer that a later stage
could accidentally leak (no field named ``answer``, ``correct_relation``, or
similar) -- the hidden rule is only ever observable through consequence,
never through inspection of world state.

Stage 2: Episode Loop & Interpretation Capture. Drives Stage 1's world
through Aurora's real live-response bridge (``aurora._run_simulation_live_
response_bridge``) via ``ActionInterface``, and captures Aurora's stated
position -- pre-consequence -- on ``EpisodeTrace``. The ordering (capture
belief, THEN reveal consequence) is enforced structurally by
``EpisodeTrace.record_consequence()``, not left to caller discipline.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import copy
import hashlib
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from types import SimpleNamespace
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

DENYLIST_TOKENS: Tuple[str, ...] = (
    "rule", "hidden", "trigger", "because", "cause", "causes", "caused",
    "direct_trigger", "delayed_trigger", "threshold_trigger",
    "conditional_on_third_variable", "correlat", "decoy", "mechanic",
    "answer", "correct_relation",
)


@dataclass(frozen=True)
class VocabularySkin:
    """A surface-word mapping layered over the SAME structural catalogs
    (ENTITY_TYPES, PROPERTIES, RELATION_TYPES, ACTION_TYPES) -- the deep
    structure (which rule families can be generated, how actions transform
    state) never changes between skins; only what gets rendered/parsed as
    language does. Stage 4's TransferGenerator uses this to produce a
    surface-disjoint rendering of a structurally identical world."""
    name: str
    entity_type_words: Dict[str, str]
    property_words: Dict[str, str]
    enum_value_words: Dict[str, Dict[str, str]]
    relation_words: Dict[str, str]
    action_words: Dict[str, str]
    action_keywords: Dict[str, Tuple[str, ...]]

    def entity_type_word(self, entity_type: str) -> str:
        return self.entity_type_words.get(entity_type, entity_type.capitalize())

    def property_word(self, prop: str) -> str:
        return self.property_words.get(prop, prop)

    def enum_word(self, prop: str, value: Any) -> str:
        return self.enum_value_words.get(prop, {}).get(value, str(value))

    def relation_word(self, relation_type: str) -> str:
        return self.relation_words.get(relation_type, relation_type.replace("_", " "))

    def action_word(self, action_type: str) -> str:
        return self.action_words.get(action_type, action_type)


_ACTION_VERB_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("add_energy", ("add energy", "increase energy", "give energy", "more energy")),
    ("remove_energy", ("remove energy", "decrease energy", "take energy", "drain energy")),
    ("seal", ("seal ", "seal.")),
    ("unseal", ("unseal ", "unseal.", "open ")),
    ("connect", ("connect ", "connect.")),
    ("disconnect", ("disconnect ", "disconnect.")),
    ("wait", ("wait",)),
)

DEFAULT_SKIN = VocabularySkin(
    name="default",
    entity_type_words={"vessel": "Vessel", "conduit": "Conduit", "sensor": "Sensor"},
    property_words={"energy": "energy", "sealed": "sealed", "color": "color", "charge": "charge", "temperature": "temperature"},
    enum_value_words={
        "color": {"red": "red", "blue": "blue", "green": "green", "neutral": "neutral"},
        "charge": {"positive": "positive", "negative": "negative", "neutral": "neutral"},
    },
    relation_words={"connected_to": "connected to", "adjacent_to": "adjacent to"},
    action_words={
        "add_energy": "add energy to", "remove_energy": "remove energy from",
        "seal": "seal", "unseal": "unseal", "connect": "connect", "disconnect": "disconnect", "wait": "wait",
    },
    action_keywords=dict(_ACTION_VERB_PATTERNS),
)

# Structurally identical to DEFAULT_SKIN (same entity types, same property
# roles, same rule-family generation, same action semantics) but with zero
# shared surface vocabulary -- entity/property/enum/relation/action words are
# all disjoint from DEFAULT_SKIN's. This is what makes a transfer case a test
# of structure rather than a re-run of the same scenery (Stage 4).
ALT_SKIN = VocabularySkin(
    name="alt",
    entity_type_words={"vessel": "Canister", "conduit": "Pipeline", "sensor": "Gauge"},
    property_words={"energy": "voltage", "sealed": "latched", "color": "hue", "charge": "polarity", "temperature": "reading"},
    enum_value_words={
        "color": {"red": "crimson", "blue": "azure", "green": "verdant", "neutral": "plain"},
        "charge": {"positive": "forward", "negative": "reverse", "neutral": "idle"},
    },
    relation_words={"connected_to": "linked to", "adjacent_to": "beside"},
    action_words={
        "add_energy": "add voltage to", "remove_energy": "remove voltage from",
        "seal": "latch", "unseal": "unlatch", "connect": "link", "disconnect": "unlink", "wait": "pause",
    },
    action_keywords={
        "add_energy": ("add voltage", "increase voltage", "give voltage", "more voltage"),
        "remove_energy": ("remove voltage", "decrease voltage", "take voltage", "drain voltage"),
        "seal": ("latch ", "latch."),
        "unseal": ("unlatch ", "unlatch.", "release "),
        "connect": ("link ", "link."),
        "disconnect": ("unlink ", "unlink."),
        "wait": ("pause",),
    },
)


def _entity_label(entity: ObservedEntity, skin: VocabularySkin = DEFAULT_SKIN) -> str:
    prefix = skin.entity_type_word(entity.entity_type)
    suffix = entity.entity_id.split("_")[-1]
    return f"{prefix} {suffix.upper()}"


def _render_property(label: str, prop: str, value: Any, skin: VocabularySkin = DEFAULT_SKIN) -> Optional[str]:
    word = skin.property_word(prop)
    if prop == "energy":
        if value == 0:
            return f"{label} is empty."
        return f"{label} contains {value} {word}."
    if prop == "sealed":
        return f"{label} is {word}." if value else f"{label} is un{word}."
    if prop == "color":
        return f"{label} is {skin.enum_word(prop, value)}."
    if prop == "charge":
        return f"{label} carries a {skin.enum_word(prop, value)} {word}."
    if prop == "temperature":
        return f"{label} reads {value} {word}."
    return None


def describe_observation(observed: ObservedWorldState, skin: VocabularySkin = DEFAULT_SKIN) -> str:
    sentences: List[str] = []
    for entity_id in sorted(observed.entities):
        entity = observed.entities[entity_id]
        label = _entity_label(entity, skin)
        for prop in sorted(entity.properties):
            sentence = _render_property(label, prop, entity.properties[prop], skin)
            if sentence:
                sentences.append(sentence)
    for rel in observed.relationships:
        if rel.source_id not in observed.entities or rel.target_id not in observed.entities:
            continue
        source_label = _entity_label(observed.entities[rel.source_id], skin)
        target_label = _entity_label(observed.entities[rel.target_id], skin)
        sentences.append(f"{source_label} is {skin.relation_word(rel.relation_type)} {target_label}.")
    return " ".join(sentences) if sentences else "Nothing is currently observable."


# ---------------------------------------------------------------------------
# Stage 2: Episode Loop & Interpretation Capture
# ---------------------------------------------------------------------------

@dataclass
class CapturedInterpretation:
    """Aurora's stated position on a turn, captured BEFORE the world reveals
    a consequence. Parsed from the same process_external_user_turn() result
    the live bridge already returns (resp_A.content, resp_A.confidence) --
    entity/relation/prediction extraction is a bounded lookup against Stage
    1's own enumerable vocabulary, not a second parser guessing at open text."""
    raw_expression: str
    identified_entities: Tuple[str, ...] = ()
    believed_relations: Tuple[Tuple[str, str, str], ...] = ()
    predicted_consequence: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    evidence_cited: Tuple[str, ...] = ()
    stated_unknowns: Tuple[str, ...] = ()


_UNKNOWN_MARKERS: Tuple[str, ...] = (
    "not sure", "unsure", "don't know", "do not know", "unclear",
    "uncertain", "no idea", "unknown",
)

_CHANGE_MARKERS: Tuple[Tuple[str, str], ...] = (
    ("increase", "increase"), ("rise", "increase"), ("go up", "increase"),
    ("gain", "increase"), ("more", "increase"), ("higher", "increase"),
    ("decrease", "decrease"), ("fall", "decrease"), ("go down", "decrease"),
    ("lose", "decrease"), ("less", "decrease"), ("lower", "decrease"),
    ("become", "change"), ("change", "change"), ("turn", "change"), ("flip", "change"),
)
# _ACTION_VERB_PATTERNS is defined earlier alongside DEFAULT_SKIN (it backs
# DEFAULT_SKIN.action_keywords) -- not redefined here.


@dataclass(frozen=True)
class InterpretedAction:
    action: "ActionInvocation"
    intent: str  # "act" | "predict" | "ask"
    interpretation: CapturedInterpretation


def _label_to_entity_id(observed: ObservedWorldState, skin: VocabularySkin = DEFAULT_SKIN) -> Dict[str, str]:
    return {_entity_label(entity, skin).lower(): entity_id for entity_id, entity in observed.entities.items()}


def _phrase_for_action(
    name: str, targets: Tuple[str, ...], observed: ObservedWorldState, skin: VocabularySkin = DEFAULT_SKIN
) -> str:
    labels = [_entity_label(observed.entities[t], skin) for t in targets]
    verb = skin.action_word(name)
    if name in ("add_energy", "remove_energy", "seal", "unseal"):
        return f"{verb} {labels[0]}"
    if name in ("connect", "disconnect"):
        return f"{verb} {labels[0]} and {labels[1]}"
    return verb


class ActionInterface:
    """Translates the world's available actions into a prompt/question form
    suitable for aurora._run_simulation_live_response_bridge(), and
    translates Aurora's returned expression back into a structured action
    selection (or predict/ask intent) the world can consume. Reuses
    describe_observation() as the observation-to-text step -- this is not a
    second natural-language renderer."""

    @staticmethod
    def available_actions(observed: ObservedWorldState) -> List[Tuple[str, Tuple[str, ...]]]:
        actions: List[Tuple[str, Tuple[str, ...]]] = []
        visible_ids = list(observed.entities)
        for entity_id in visible_ids:
            props = observed.entities[entity_id].properties
            for action_name, required_prop in _ACTION_REQUIRED_PROPERTY.items():
                if required_prop in props:
                    actions.append((action_name, (entity_id,)))
        connected_pairs = {(rel.source_id, rel.target_id) for rel in observed.relationships}
        for a in visible_ids:
            for b in visible_ids:
                if a == b:
                    continue
                actions.append(("disconnect", (a, b)) if (a, b) in connected_pairs else ("connect", (a, b)))
        actions.append(("wait", ()))
        return actions

    @staticmethod
    def build_prompt(observed: ObservedWorldState, max_actions: int = 8, skin: VocabularySkin = DEFAULT_SKIN) -> str:
        observation_text = describe_observation(observed, skin)
        options = ActionInterface.available_actions(observed)[:max_actions]
        option_phrases = [_phrase_for_action(name, targets, observed, skin) for name, targets in options]
        options_text = ("Available actions: " + "; ".join(option_phrases) + ".") if option_phrases else ""
        ask = (
            "Choose one action, state what you predict will happen as a result, "
            "and say how confident you are. Note anything you are unsure about."
        )
        return " ".join(part for part in (observation_text, options_text, ask) if part)

    @staticmethod
    def interpret_expression(
        expression: str, observed: ObservedWorldState, confidence: float, skin: VocabularySkin = DEFAULT_SKIN
    ) -> InterpretedAction:
        text = str(expression or "")
        lowered = text.lower()
        label_to_id = _label_to_entity_id(observed, skin)

        identified_entities = tuple(sorted(
            entity_id for label, entity_id in label_to_id.items() if label and label in lowered
        ))
        believed_relations = tuple(
            (rel.source_id, rel.relation_type, rel.target_id)
            for rel in observed.relationships
            if _entity_label(observed.entities[rel.source_id], skin).lower() in lowered
            and _entity_label(observed.entities[rel.target_id], skin).lower() in lowered
        )

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        evidence_cited = tuple(
            s for s in sentences
            if any(label in s.lower() for label in label_to_id if label)
            or any(skin.property_word(prop).lower() in s.lower() for prop in PROPERTIES)
        )
        stated_unknowns = tuple(s for s in sentences if any(marker in s.lower() for marker in _UNKNOWN_MARKERS))

        predicted_consequence: Optional[Dict[str, Any]] = None
        for label, entity_id in label_to_id.items():
            if not label or label not in lowered:
                continue
            for prop_name in observed.entities[entity_id].properties:
                if skin.property_word(prop_name).lower() not in lowered:
                    continue
                for marker, direction in _CHANGE_MARKERS:
                    if marker in lowered:
                        predicted_consequence = {"entity_id": entity_id, "property": prop_name, "direction": direction}
                        break
                if predicted_consequence:
                    break
            if predicted_consequence:
                break

        interpretation = CapturedInterpretation(
            raw_expression=text,
            identified_entities=identified_entities,
            believed_relations=believed_relations,
            predicted_consequence=predicted_consequence,
            confidence=confidence,
            evidence_cited=evidence_cited,
            stated_unknowns=stated_unknowns,
        )

        action_type = next((name for name, patterns in skin.action_keywords.items() if any(p in lowered for p in patterns)), None)
        target_entity_id = identified_entities[0] if identified_entities else None

        intent = "act"
        if action_type is None:
            intent = "ask" if "?" in text else "predict"
            action = ActionInvocation("wait", ())
        else:
            spec = ACTION_TYPES[action_type]
            if spec.arity == 0:
                action = ActionInvocation(action_type, ())
            elif spec.arity == 1:
                required_prop = _ACTION_REQUIRED_PROPERTY.get(action_type)
                candidate = None
                if target_entity_id is not None:
                    obs_entity = observed.entities.get(target_entity_id)
                    if obs_entity is not None and required_prop in obs_entity.properties:
                        candidate = target_entity_id
                if candidate is None:
                    candidate = next(
                        (eid for eid, e in observed.entities.items() if required_prop in e.properties),
                        None,
                    )
                if candidate is None:
                    intent = "predict"
                    action = ActionInvocation("wait", ())
                else:
                    action = ActionInvocation(action_type, (candidate,))
            else:
                two = list(identified_entities[:2])
                if len(two) < 2:
                    two = list(observed.entities)[:2]
                if len(two) < 2:
                    intent = "predict"
                    action = ActionInvocation("wait", ())
                else:
                    action = ActionInvocation(action_type, tuple(two))

        return InterpretedAction(action=action, intent=intent, interpretation=interpretation)


# ---------------------------------------------------------------------------
# EpisodeTrace
# ---------------------------------------------------------------------------

@dataclass
class EpisodeStep:
    tick: int
    observation_text: str
    action: ActionInvocation
    intent: str
    interpretation: CapturedInterpretation
    consequence: Optional[WorldState] = None
    # Extension points for later stages -- kept generic so Stage 3/4/5 extend
    # this record rather than restructuring it.
    causal_scores: Optional[Dict[str, float]] = None       # Stage 3
    backprojection: Optional[Dict[str, Any]] = None        # Stage 3
    counterfactual_branch_ids: Tuple[str, ...] = ()        # Stage 4
    dual_strata_snapshot: Optional[Dict[str, Any]] = None  # Stage 5 -- captured pre-articulation
    expression_fidelity: Optional[Dict[str, Any]] = None   # Stage 5 -- evaluator's scoring output
    # Build 608 (C): the full ground-truth world state and what was actually
    # observable through the boundary, both AS OF the moment interpretation
    # was captured -- reusable structured evidence for synthesis, not
    # re-derivable from consequence alone once the episode has moved on.
    world_before: Optional[WorldState] = None
    observed_before: Optional[ObservedWorldState] = None


@dataclass
class EpisodeTrace:
    """Every later stage reads from and writes to this object: Stage 3
    appends consequence/backprojection scoring, Stage 4 appends
    counterfactual/transfer branches, Stage 5 appends expression-fidelity
    comparisons, Stage 6 consumes the whole trace for promotion."""
    episode_id: str
    world_seed: Optional[int]
    rule_family: str  # internal bookkeeping only -- never surfaced to Aurora
    agent_id: str
    steps: List[EpisodeStep] = field(default_factory=list)
    terminal_state: Optional[WorldState] = None
    _interpretation_pending: bool = field(default=False, repr=False)

    def record_interpretation(
        self,
        tick: int,
        observation_text: str,
        action: ActionInvocation,
        intent: str,
        interpretation: CapturedInterpretation,
    ) -> None:
        self.steps.append(EpisodeStep(
            tick=tick,
            observation_text=observation_text,
            action=action,
            intent=intent,
            interpretation=interpretation,
        ))
        self._interpretation_pending = True

    def record_consequence(self, consequence: WorldState) -> None:
        # The ordering (capture belief, THEN reveal consequence) is enforced
        # here structurally -- not left to caller discipline.
        if not self._interpretation_pending or not self.steps:
            raise RuntimeError(
                "EpisodeTrace.record_consequence() called with no interpretation "
                "captured for the current turn -- call record_interpretation() first"
            )
        self.steps[-1].consequence = consequence
        self._interpretation_pending = False

    def close(self, terminal_state: WorldState) -> None:
        self.terminal_state = terminal_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "world_seed": self.world_seed,
            "rule_family": self.rule_family,
            "agent_id": self.agent_id,
            "steps": [_episode_step_to_dict(step) for step in self.steps],
            "terminal_state": _worldstate_to_dict(self.terminal_state) if self.terminal_state is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodeTrace":
        trace = cls(
            episode_id=str(data.get("episode_id", "")),
            world_seed=data.get("world_seed"),
            rule_family=str(data.get("rule_family", "")),
            agent_id=str(data.get("agent_id", "")),
        )
        trace.steps = [_episode_step_from_dict(s) for s in data.get("steps", []) or []]
        terminal = data.get("terminal_state")
        trace.terminal_state = _worldstate_from_dict(terminal) if terminal is not None else None
        return trace


def _worldstate_to_dict(state: WorldState) -> Dict[str, Any]:
    return {
        "tick": state.tick,
        "entities": {eid: asdict(e) for eid, e in state.entities.items()},
        "relationships": [asdict(r) for r in state.relationships],
        "agents": list(state.agents),
        "property_history": [[list(key), [list(pair) for pair in value]] for key, value in state.property_history.items()],
        "pending_effects": [asdict(p) for p in state.pending_effects],
    }


def _worldstate_from_dict(data: Dict[str, Any]) -> WorldState:
    entities = {eid: Entity(**e) for eid, e in data.get("entities", {}).items()}
    relationships = [Relationship(**r) for r in data.get("relationships", [])]
    property_history = {
        tuple(key): [tuple(pair) for pair in value]
        for key, value in data.get("property_history", [])
    }
    pending_effects = [PendingEffect(**p) for p in data.get("pending_effects", [])]
    return WorldState(
        tick=int(data.get("tick", 0)),
        entities=entities,
        relationships=relationships,
        agents=tuple(data.get("agents", ())),
        property_history=property_history,
        pending_effects=pending_effects,
    )


def _observed_worldstate_to_dict(observed: ObservedWorldState) -> Dict[str, Any]:
    return {
        "tick": observed.tick,
        "agent_id": observed.agent_id,
        "entities": {eid: asdict(e) for eid, e in observed.entities.items()},
        "relationships": [asdict(r) for r in observed.relationships],
    }


def _observed_worldstate_from_dict(data: Dict[str, Any]) -> ObservedWorldState:
    entities = {eid: ObservedEntity(**e) for eid, e in data.get("entities", {}).items()}
    relationships = tuple(Relationship(**r) for r in data.get("relationships", []))
    return ObservedWorldState(
        tick=int(data.get("tick", 0)),
        agent_id=str(data.get("agent_id", "")),
        entities=entities,
        relationships=relationships,
    )


def _episode_step_to_dict(step: EpisodeStep) -> Dict[str, Any]:
    return {
        "tick": step.tick,
        "observation_text": step.observation_text,
        "action": asdict(step.action),
        "intent": step.intent,
        "interpretation": asdict(step.interpretation),
        "consequence": _worldstate_to_dict(step.consequence) if step.consequence is not None else None,
        "causal_scores": step.causal_scores,
        "backprojection": step.backprojection,
        "counterfactual_branch_ids": list(step.counterfactual_branch_ids),
        "dual_strata_snapshot": step.dual_strata_snapshot,
        "expression_fidelity": step.expression_fidelity,
        "world_before": _worldstate_to_dict(step.world_before) if step.world_before is not None else None,
        "observed_before": _observed_worldstate_to_dict(step.observed_before) if step.observed_before is not None else None,
    }


def _episode_step_from_dict(data: Dict[str, Any]) -> EpisodeStep:
    action_data = dict(data.get("action", {}) or {})
    action = ActionInvocation(
        action_type=str(action_data.get("action_type", "wait")),
        target_ids=tuple(action_data.get("target_ids", ()) or ()),
    )
    interp_data = dict(data.get("interpretation", {}) or {})
    interpretation = CapturedInterpretation(
        raw_expression=str(interp_data.get("raw_expression", "")),
        identified_entities=tuple(interp_data.get("identified_entities", ()) or ()),
        believed_relations=tuple(tuple(r) for r in (interp_data.get("believed_relations", ()) or ())),
        predicted_consequence=interp_data.get("predicted_consequence"),
        confidence=float(interp_data.get("confidence", 0.0) or 0.0),
        evidence_cited=tuple(interp_data.get("evidence_cited", ()) or ()),
        stated_unknowns=tuple(interp_data.get("stated_unknowns", ()) or ()),
    )
    consequence_data = data.get("consequence")
    return EpisodeStep(
        tick=int(data.get("tick", 0)),
        observation_text=str(data.get("observation_text", "")),
        action=action,
        intent=str(data.get("intent", "predict")),
        interpretation=interpretation,
        consequence=_worldstate_from_dict(consequence_data) if consequence_data is not None else None,
        causal_scores=data.get("causal_scores"),
        backprojection=data.get("backprojection"),
        counterfactual_branch_ids=tuple(data.get("counterfactual_branch_ids", ()) or ()),
        dual_strata_snapshot=data.get("dual_strata_snapshot"),
        expression_fidelity=data.get("expression_fidelity"),
        world_before=_worldstate_from_dict(data["world_before"]) if data.get("world_before") is not None else None,
        observed_before=_observed_worldstate_from_dict(data["observed_before"]) if data.get("observed_before") is not None else None,
    )


# ---------------------------------------------------------------------------
# Episode loop driver -- reuses aurora._build_simulation_live_bridge_context()
# / aurora._run_simulation_live_response_bridge() rather than building a
# second pipeline-routing mechanism. Imported lazily so this module stays
# importable (e.g. for pure world-substrate use) without pulling in Aurora's
# full boot dependency chain.
# ---------------------------------------------------------------------------

def build_episode_runtime_context(systems: Dict[str, Any]) -> Dict[str, Any]:
    import aurora as _aurora
    return _aurora._build_simulation_live_bridge_context(systems)


def read_cers_verdict_detail(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Read-only pull of the FULL CERSVerdict (not just the surface-
    compressed subset aurora.py's own _read_cers_salience() exposes to the
    live surface -- this evaluator is a different, offline consumer,
    explicitly chartered by Stage 5 to read intervention_label/
    geometry_deviation/confirmed_potential_benefits for fidelity scoring,
    where the live surface's "compressed signal, not full explanation" rule
    does not apply). Reuses aurora.py's own cers_detail.json read path;
    never writes, never touches CERS's decision logic."""
    import aurora as _aurora

    state_dir = _aurora._dual_strata_state_dir(systems)
    detail = _aurora._read_dual_strata_json(state_dir / "cers_detail.json", {})
    if not isinstance(detail, dict):
        return {}
    return dict(detail.get("cers_verdict") or {})


def capture_dual_strata_snapshot(systems: Dict[str, Any], bridge_result: Dict[str, Any]) -> Dict[str, Any]:
    """Merges the bridge's own additive dual_strata_snapshot (semantic_
    salience/semantic_hesitation/variant_confidence/semantic_mode/
    response_bias, already computed this turn) with a read-only pull of the
    fuller CERSVerdict fields (intervention_label, geometry_deviation,
    confirmed_potential_benefits) for the same turn. A read, never a
    mutation -- CERSBridge's live behavior for real turns is untouched."""
    snapshot = dict(bridge_result.get("dual_strata_snapshot") or {})
    verdict = read_cers_verdict_detail(systems)
    snapshot["intervention_label"] = verdict.get("intervention_label")
    snapshot["geometry_deviation"] = verdict.get("geometry_deviation")
    snapshot["confirmed_potential_benefits"] = dict(verdict.get("confirmed_potential_benefits") or {})
    return snapshot


def run_episode_step(
    trace: EpisodeTrace,
    systems: Dict[str, Any],
    episode_runtime_context: Dict[str, Any],
    world_state: WorldState,
    rule_engine: HiddenRuleEngine,
    boundary: ObservationBoundary,
    agent_id: str,
    skin: VocabularySkin = DEFAULT_SKIN,
) -> WorldState:
    """Drive one turn of an episode through Aurora's real live-response
    bridge. Enforces capture-then-consequence structurally: interpretation is
    recorded before HiddenRuleEngine.step() is ever called. skin defaults to
    DEFAULT_SKIN; Stage 4's TransferGenerator passes ALT_SKIN so the same
    world structure is rendered/parsed through disjoint surface vocabulary."""
    import aurora as _aurora

    observed = boundary.observe(world_state, agent_id)
    prompt_text = ActionInterface.build_prompt(observed, skin=skin)

    selected = SimpleNamespace(primary_concept=SimpleNamespace(value="cognitive_experience_chamber"))
    context = {"prompt": prompt_text, "category": "cognitive_experience_chamber"}

    bridge_result = _aurora._run_simulation_live_response_bridge(
        systems,
        selected=selected,
        context=context,
        mode=None,
        runtime_context=episode_runtime_context,
    )
    expression = str(bridge_result.get("expression", "") or "")
    confidence = float((bridge_result.get("meta", {}) or {}).get("confidence", 0.0) or 0.0)

    interpreted = ActionInterface.interpret_expression(expression, observed, confidence, skin=skin)

    trace.record_interpretation(
        tick=world_state.tick,
        observation_text=prompt_text,
        action=interpreted.action,
        intent=interpreted.intent,
        interpretation=interpreted.interpretation,
    )
    # Stage 5: retain the pre-articulation snapshot from THIS SAME turn,
    # captured alongside the interpretation rather than re-derived later.
    trace.steps[-1].dual_strata_snapshot = capture_dual_strata_snapshot(systems, bridge_result)
    # Build 608 (C): retain the ground-truth and observed state AS OF this
    # same moment -- reusable structured evidence, not re-derivable once the
    # episode has moved past this tick.
    trace.steps[-1].world_before = world_state.clone()
    trace.steps[-1].observed_before = observed

    new_state = rule_engine.step(world_state, interpreted.action)
    trace.record_consequence(new_state)
    return new_state


# ---------------------------------------------------------------------------
# Stage 3: Causal Evaluator & Backprojection
# ---------------------------------------------------------------------------
#
# Traced and confirmed against the live avatar system: SimulatedAvatar.
# react() scores clarity from sentence-count/word-count ratio, tone from
# presence of literal tokens ('feel', 'yes', 'and', 'I'), and
# _behavior_adjustment()/_dimension_pressure_adjustment() reward the literal
# tokens "however", "maybe", "earlier" as if their presence demonstrated
# contradiction-handling, uncertainty calibration, and temporal continuity.
# That system stays exactly as-is for its own purpose -- social and
# expressive pressure. CausalEvaluator below must NOT inherit this pattern:
# nothing here may score a response by the presence of any lexical marker.
# Every dimension below reads ONLY structured fields already captured on
# CapturedInterpretation (identified_entities, believed_relations,
# predicted_consequence) and world state -- never interpretation.raw_expression.

CAUSAL_DIMENSION_NAMES: Tuple[str, ...] = (
    "causal_state_accuracy",
    "causal_prediction_accuracy",
    "causal_discrimination",
    "evidence_discipline",
    "revision_quality",
    "counterfactual_consistency",  # Stage 4
    "transfer",                    # Stage 4 -- cross-episode, not on CausalEvaluationResult; see TransferComparison
    "confidence_calibration",      # Stage 5
)


def _relation_holds(world: WorldState, source_id: str, relation_type: str, target_id: str) -> bool:
    return any(
        r.source_id == source_id and r.relation_type == relation_type and r.target_id == target_id
        for r in world.relationships
    )


def _direction_of_change(before: Any, after: Any) -> str:
    if before == after:
        return "no_change"
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return "increase" if after > before else "decrease"
    return "change"


@dataclass(frozen=True)
class CausalEvaluationResult:
    """Independent scores, one per turn. No blended fitness number -- the
    original proposal's objection to one number standing in for all of them
    applies here directly. None means the dimension was not applicable to
    this turn (e.g. no prediction was made), not that it scored zero.
    ``transfer`` is deliberately not a field here -- it compares two whole
    episodes, not one turn; see TransferComparison / compute_transfer_
    comparison() below."""
    state_accuracy: Optional[float]
    prediction_accuracy: Optional[float]
    causal_discrimination: Optional[float]
    evidence_discipline: Optional[float]
    revision_quality: Optional[float]
    counterfactual_consistency: Optional[float] = None
    confidence_calibration: Optional[float] = None

    def as_dimension_scores(self) -> Dict[str, float]:
        mapping = {
            "causal_state_accuracy": self.state_accuracy,
            "causal_prediction_accuracy": self.prediction_accuracy,
            "causal_discrimination": self.causal_discrimination,
            "evidence_discipline": self.evidence_discipline,
            "revision_quality": self.revision_quality,
            "counterfactual_consistency": self.counterfactual_consistency,
            "confidence_calibration": self.confidence_calibration,
        }
        return {name: score for name, score in mapping.items() if score is not None}


class CausalEvaluator:
    """Scores exclusively from comparing captured interpretation against
    actual world state/consequence, never from surface features of the
    expression."""

    @staticmethod
    def state_accuracy(interpretation: CapturedInterpretation, world_before: WorldState) -> float:
        if not interpretation.believed_relations:
            return 1.0 if interpretation.identified_entities else 0.5
        correct = sum(
            1 for (source_id, relation_type, target_id) in interpretation.believed_relations
            if _relation_holds(world_before, source_id, relation_type, target_id)
        )
        return correct / len(interpretation.believed_relations)

    @staticmethod
    def prediction_accuracy(
        interpretation: CapturedInterpretation, world_before: WorldState, consequence: WorldState
    ) -> Optional[float]:
        pred = interpretation.predicted_consequence
        if pred is None:
            return None
        entity_id, prop, direction = pred.get("entity_id"), pred.get("property"), pred.get("direction")
        before_entity = world_before.entities.get(entity_id)
        after_entity = consequence.entities.get(entity_id)
        if before_entity is None or after_entity is None or prop not in before_entity.properties:
            return 0.0
        actual_direction = _direction_of_change(before_entity.properties.get(prop), after_entity.properties.get(prop))
        return 1.0 if actual_direction == direction else 0.0

    @staticmethod
    def causal_discrimination(interpretation: CapturedInterpretation, engine: "HiddenRuleEngine") -> Optional[float]:
        rule = engine._rule
        pred = interpretation.predicted_consequence
        if pred is None or rule.decoy_entity_id is None:
            return None
        predicted_decoy = pred.get("entity_id") == rule.decoy_entity_id and pred.get("property") == rule.decoy_property
        predicted_true_target = pred.get("entity_id") == rule.target_entity_id and pred.get("property") == rule.target_property
        if predicted_true_target and not predicted_decoy:
            return 1.0
        if predicted_decoy and not predicted_true_target:
            return 0.0
        return 0.5

    @staticmethod
    def evidence_discipline(interpretation: CapturedInterpretation, observed_before: ObservedWorldState) -> float:
        visible_entities = set(observed_before.entities)
        total = 0
        unsupported = 0
        for entity_id in interpretation.identified_entities:
            total += 1
            if entity_id not in visible_entities:
                unsupported += 1
        for source_id, _relation_type, target_id in interpretation.believed_relations:
            total += 1
            if source_id not in visible_entities or target_id not in visible_entities:
                unsupported += 1
        if interpretation.predicted_consequence is not None:
            total += 1
            entity_id = interpretation.predicted_consequence.get("entity_id")
            prop = interpretation.predicted_consequence.get("property")
            obs_entity = observed_before.entities.get(entity_id)
            if obs_entity is None or prop not in obs_entity.properties:
                unsupported += 1
        if total == 0:
            return 1.0
        return 1.0 - (unsupported / total)

    @staticmethod
    def revision_accuracy_delta(
        original: CapturedInterpretation,
        revised: Optional[CapturedInterpretation],
        world_before: WorldState,
        consequence: WorldState,
    ) -> Optional[float]:
        """The raw measurement Build 608 (B) asks for: revised_accuracy -
        original_accuracy, in [-1, 1]. None when there is nothing to
        measure -- no revision, or either side's prediction_accuracy isn't
        itself measurable (no prediction made)."""
        if revised is None:
            return None
        original_score = CausalEvaluator.prediction_accuracy(original, world_before, consequence)
        if original_score is None:
            return None
        revised_score = CausalEvaluator.prediction_accuracy(revised, world_before, consequence)
        if revised_score is None:
            return None
        return revised_score - original_score

    @staticmethod
    def revision_quality(
        original: CapturedInterpretation,
        revised: Optional[CapturedInterpretation],
        world_before: WorldState,
        consequence: WorldState,
    ) -> Optional[float]:
        """Measures revised accuracy - original accuracy (via
        revision_accuracy_delta), rescaled to [0, 1] for the same
        threshold-based gating convention every other dimension uses here
        (delta=0 -> 0.5, delta=+1 -> 1.0, delta=-1 -> 0.0) -- NOT merely
        whether the parsed structure changed. Not applicable (None) when the
        original prediction was already correct: there is nothing to
        correct, and that is immediate-understanding territory, not
        successful-correction territory (see determine_admissibility_route()
        below)."""
        original_score = CausalEvaluator.prediction_accuracy(original, world_before, consequence)
        if original_score is None or original_score >= 1.0:
            return None
        delta = CausalEvaluator.revision_accuracy_delta(original, revised, world_before, consequence)
        if delta is None:
            return None
        return max(0.0, min(1.0, (delta + 1.0) / 2.0))

    @staticmethod
    def counterfactual_consistency(
        interpretation: CapturedInterpretation, branch: "CounterfactualBranch"
    ) -> Optional[float]:
        """Does Aurora's stated causal claim (the original interpretation or
        its revision) correctly predict the counterfactual branch's outcome,
        or does it only fit the one sequence she already saw? Reuses
        prediction_accuracy's exact logic against the branch's own
        before/after states -- the same static prediction template is simply
        tested against a world where one variable was altered."""
        if branch.consequence is None:
            return None
        return CausalEvaluator.prediction_accuracy(interpretation, branch.world_before, branch.consequence)

    @staticmethod
    def confidence_calibration(
        interpretation: CapturedInterpretation, dual_strata_snapshot: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """Does expressed certainty (interpretation.confidence, i.e. resp_A.
        confidence -- an already-existing field, not re-derived) track
        internal confidence (the pre-articulation semantic_salience CERS
        already computed)? A pure numeric comparison, not a lexical check."""
        if not dual_strata_snapshot:
            return None
        internal_confidence = dual_strata_snapshot.get("semantic_salience")
        if internal_confidence is None:
            return None
        gap = abs(float(interpretation.confidence) - float(internal_confidence))
        return max(0.0, 1.0 - gap)

    @classmethod
    def evaluate(
        cls,
        interpretation: CapturedInterpretation,
        world_before: WorldState,
        consequence: WorldState,
        observed_before: ObservedWorldState,
        engine: "HiddenRuleEngine",
        revised_interpretation: Optional[CapturedInterpretation] = None,
        counterfactual_branch: Optional["CounterfactualBranch"] = None,
        dual_strata_snapshot: Optional[Dict[str, Any]] = None,
    ) -> CausalEvaluationResult:
        prediction_score = cls.prediction_accuracy(interpretation, world_before, consequence)
        counterfactual_score = (
            cls.counterfactual_consistency(revised_interpretation or interpretation, counterfactual_branch)
            if counterfactual_branch is not None
            else None
        )
        return CausalEvaluationResult(
            state_accuracy=cls.state_accuracy(interpretation, world_before),
            prediction_accuracy=prediction_score,
            causal_discrimination=cls.causal_discrimination(interpretation, engine),
            evidence_discipline=cls.evidence_discipline(interpretation, observed_before),
            revision_quality=cls.revision_quality(interpretation, revised_interpretation, world_before, consequence),
            counterfactual_consistency=counterfactual_score,
            confidence_calibration=cls.confidence_calibration(interpretation, dual_strata_snapshot),
        )

    @staticmethod
    def record_fail_dimensions(
        dream_trainer: Any,
        result: CausalEvaluationResult,
        *,
        threshold: float = 0.5,
        example: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Feeds genuine failures (real scored episodes, never scripted ones)
        into DreamTrainer._record_fail_dimension() using the same call
        pattern already used for semantic_precision/coherence_maintenance --
        not a new mechanism."""
        if dream_trainer is None or not hasattr(dream_trainer, "_record_fail_dimension"):
            return []
        recorded: List[str] = []
        for name, score in result.as_dimension_scores().items():
            if score < threshold:
                dream_trainer._record_fail_dimension(name, 1.0 - score, example=example)
                recorded.append(name)
        return recorded


def apply_causal_evaluation(
    trace: EpisodeTrace,
    step_index: int,
    world_before: WorldState,
    engine: HiddenRuleEngine,
    boundary: ObservationBoundary,
    agent_id: str,
    revised_interpretation: Optional[CapturedInterpretation] = None,
    dream_trainer: Any = None,
    counterfactual_branch: Optional["CounterfactualBranch"] = None,
) -> CausalEvaluationResult:
    step = trace.steps[step_index]
    if step.consequence is None:
        raise RuntimeError("apply_causal_evaluation() requires a step whose consequence has already been recorded")
    observed_before = boundary.observe(world_before, agent_id)
    result = CausalEvaluator.evaluate(
        step.interpretation,
        world_before,
        step.consequence,
        observed_before,
        engine,
        revised_interpretation=revised_interpretation,
        counterfactual_branch=counterfactual_branch,
        dual_strata_snapshot=step.dual_strata_snapshot,
    )
    step.causal_scores = result.as_dimension_scores()
    if counterfactual_branch is not None:
        step.counterfactual_branch_ids = step.counterfactual_branch_ids + (counterfactual_branch.branch_id,)
    if dream_trainer is not None:
        CausalEvaluator.record_fail_dimensions(
            dream_trainer,
            result,
            example={"episode_id": trace.episode_id, "tick": step.tick, "intent": step.intent},
        )
    return result


def run_backprojection_step(
    trace: EpisodeTrace,
    systems: Dict[str, Any],
    episode_runtime_context: Dict[str, Any],
    step_index: int,
    boundary: ObservationBoundary,
    agent_id: str,
    skin: VocabularySkin = DEFAULT_SKIN,
) -> CapturedInterpretation:
    """Aurora revisits -- does not re-answer -- the original captured
    interpretation. Presents the consequence and asks her to reconcile it
    with what she believed, through the same live-response bridge."""
    import aurora as _aurora

    step = trace.steps[step_index]
    if step.consequence is None:
        raise RuntimeError("run_backprojection_step() requires a step whose consequence has already been recorded")

    observed_after = boundary.observe(step.consequence, agent_id)
    reconciliation_prompt = (
        f"Earlier you observed: {step.observation_text} "
        f"Now: {describe_observation(observed_after, skin)} "
        "Given what actually happened, revisit what you believed. Does it still "
        "hold, or has your understanding changed? Explain your revised "
        "understanding, including anything you would predict differently now."
    )

    selected = SimpleNamespace(primary_concept=SimpleNamespace(value="cognitive_experience_chamber_backprojection"))
    context = {"prompt": reconciliation_prompt, "category": "cognitive_experience_chamber"}
    bridge_result = _aurora._run_simulation_live_response_bridge(
        systems,
        selected=selected,
        context=context,
        mode=None,
        runtime_context=episode_runtime_context,
    )
    expression = str(bridge_result.get("expression", "") or "")
    confidence = float((bridge_result.get("meta", {}) or {}).get("confidence", 0.0) or 0.0)

    revised = ActionInterface.interpret_expression(expression, observed_after, confidence, skin=skin).interpretation

    step.backprojection = {
        "original_interpretation": asdict(step.interpretation),
        "reconciliation_prompt": reconciliation_prompt,
        "revised_interpretation": asdict(revised),
    }
    return revised


# ---------------------------------------------------------------------------
# Stage 4: Counterfactual Branching & Transfer Generation
# ---------------------------------------------------------------------------

@dataclass
class CounterfactualBranch:
    branch_id: str
    parent_branch_id: str
    decision_tick: int
    altered_variable: Dict[str, Any]  # {"entity_id":..., "property":..., "value":...}
    world_before: WorldState
    action: ActionInvocation
    consequence: Optional[WorldState] = None


class CounterfactualBrancher:
    """Given a canonical world state at a chosen decision point, clones it
    and alters exactly one variable, then runs the cloned branch through
    HiddenRuleEngine.step() independently. Tracks branches in a parent ->
    children structure mirroring InceptionEntity's _entity_tree PATTERN
    (aurora_simulation_engine.py:1294's spawn_entity()/collapse_entity()) --
    not its I-state/emotional-cascade content model, which has no bearing
    here. Branches are keyed and traceable but fully discardable without
    corrupting the canonical trace."""

    def __init__(self) -> None:
        self.branches: Dict[str, CounterfactualBranch] = {}
        self._branch_tree: Dict[str, List[str]] = defaultdict(list)

    def spawn_branch(
        self,
        canonical_world_before: WorldState,
        action: ActionInvocation,
        engine: HiddenRuleEngine,
        alter: Dict[str, Any],
        parent_branch_id: str = "canonical",
    ) -> CounterfactualBranch:
        entity_id = alter["entity_id"]
        prop = alter["property"]
        new_value = alter["value"]
        if entity_id not in canonical_world_before.entities or prop not in canonical_world_before.entities[entity_id].properties:
            raise ValueError(f"cannot alter unknown entity/property: {entity_id}.{prop}")

        branched_world = canonical_world_before.clone()
        _set_property(branched_world, entity_id, prop, new_value)

        branch_id = f"branch_{len(self.branches)}_{entity_id}_{prop}"
        branch = CounterfactualBranch(
            branch_id=branch_id,
            parent_branch_id=parent_branch_id,
            decision_tick=canonical_world_before.tick,
            altered_variable={"entity_id": entity_id, "property": prop, "value": new_value},
            world_before=branched_world,
            action=action,
        )
        branch.consequence = engine.step(branched_world, action)

        self.branches[branch_id] = branch
        self._branch_tree[parent_branch_id].append(branch_id)
        return branch

    def children_of(self, branch_id: str) -> Tuple[str, ...]:
        return tuple(self._branch_tree.get(branch_id, ()))

    def discard_branch(self, branch_id: str) -> None:
        """Collapses a branch and everything spawned from it, recursively --
        mirrors InceptionEntity.collapse_entity()'s children-first recursion.
        Discarding never touches the canonical world state or trace; branches
        live only in self.branches/self._branch_tree."""
        for child_id in list(self._branch_tree.get(branch_id, ())):
            self.discard_branch(child_id)
        branch = self.branches.get(branch_id)
        if branch is not None:
            siblings = self._branch_tree.get(branch.parent_branch_id)
            if siblings is not None and branch_id in siblings:
                siblings.remove(branch_id)
        self.branches.pop(branch_id, None)
        self._branch_tree.pop(branch_id, None)


@dataclass(frozen=True)
class TransferComparison:
    """Compares performance on an original episode against a surface-varied
    transfer case built from the same rule family. Records the delta
    explicitly per shared dimension, not just the transfer case's raw
    scores -- a large drop is the direct signal that structure was not
    actually learned, only the one scenario's scenery."""
    original_scores: Dict[str, float]
    transfer_scores: Dict[str, float]
    deltas: Dict[str, float]
    transfer_score: Optional[float]


def compute_transfer_comparison(
    original_scores: Dict[str, float], transfer_scores: Dict[str, float]
) -> TransferComparison:
    shared = sorted(set(original_scores) & set(transfer_scores))
    deltas = {dim: round(transfer_scores[dim] - original_scores[dim], 6) for dim in shared}
    transfer_score = None
    if shared:
        transfer_score = max(0.0, 1.0 - (sum(abs(d) for d in deltas.values()) / len(deltas)))
    return TransferComparison(
        original_scores=dict(original_scores),
        transfer_scores=dict(transfer_scores),
        deltas=deltas,
        transfer_score=transfer_score,
    )


def record_transfer_fail(
    dream_trainer: Any,
    comparison: TransferComparison,
    *,
    threshold: float = 0.5,
    example: Optional[Dict[str, Any]] = None,
) -> bool:
    """Feeds a genuine transfer collapse into DreamTrainer._record_fail_
    dimension() under the 'transfer' dimension name -- same call pattern as
    CausalEvaluator.record_fail_dimensions(), applied to the one dimension
    that spans two episodes instead of one turn."""
    if dream_trainer is None or not hasattr(dream_trainer, "_record_fail_dimension"):
        return False
    if comparison.transfer_score is None or comparison.transfer_score >= threshold:
        return False
    dream_trainer._record_fail_dimension("transfer", 1.0 - comparison.transfer_score, example=example)
    return True


_TOKEN_PATTERN = re.compile(r"[a-z]+")
_SURFACE_TOKEN_STOPWORDS: frozenset = frozenset({
    "is", "a", "the", "and", "to", "of", "in", "from", "with", "an", "carries",
    "reads", "contains", "empty", "nothing", "currently", "observable",
})


def surface_content_tokens(text: str) -> "set[str]":
    """Content-word tokens for a zero-overlap check between two renderings --
    excludes short/grammatical filler so the comparison is about nouns, not
    English function words every render necessarily shares."""
    return {
        token for token in _TOKEN_PATTERN.findall(text.lower())
        if len(token) >= 4 and token not in _SURFACE_TOKEN_STOPWORDS
    }


class TransferGenerator:
    """Given a completed episode's rule family (not its specific rule
    instance), generates a structurally equivalent world with no shared
    nouns, entity labels, or phrasing. Reuses Stage 1's WorldGenerator with a
    fresh seed constrained to the same rule family -- a fresh seed alone
    would still share DEFAULT_SKIN's vocabulary, so the world is driven
    through ALT_SKIN throughout (rendering AND parsing) to make the surface
    genuinely disjoint while the deep structure -- same entity/property
    catalogs, same rule-family generation, same action semantics -- repeats
    exactly."""

    @staticmethod
    def generate_transfer_world(
        rule_family: str,
        seed: int,
        num_entities: int = 3,
        entity_types: Optional[Sequence[str]] = None,
    ) -> Tuple[WorldState, HiddenRuleEngine]:
        world = WorldGenerator().build_world(
            seed=seed,
            num_entities=num_entities,
            entity_types=entity_types or tuple(ENTITY_TYPES),
            connect_chain=False,
        )
        engine = HiddenRuleEngine.generate(world, rng=random.Random(seed), family=rule_family)
        return world, engine

    @staticmethod
    def confirm_zero_surface_overlap(original_render: str, transfer_render: str) -> bool:
        return not (surface_content_tokens(original_render) & surface_content_tokens(transfer_render))


# ---------------------------------------------------------------------------
# Stage 5: Expression Fidelity Bridge
# ---------------------------------------------------------------------------
#
# CERSBridge.build_snapshot() already produces a DualStrataSnapshot carrying
# a CERSVerdict (semantic_salience, semantic_hesitation, intervention_label,
# geometry_deviation, confirmed_potential_benefits, ...) computed BEFORE
# articulation, per the bridge's own documented call-order comment. This
# section reads that already-computed, pre-expression structured state --
# capture_dual_strata_snapshot() above -- and compares it against the
# eventual spoken output. It does not invent an internal-conclusion
# representation and does not modify CERS's own decision logic in any way.
#
# Every check below compares presence/absence/direction of a SPECIFIC
# internal signal against structured fields Stage 2 already captured
# (CapturedInterpretation.stated_unknowns, .predicted_consequence,
# .identified_entities, .confidence) -- never a new keyword scan invented
# for this stage, and never a word-count/surface-fluency heuristic.

class ExpressionFidelityEvaluator:
    """Compares captured internal state against the final articulated
    expression. Must not penalize stylistic variation -- it compares
    presence/absence/direction of specific internal signals against the
    expressed text, not a second surface-feature scorer."""

    @staticmethod
    def hesitation_fidelity(
        dual_strata_snapshot: Optional[Dict[str, Any]], interpretation: CapturedInterpretation
    ) -> Optional[float]:
        """Does semantic_hesitation (internal) correspond to actual hedging
        language in the expression -- and, critically, the reverse: does
        confident-sounding expression exist despite high internal
        hesitation? 'Hedging language present' reuses Stage 2's own
        stated_unknowns capture; this is not a new lexical scan."""
        if not dual_strata_snapshot or "semantic_hesitation" not in dual_strata_snapshot:
            return None
        internal_hesitation = bool(dual_strata_snapshot.get("semantic_hesitation"))
        expressed_hedging = bool(interpretation.stated_unknowns)
        return 1.0 if internal_hesitation == expressed_hedging else 0.0

    @staticmethod
    def intervention_fidelity(
        dual_strata_snapshot: Optional[Dict[str, Any]], interpretation: CapturedInterpretation
    ) -> Optional[float]:
        """Does intervention_label/geometry_deviation, when present, show up
        as a genuine reconsideration in the expressed text, or does the
        expression proceed as if the internal deviation never registered?
        'Reconsideration expressed' reuses the same stated_unknowns signal
        hesitation_fidelity uses -- both are the structured record of
        uncertainty actually surfacing in what was said."""
        if not dual_strata_snapshot:
            return None
        geometry_deviation = dual_strata_snapshot.get("geometry_deviation")
        intervention_registered = bool(dual_strata_snapshot.get("intervention_label")) or bool(geometry_deviation)
        if not intervention_registered:
            return None  # nothing internally flagged this turn -- not applicable
        reconsideration_expressed = bool(interpretation.stated_unknowns)
        return 1.0 if reconsideration_expressed else 0.0

    @staticmethod
    def causal_claim_preservation(
        original: CapturedInterpretation, revised: Optional[CapturedInterpretation]
    ) -> Optional[float]:
        """Does the causal claim scored in Stage 3 appear, preserved, in the
        expressed text across backprojection -- not paraphrase-perfect, but
        not contradicted or silently dropped either?"""
        if original.predicted_consequence is None or revised is None:
            return None
        claim_key = (original.predicted_consequence.get("entity_id"), original.predicted_consequence.get("property"))
        if revised.predicted_consequence is not None:
            revised_key = (revised.predicted_consequence.get("entity_id"), revised.predicted_consequence.get("property"))
            if revised_key == claim_key:
                return 1.0  # addressed -- same claim revisited, confirmed or revised
        if original.predicted_consequence.get("entity_id") in revised.identified_entities:
            return 0.5  # the entity is still referenced, but the claim itself was not re-addressed
        return 0.0  # silently dropped

    @staticmethod
    def classify_fidelity_quadrant(internal_correct: bool, expression_hedged: bool) -> str:
        """The four fidelity quadrants from the original proposal. When
        internal belief was correct, hedging when there was no need to is
        the miscalibration ('wrong expression'); when internal belief was
        wrong, fluent/confident phrasing is the failure-hidden-by-language
        case, while hedging is at least honestly flagged."""
        if internal_correct and not expression_hedged:
            return "correct_internal_correct_expression"
        if internal_correct and expression_hedged:
            return "correct_internal_wrong_expression"
        if not internal_correct and not expression_hedged:
            return "wrong_internal_fluent_expression"
        return "wrong_internal_honest_expression"

    @classmethod
    def evaluate(
        cls,
        dual_strata_snapshot: Optional[Dict[str, Any]],
        interpretation: CapturedInterpretation,
        revised_interpretation: Optional[CapturedInterpretation] = None,
        internal_correct: Optional[bool] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "hesitation_fidelity": cls.hesitation_fidelity(dual_strata_snapshot, interpretation),
            "intervention_fidelity": cls.intervention_fidelity(dual_strata_snapshot, interpretation),
            "causal_claim_preservation": cls.causal_claim_preservation(interpretation, revised_interpretation),
        }
        if internal_correct is not None:
            result["quadrant"] = cls.classify_fidelity_quadrant(
                internal_correct=internal_correct,
                expression_hedged=bool(interpretation.stated_unknowns),
            )
        return result


def apply_expression_fidelity_evaluation(
    trace: EpisodeTrace,
    step_index: int,
    revised_interpretation: Optional[CapturedInterpretation] = None,
) -> Dict[str, Any]:
    step = trace.steps[step_index]
    internal_correct: Optional[bool] = None
    if step.causal_scores is not None:
        internal_correct = step.causal_scores.get("causal_prediction_accuracy") == 1.0 \
            if "causal_prediction_accuracy" in step.causal_scores else None
    result = ExpressionFidelityEvaluator.evaluate(
        step.dual_strata_snapshot,
        step.interpretation,
        revised_interpretation=revised_interpretation,
        internal_correct=internal_correct,
    )
    step.expression_fidelity = result
    return result


# ---------------------------------------------------------------------------
# Stage 6: Developmental Promotion Bridge, Governors & Shadow Persistence
# ---------------------------------------------------------------------------
#
# This is the closing stage -- everything built in Stages 1-5 stays
# quarantined and inert until this stage's gates let it through. Nothing
# here bypasses AuroraOperationalSynthesisChamber._score_trial()'s existing
# perfect-training-AND-validation gate; this module only decides whether a
# scored episode is even worth submitting through the real
# submit_operational_experience() seam. The chamber's own WARP trial
# machinery still has the final word on promotion, exactly as it does for
# every other caller of that seam.

@dataclass(frozen=True)
class GovernorResult:
    name: str
    tripped: bool
    reason: str
    detail: Dict[str, Any] = field(default_factory=dict)


def _trend(values: Sequence[float], window: int = 5) -> float:
    """Mirrors TimeDilationGovernor.get_fitness_trend()'s exact formula
    (aurora_simulation_engine.py) -- reused, not reinvented. Returns 0.0
    (no signal) until at least `window` samples have accumulated."""
    if len(values) < window:
        return 0.0
    recent = list(values)[-window:]
    return (recent[-1] - recent[0]) / len(recent)


class ContradictionTracker:
    """Mirrors SynthesisTask.conflict_count's exact pattern
    (aurora_operational_synthesis.py): a plain int counter, incremented via
    stable comparison of contradictory evidence for the same input across
    recent episodes, used as a hard gate rather than a weighted penalty."""

    def __init__(self) -> None:
        self._seen: Dict[str, Any] = {}
        self.conflict_count = 0

    def record(self, input_key: str, output_value: Any) -> bool:
        """Returns True if this observation contradicted a prior one for
        the same input_key."""
        if input_key in self._seen and self._seen[input_key] != output_value:
            self.conflict_count += 1
            return True
        self._seen[input_key] = output_value
        return False


class DevelopmentalGovernors:
    """Pre-submission circuit breakers. Each is independently checkable and
    independently loggable. Any governor tripping halts promotion for that
    episode and routes it to DreamTrainer._record_fail_dimension() and
    autonomy.add_study_topic() instead -- a tripped governor is data, not a
    discarded run. Governors whose required context was not supplied report
    tripped=False with an explicit not-applicable reason, rather than being
    silently skipped."""

    @staticmethod
    def contradiction_accumulation(tracker: ContradictionTracker, threshold: int = 1) -> GovernorResult:
        tripped = tracker.conflict_count >= threshold
        return GovernorResult(
            "contradiction_accumulation", tripped,
            f"conflict_count={tracker.conflict_count} threshold={threshold}",
            {"conflict_count": tracker.conflict_count, "threshold": threshold},
        )

    @staticmethod
    def confidence_rising_accuracy_falling(
        confidence_calibration_history: Optional[Sequence[float]],
        accuracy_history: Optional[Sequence[float]],
        window: int = 5,
    ) -> GovernorResult:
        if not confidence_calibration_history or not accuracy_history:
            return GovernorResult("confidence_rising_accuracy_falling", False, "not_applicable_missing_context", {})
        confidence_trend = _trend(confidence_calibration_history, window)
        accuracy_trend = _trend(accuracy_history, window)
        tripped = confidence_trend > 0 and accuracy_trend < 0
        return GovernorResult(
            "confidence_rising_accuracy_falling", tripped,
            f"confidence_trend={confidence_trend:.4f} accuracy_trend={accuracy_trend:.4f}",
            {"confidence_trend": confidence_trend, "accuracy_trend": accuracy_trend},
        )

    @staticmethod
    def surface_fitness_without_transfer(
        avatar_fitness_trend: Optional[float], transfer_score_trend: Optional[float]
    ) -> GovernorResult:
        """The single most load-bearing check in the six-stage program: reads
        SimulatedAvatar's own already-computed fitness trend (session.
        governor.get_fitness_trend(), aurora_simulation_engine.py's
        TimeDilationGovernor -- not a second tracker) against Stage 4's
        transfer-score trend, and halts when surface fitness rises while
        transfer worsens. The direct test of whether the 'hall of mirrors'
        failure mode is actually prevented in practice."""
        if avatar_fitness_trend is None or transfer_score_trend is None:
            return GovernorResult("surface_fitness_without_transfer", False, "not_applicable_missing_context", {})
        tripped = avatar_fitness_trend > 0 and transfer_score_trend < 0
        return GovernorResult(
            "surface_fitness_without_transfer", tripped,
            f"avatar_fitness_trend={avatar_fitness_trend:.4f} transfer_score_trend={transfer_score_trend:.4f}",
            {"avatar_fitness_trend": avatar_fitness_trend, "transfer_score_trend": transfer_score_trend},
        )

    @staticmethod
    def loss_of_stable_ability(
        genealogy: Any, ability_tag: Optional[str], regression_evidence_passed: Optional[bool]
    ) -> GovernorResult:
        """Regression against previously promoted _register_genealogy()
        entries -- reads genealogy.abilities directly (the same store
        register_emergent_operational_synthesis() writes to), filtered by
        the same effect_tags vocabulary that promotion already uses, rather
        than inventing new bookkeeping."""
        if genealogy is None or ability_tag is None or regression_evidence_passed is None:
            return GovernorResult("loss_of_stable_ability", False, "not_applicable_missing_context", {})
        abilities = getattr(genealogy, "abilities", {}) or {}
        previously_promoted = any(
            ability_tag in getattr(ability, "effect_tags", ()) for ability in abilities.values()
        )
        tripped = previously_promoted and not regression_evidence_passed
        return GovernorResult(
            "loss_of_stable_ability", tripped,
            f"previously_promoted={previously_promoted} regression_evidence_passed={regression_evidence_passed}",
            {"ability_tag": ability_tag, "previously_promoted": previously_promoted},
        )

    @staticmethod
    def runaway_complexity(tree: Optional[Dict[str, Any]]) -> GovernorResult:
        """Reuses aurora_operational_synthesis.py's own _MAX_PROGRAM_NODES/
        _node_count() ceiling rather than a new limit. Only applicable once
        a candidate program tree exists (formed inside the operational
        synthesis chamber after enough examples accumulate) -- a single
        freshly-submitted episode has no tree yet, and that is reported
        honestly as not-applicable rather than silently passing."""
        if tree is None:
            return GovernorResult("runaway_complexity", False, "not_applicable_no_candidate_tree_yet", {})
        from aurora_internal.aurora_operational_synthesis import _MAX_PROGRAM_NODES, _node_count
        count = _node_count(tree)
        tripped = count > _MAX_PROGRAM_NODES
        return GovernorResult(
            "runaway_complexity", tripped,
            f"node_count={count} max={_MAX_PROGRAM_NODES}",
            {"node_count": count, "max_nodes": _MAX_PROGRAM_NODES},
        )

    @staticmethod
    def meaning_expression_divergence(
        expression_fidelity: Optional[Dict[str, Any]], threshold: float = 0.5
    ) -> GovernorResult:
        """Stage 5's fidelity score falling below threshold halts promotion
        regardless of how well Stages 3-4 scored."""
        if not expression_fidelity:
            return GovernorResult("meaning_expression_divergence", False, "not_applicable_no_fidelity_data", {})
        low_scores = {
            k: v for k, v in expression_fidelity.items()
            if isinstance(v, (int, float)) and v < threshold
        }
        tripped = bool(low_scores)
        return GovernorResult(
            "meaning_expression_divergence", tripped,
            f"low_scores={low_scores}" if tripped else "within threshold",
            {"low_scores": low_scores, "threshold": threshold},
        )


def route_tripped_governors_to_fail_pressure(
    dream_trainer: Any,
    autonomy: Any,
    tripped: Sequence[GovernorResult],
    episode_id: str,
) -> None:
    """A tripped governor is data, not a discarded run: same
    _record_fail_dimension() call pattern already used elsewhere in this
    module, plus autonomy.add_study_topic() so the halted episode becomes a
    curiosity target rather than silently vanishing."""
    if dream_trainer is not None and hasattr(dream_trainer, "_record_fail_dimension"):
        for governor in tripped:
            dream_trainer._record_fail_dimension(
                governor.name, 1.0, example={"episode_id": episode_id, "halted_by": "developmental_governor", "reason": governor.reason},
            )
    if autonomy is not None and hasattr(autonomy, "add_study_topic"):
        names = ",".join(g.name for g in tripped)
        autonomy.add_study_topic(f"recursive_causal_experience_chamber:{episode_id}:{names}")


_PROMOTION_TRANSFER_THRESHOLD = 0.8

# Build 608 (B): two legitimate success paths. Dimensions common to both;
# each route additionally requires either a correct ORIGINAL prediction
# (immediate_understanding) or a genuinely improving REVISION
# (successful_correction) -- never both, and revision_quality is simply not
# a meaningful concept when nothing needed correcting.
_SHARED_ROUTE_DIMENSIONS: Dict[str, float] = {
    "causal_state_accuracy": 1.0,
    "causal_discrimination": 1.0,
    "evidence_discipline": 1.0,
    "counterfactual_consistency": 1.0,
    "confidence_calibration": 0.8,
}
_ROUTE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "immediate_understanding": {**_SHARED_ROUTE_DIMENSIONS, "causal_prediction_accuracy": 1.0},
    "successful_correction": {**_SHARED_ROUTE_DIMENSIONS, "revision_quality": 1.0},
}


def determine_admissibility_route(dimension_scores: Dict[str, float]) -> Optional[str]:
    """Build 608 (B). immediate_understanding: the original prediction was
    already correct -- revision_quality is not applicable and not required.
    successful_correction: the original prediction was wrong but the
    backprojected revision corrected it -- revision_quality (revised_
    accuracy - original_accuracy, rescaled) must show genuine improvement.
    Returns None if this episode's evidence doesn't meet either route's
    precondition (e.g. still wrong after revision, or no prediction ever
    made at all)."""
    prediction_accuracy = dimension_scores.get("causal_prediction_accuracy")
    if prediction_accuracy is not None and prediction_accuracy >= 1.0:
        return "immediate_understanding"
    if dimension_scores.get("revision_quality") is not None:
        return "successful_correction"
    return None


# Build 608 (C): the narrow target operation for this first chamber --
# observed state + chosen action -> resulting state delta. ONE stable task
# id shared across every episode of a given rule family, not a fresh task
# per episode, so submit_operational_experience()'s underlying WARP task
# can actually accumulate the training/validation examples _score_trial()
# requires (_MIN_TRAINING_EXAMPLES etc., aurora_operational_synthesis.py) --
# a unique per-episode task_id could never reach that bar.
def rcec_primary_task_id(rule_family: str) -> str:
    return f"RCEC:observed_state_plus_action_to_state_delta:{rule_family}"


def compute_state_delta(world_before: WorldState, consequence: WorldState) -> Dict[str, Dict[str, Any]]:
    """{'entity_id.property': {'before':..., 'after':...}} for every
    property that actually changed -- the resulting state delta, not the
    full raw consequence state."""
    delta: Dict[str, Dict[str, Any]] = {}
    for entity_id, entity in consequence.entities.items():
        before_entity = world_before.entities.get(entity_id)
        if before_entity is None:
            continue
        for prop, after_value in entity.properties.items():
            before_value = before_entity.properties.get(prop)
            if before_value != after_value:
                delta[f"{entity_id}.{prop}"] = {"before": before_value, "after": after_value}
    return delta


def build_operation_evidence(step: EpisodeStep) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """(input_value, expected_output) shaped for observe_example(): observed
    state + chosen action -> resulting state delta. None if the step lacks
    the structured before-state evidence needed (world_before/observed_
    before/consequence) -- e.g. an episode scored without ever reaching
    run_episode_step()'s live capture."""
    if step.observed_before is None or step.world_before is None or step.consequence is None:
        return None
    input_value = {
        "observed_state": _observed_worldstate_to_dict(step.observed_before),
        "action": asdict(step.action),
    }
    expected_output = compute_state_delta(step.world_before, step.consequence)
    return input_value, expected_output


@dataclass(frozen=True)
class PromotionDecision:
    episode_id: str
    promoted: bool
    reason: str
    tripped: Tuple[str, ...] = ()
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    transfer_score: Optional[float] = None
    submission_result: Optional[Dict[str, Any]] = None
    route: Optional[str] = None


class DevelopmentalPromotionBridge:
    """Takes a completed, scored EpisodeStep and, only when it qualifies for
    one of the two legitimate admissibility routes (Build 608, B) AND a
    supplied transfer case also clears its threshold, submits structured
    observed-state+action -> state-delta evidence to submit_operational_
    experience() under one stable, shared task id per rule family (Build
    608, C). This is the ONLY path from this chamber into the operational
    synthesis chamber's promotion pipeline."""

    def __init__(
        self,
        route_thresholds: Optional[Dict[str, Dict[str, float]]] = None,
        transfer_threshold: float = _PROMOTION_TRANSFER_THRESHOLD,
    ) -> None:
        self.route_thresholds = {
            route: dict(thresholds) for route, thresholds in (route_thresholds or _ROUTE_THRESHOLDS).items()
        }
        self.transfer_threshold = transfer_threshold

    def clears_dimension_thresholds(
        self, dimension_scores: Dict[str, float]
    ) -> Tuple[bool, List[str], Optional[str]]:
        route = determine_admissibility_route(dimension_scores)
        if route is None:
            return (False, [], None)
        required = self.route_thresholds.get(route, {})
        missing_or_low = [
            dim for dim, threshold in required.items()
            if dimension_scores.get(dim) is None or dimension_scores[dim] < threshold
        ]
        return (not missing_or_low, missing_or_low, route)

    def evaluate_and_submit(
        self,
        systems: Dict[str, Any],
        step: EpisodeStep,
        transfer_comparison: Optional[TransferComparison],
        governor_results: Sequence[GovernorResult],
        *,
        dream_trainer: Any = None,
        autonomy: Any = None,
        episode_id: str = "",
        validation: bool = False,
        rule_family: str = "",
    ) -> PromotionDecision:
        dimension_scores = dict(step.causal_scores or {})

        tripped = [g for g in governor_results if g.tripped]
        if tripped:
            route_tripped_governors_to_fail_pressure(dream_trainer, autonomy, tripped, episode_id)
            return PromotionDecision(episode_id, False, "governor_tripped", tuple(g.name for g in tripped), dimension_scores)

        cleared, missing, route = self.clears_dimension_thresholds(dimension_scores)
        if route is None:
            if dream_trainer is not None and hasattr(dream_trainer, "_record_fail_dimension"):
                dream_trainer._record_fail_dimension("causal_prediction_accuracy", 1.0, example={"episode_id": episode_id, "halted_by": "promotion_bridge", "reason": "no_admissible_route"})
            if autonomy is not None and hasattr(autonomy, "add_study_topic"):
                autonomy.add_study_topic(f"recursive_causal_experience_chamber:{episode_id}:no_admissible_route")
            return PromotionDecision(episode_id, False, "no_admissible_route", (), dimension_scores)

        transfer_score = transfer_comparison.transfer_score if transfer_comparison is not None else None
        transfer_cleared = transfer_score is not None and transfer_score >= self.transfer_threshold

        if not cleared or not transfer_cleared:
            failing = list(missing) + ([] if transfer_cleared else ["transfer"])
            if dream_trainer is not None and hasattr(dream_trainer, "_record_fail_dimension"):
                for dim in failing:
                    dream_trainer._record_fail_dimension(dim, 1.0, example={"episode_id": episode_id, "halted_by": "promotion_bridge", "route": route})
            if autonomy is not None and hasattr(autonomy, "add_study_topic"):
                autonomy.add_study_topic(f"recursive_causal_experience_chamber:{episode_id}:{','.join(failing)}")
            reason = "dimension_below_threshold" if missing else "transfer_below_threshold"
            return PromotionDecision(episode_id, False, reason, tuple(failing), dimension_scores, transfer_score, route=route)

        submitter = systems.get("submit_operational_experience")
        if submitter is None:
            return PromotionDecision(episode_id, False, "no_submission_seam_available", (), dimension_scores, transfer_score, route=route)

        operation_evidence = build_operation_evidence(step)
        if operation_evidence is None:
            return PromotionDecision(episode_id, False, "insufficient_structured_evidence", (), dimension_scores, transfer_score, route=route)
        input_value, expected_output = operation_evidence

        evidence = {
            "input_value": input_value,
            "expected_output": expected_output,
            "validation": validation,
            "task_id": rcec_primary_task_id(rule_family or "direct_trigger"),
            "source": "cognitive_experience_chamber",
            "need_description": "observed state + chosen action -> resulting state delta (RCEC chamber)",
        }
        submission_result = dict(submitter(evidence) or {})
        return PromotionDecision(episode_id, True, "submitted", (), dimension_scores, transfer_score, submission_result, route=route)


def run_shadow_promotion_cycle(
    state_dir: str,
    episode_world_specs: Sequence[Tuple[WorldState, HiddenRuleEngine, ObservationBoundary]],
    *,
    agent_id: str = "agent_a",
    bridge: Optional[DevelopmentalPromotionBridge] = None,
    promote_keys: Sequence[str] = (),
    boot_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Wires the full cycle: open_shadow_state() -> boot a second, fully
    independent Aurora instance against the shadow copy -> run each given
    episode inside it -> evaluate the always-on governors (meaning/
    expression divergence, contradiction accumulation across this cycle's
    episodes) -> for surviving episodes, submit_operational_experience()
    (the chamber's own WARP trial machinery still decides real promotion)
    -> promote_shadow_deltas() for the named keys only if at least one
    episode was actually submitted -> discard the rest of the shadow copy
    on exit.

    Known limitation, live-verified during this stage (not introduced by
    this module, and out of this directive's scope to fix): merely
    importing aurora, and separately boot_aurora() itself, were observed to
    write to the real DEFAULT aurora_state/ directory's files even when
    every systems dict here correctly threads a shadow state_dir through --
    something in aurora.py's own boot/runtime path still touches its
    hardcoded `Path(__file__).parent / "aurora_state"` fallback somewhere
    outside this function's control. aurora_shadow_state.py's own isolation
    is provably correct (test_shadow_state_utility.py exercises it against
    plain files with zero dependency on aurora.py); the gap is upstream,
    in aurora.py's state_dir threading, not in this shadow-copy mechanism.
    The live state_dir this function itself writes to is never touched until promote_shadow_
    deltas() runs, and only the named keys move."""
    import aurora as _aurora
    from aurora_internal.aurora_shadow_state import open_shadow_state, promote_shadow_deltas

    bridge = bridge or DevelopmentalPromotionBridge()
    boot_kwargs = dict(boot_kwargs if boot_kwargs is not None else {"runtime_profile": "surface", "verbose": False})
    decisions: List[PromotionDecision] = []
    tracker = ContradictionTracker()

    with open_shadow_state(state_dir) as handle:
        shadow_systems = _aurora.boot_aurora(state_dir=str(handle.shadow_state_dir), **boot_kwargs)
        dream_trainer = shadow_systems.get("dream_trainer")
        autonomy = shadow_systems.get("autonomy")

        for index, (world, engine, boundary) in enumerate(episode_world_specs):
            episode_id = f"shadow_{index}"
            trace = EpisodeTrace(episode_id=episode_id, world_seed=world.tick, rule_family=engine._rule.family, agent_id=agent_id)
            runtime_context = build_episode_runtime_context(shadow_systems)
            run_episode_step(trace, shadow_systems, runtime_context, world, engine, boundary, agent_id)
            step = trace.steps[0]

            apply_causal_evaluation(trace, 0, world, engine, boundary, agent_id, dream_trainer=dream_trainer)
            apply_expression_fidelity_evaluation(trace, 0)

            if step.interpretation.predicted_consequence is not None:
                contradiction_key = f"{step.interpretation.predicted_consequence.get('entity_id')}.{step.interpretation.predicted_consequence.get('property')}"
                tracker.record(contradiction_key, step.interpretation.predicted_consequence.get("direction"))

            governor_results = [
                DevelopmentalGovernors.meaning_expression_divergence(step.expression_fidelity),
                DevelopmentalGovernors.contradiction_accumulation(tracker),
            ]

            decision = bridge.evaluate_and_submit(
                shadow_systems, step, None, governor_results,
                dream_trainer=dream_trainer, autonomy=autonomy, episode_id=episode_id,
                rule_family=engine._rule.family,
            )
            decisions.append(decision)

        promoted_keys: List[str] = []
        if promote_keys and any(d.promoted for d in decisions):
            promoted_keys = promote_shadow_deltas(handle, promote_keys)

        # Build 608 (D3): stop the background daemon threads this boot
        # started (ConnectivityMonitor, ThoughtBraid, CheckpointAutoSave)
        # before the shadow copy is discarded -- see aurora.shutdown_
        # aurora()'s own docstring for why this matters across a battery of
        # calls, not just this one.
        _aurora.shutdown_aurora(shadow_systems)

    return {"decisions": decisions, "promoted_keys": promoted_keys}


# ---------------------------------------------------------------------------
# Build 608 (A): Canonical episode orchestrator.
# ---------------------------------------------------------------------------
#
# One function performing the entire developmental sequence: initial
# observation -> interpretation and action -> consequence -> initial
# evaluation -> backprojection -> revised evaluation -> counterfactual
# branch -> counterfactual evaluation -> transfer episode using ALT_SKIN ->
# transfer evaluation -> all developmental governors -> evidence admission.
# No daemon scheduling here -- this is a single manually invoked call, and
# every step reuses exactly the machinery Stages 1-6 already built. This
# function adds no new scoring or evaluation logic of its own; it is glue.

@dataclass(frozen=True)
class ClosedLoopEpisodeResult:
    trace: EpisodeTrace
    world_after: WorldState
    causal_result: CausalEvaluationResult
    revised_interpretation: Optional[CapturedInterpretation]
    counterfactual_branch: CounterfactualBranch
    transfer_world: WorldState
    transfer_engine: HiddenRuleEngine
    transfer_trace: EpisodeTrace
    transfer_result: CausalEvaluationResult
    transfer_comparison: TransferComparison
    expression_fidelity: Dict[str, Any]
    governor_results: List[GovernorResult]
    promotion_decision: PromotionDecision


def _auto_pick_counterfactual_alter(world: WorldState, engine: HiddenRuleEngine) -> Dict[str, Any]:
    """Default single-variable alteration when the caller doesn't supply
    one: perturb the rule's OWN target property's starting value (not the
    trigger condition), so the branch tests whether the stated causal claim
    holds from a different starting state -- not just the one sequence
    already observed."""
    rule = engine._rule
    target_entity = world.entities.get(rule.target_entity_id)
    if target_entity is None:
        raise ValueError("rule target entity is not present in this world")
    current = target_entity.properties.get(rule.target_property)
    if isinstance(current, bool):
        new_value: Any = not current
    elif isinstance(current, (int, float)):
        new_value = current + 3
    else:
        spec = PROPERTIES.get(rule.target_property)
        choices = [v for v in spec.domain] if spec is not None and spec.domain else []
        choices = [v for v in choices if v != current]
        new_value = choices[0] if choices else current
    return {"entity_id": rule.target_entity_id, "property": rule.target_property, "value": new_value}


def _stable_seed_from_id(identifier: str, offset: int = 500_000) -> int:
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:8]
    return (int(digest, 16) % 1_000_000) + offset


def run_closed_loop_episode(
    systems: Dict[str, Any],
    episode_runtime_context: Dict[str, Any],
    world: WorldState,
    engine: HiddenRuleEngine,
    boundary: ObservationBoundary,
    agent_id: str,
    *,
    episode_id: str,
    counterfactual_alter: Optional[Dict[str, Any]] = None,
    contradiction_tracker: Optional[ContradictionTracker] = None,
    confidence_calibration_history: Optional[Sequence[float]] = None,
    accuracy_history: Optional[Sequence[float]] = None,
    avatar_fitness_trend: Optional[float] = None,
    transfer_score_trend: Optional[float] = None,
    genealogy: Any = None,
    ability_tag: Optional[str] = None,
    regression_evidence_passed: Optional[bool] = None,
    candidate_program_tree: Optional[Dict[str, Any]] = None,
    dream_trainer: Any = None,
    autonomy: Any = None,
    bridge: Optional[DevelopmentalPromotionBridge] = None,
    validation: bool = False,
    transfer_seed: Optional[int] = None,
    fidelity_threshold: float = 0.5,
    skin: VocabularySkin = DEFAULT_SKIN,
) -> ClosedLoopEpisodeResult:
    """The canonical developmental sequence, start to finish, in one call.

    Cohort-level governors (confidence_rising_accuracy_falling, surface_
    fitness_without_transfer, loss_of_stable_ability, runaway_complexity)
    accept optional external context; a standalone call to this function
    (task A's "prove one complete manually invoked cycle") naturally
    reports them not-applicable, and a cohort runner supplies real
    cross-episode history/trends/genealogy to make them load-bearing --
    see run_developmental_cohort().

    skin renders/parses the PRIMARY episode (default DEFAULT_SKIN). The
    transfer sub-episode (steps 9-10) always uses whichever of the two
    skins is NOT the primary one, so transfer always tests genuinely
    disjoint surface vocabulary regardless of which skin the primary
    episode itself used -- this is how an "ALT_SKIN validation episode"
    (skin=ALT_SKIN) still gets a DEFAULT_SKIN transfer check."""
    bridge = bridge or DevelopmentalPromotionBridge()
    tracker = contradiction_tracker if contradiction_tracker is not None else ContradictionTracker()
    transfer_skin = DEFAULT_SKIN if skin is ALT_SKIN else ALT_SKIN

    # 1-3: initial observation -> interpretation and action -> consequence.
    trace = EpisodeTrace(episode_id=episode_id, world_seed=world.tick, rule_family=engine._rule.family, agent_id=agent_id)
    world_after = run_episode_step(trace, systems, episode_runtime_context, world, engine, boundary, agent_id, skin=skin)
    step = trace.steps[0]

    # 4: initial evaluation.
    apply_causal_evaluation(trace, 0, world, engine, boundary, agent_id, dream_trainer=dream_trainer)

    # 5-6: backprojection -> revised evaluation.
    revised_interpretation = run_backprojection_step(trace, systems, episode_runtime_context, 0, boundary, agent_id, skin=skin)

    # 7-8: counterfactual branch -> counterfactual evaluation.
    brancher = CounterfactualBrancher()
    alter = counterfactual_alter or _auto_pick_counterfactual_alter(world, engine)
    branch = brancher.spawn_branch(world, step.action, engine, alter)

    causal_result = apply_causal_evaluation(
        trace, 0, world, engine, boundary, agent_id,
        revised_interpretation=revised_interpretation,
        counterfactual_branch=branch,
        dream_trainer=dream_trainer,
    )

    # 9-10: transfer episode using ALT_SKIN -> transfer evaluation.
    transfer_world, transfer_engine = TransferGenerator.generate_transfer_world(
        rule_family=engine._rule.family,
        seed=transfer_seed if transfer_seed is not None else _stable_seed_from_id(episode_id),
        num_entities=len(world.entities),
        entity_types=tuple(sorted({e.entity_type for e in world.entities.values()})),
    )
    transfer_boundary = ObservationBoundary()
    transfer_trace = EpisodeTrace(
        episode_id=f"{episode_id}:transfer", world_seed=transfer_world.tick,
        rule_family=transfer_engine._rule.family, agent_id=agent_id,
    )
    transfer_runtime_context = build_episode_runtime_context(systems)
    run_episode_step(
        transfer_trace, systems, transfer_runtime_context, transfer_world, transfer_engine,
        transfer_boundary, agent_id, skin=transfer_skin,
    )
    transfer_result = apply_causal_evaluation(
        transfer_trace, 0, transfer_world, transfer_engine, transfer_boundary, agent_id, dream_trainer=dream_trainer,
    )
    transfer_comparison = compute_transfer_comparison(
        causal_result.as_dimension_scores(), transfer_result.as_dimension_scores(),
    )
    record_transfer_fail(dream_trainer, transfer_comparison, example={"episode_id": episode_id})

    # Expression fidelity (Stage 5) -- against the FINAL (revised) interpretation.
    apply_expression_fidelity_evaluation(trace, 0, revised_interpretation=revised_interpretation)

    if step.interpretation.predicted_consequence is not None:
        contradiction_key = f"{step.interpretation.predicted_consequence.get('entity_id')}.{step.interpretation.predicted_consequence.get('property')}"
        tracker.record(contradiction_key, step.interpretation.predicted_consequence.get("direction"))

    # 11: all developmental governors.
    governor_results = [
        DevelopmentalGovernors.meaning_expression_divergence(step.expression_fidelity, threshold=fidelity_threshold),
        DevelopmentalGovernors.contradiction_accumulation(tracker),
        DevelopmentalGovernors.confidence_rising_accuracy_falling(confidence_calibration_history, accuracy_history),
        DevelopmentalGovernors.surface_fitness_without_transfer(avatar_fitness_trend, transfer_score_trend),
        DevelopmentalGovernors.loss_of_stable_ability(genealogy, ability_tag, regression_evidence_passed),
        DevelopmentalGovernors.runaway_complexity(candidate_program_tree),
    ]

    # 12: evidence admission.
    decision = bridge.evaluate_and_submit(
        systems, step, transfer_comparison, governor_results,
        dream_trainer=dream_trainer, autonomy=autonomy, episode_id=episode_id,
        validation=validation, rule_family=engine._rule.family,
    )

    return ClosedLoopEpisodeResult(
        trace=trace,
        world_after=world_after,
        causal_result=causal_result,
        revised_interpretation=revised_interpretation,
        counterfactual_branch=branch,
        transfer_world=transfer_world,
        transfer_engine=transfer_engine,
        transfer_trace=transfer_trace,
        transfer_result=transfer_result,
        transfer_comparison=transfer_comparison,
        expression_fidelity=step.expression_fidelity or {},
        governor_results=governor_results,
        promotion_decision=decision,
    )


@dataclass(frozen=True)
class CohortResult:
    episode_results: List[ClosedLoopEpisodeResult]
    decisions: List[PromotionDecision]
    summary: Dict[str, Any]


def run_developmental_cohort(
    systems: Dict[str, Any],
    episode_specs: Sequence[Dict[str, Any]],
    *,
    agent_id: str = "agent_a",
    bridge: Optional[DevelopmentalPromotionBridge] = None,
    dream_trainer: Any = None,
    autonomy: Any = None,
    genealogy: Any = None,
    avatar: Any = None,
    history_window: int = 5,
) -> CohortResult:
    """Build 608 (D3): reuses ONE already-booted systems dict across every
    episode in the cohort rather than booting Aurora repeatedly -- the
    caller boots (and shuts down) exactly once, around this call. Also
    accumulates confidence-calibration/accuracy/transfer/avatar-fitness
    history across episodes so the cohort-level governors (confidence_
    rising_accuracy_falling, surface_fitness_without_transfer) become load-
    bearing instead of trivially not-applicable, the way a single isolated
    run_closed_loop_episode() call would report them.

    Each item in episode_specs is a dict with keys: world, engine,
    episode_id, and optionally boundary, counterfactual_alter, validation,
    transfer_seed, ability_tag, regression_evidence_passed, skin (the
    PRIMARY episode's vocabulary -- e.g. skin=ALT_SKIN for an "ALT_SKIN
    validation episode"; its transfer sub-episode always uses the other
    skin, per run_closed_loop_episode())."""
    bridge = bridge or DevelopmentalPromotionBridge()
    tracker = ContradictionTracker()
    confidence_history: List[float] = []
    accuracy_history: List[float] = []
    transfer_score_history: List[float] = []
    avatar_fitness_history: List[float] = []

    runtime_context = build_episode_runtime_context(systems)
    episode_results: List[ClosedLoopEpisodeResult] = []

    for spec in episode_specs:
        result = run_closed_loop_episode(
            systems, runtime_context,
            spec["world"], spec["engine"], spec.get("boundary") or ObservationBoundary(), agent_id,
            episode_id=spec["episode_id"],
            counterfactual_alter=spec.get("counterfactual_alter"),
            contradiction_tracker=tracker,
            confidence_calibration_history=list(confidence_history),
            accuracy_history=list(accuracy_history),
            avatar_fitness_trend=_trend(avatar_fitness_history, history_window) if avatar_fitness_history else None,
            transfer_score_trend=_trend(transfer_score_history, history_window) if transfer_score_history else None,
            genealogy=genealogy,
            ability_tag=spec.get("ability_tag"),
            regression_evidence_passed=spec.get("regression_evidence_passed"),
            dream_trainer=dream_trainer,
            autonomy=autonomy,
            bridge=bridge,
            validation=bool(spec.get("validation", False)),
            transfer_seed=spec.get("transfer_seed"),
            skin=spec.get("skin", DEFAULT_SKIN),
        )
        episode_results.append(result)

        if result.causal_result.confidence_calibration is not None:
            confidence_history.append(result.causal_result.confidence_calibration)
        accuracy_dim = (
            result.causal_result.prediction_accuracy
            if result.causal_result.prediction_accuracy is not None
            else result.causal_result.state_accuracy
        )
        if accuracy_dim is not None:
            accuracy_history.append(accuracy_dim)
        if result.transfer_comparison.transfer_score is not None:
            transfer_score_history.append(result.transfer_comparison.transfer_score)
        if avatar is not None and hasattr(avatar, "react"):
            avatar_result = avatar.react(
                result.trace.steps[0].interpretation.raw_expression,
                {"topic": spec["episode_id"], "expected_tone": "neutral"},
            )
            avatar_fitness_history.append(float(avatar_result.get("scaled_fitness", 0.0)))

    decisions = [r.promotion_decision for r in episode_results]
    summary = {
        "total_episodes": len(episode_results),
        "promoted": sum(1 for d in decisions if d.promoted),
        "routes": {d.episode_id: d.route for d in decisions},
        "confidence_calibration_history": confidence_history,
        "accuracy_history": accuracy_history,
        "transfer_score_history": transfer_score_history,
        "avatar_fitness_history": avatar_fitness_history,
    }
    return CohortResult(episode_results=episode_results, decisions=decisions, summary=summary)
