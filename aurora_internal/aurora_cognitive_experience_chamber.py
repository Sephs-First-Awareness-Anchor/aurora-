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
import random
import re
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

_ACTION_VERB_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("add_energy", ("add energy", "increase energy", "give energy", "more energy")),
    ("remove_energy", ("remove energy", "decrease energy", "take energy", "drain energy")),
    ("seal", ("seal ", "seal.")),
    ("unseal", ("unseal ", "unseal.", "open ")),
    ("connect", ("connect ", "connect.")),
    ("disconnect", ("disconnect ", "disconnect.")),
    ("wait", ("wait",)),
)


@dataclass(frozen=True)
class InterpretedAction:
    action: "ActionInvocation"
    intent: str  # "act" | "predict" | "ask"
    interpretation: CapturedInterpretation


def _label_to_entity_id(observed: ObservedWorldState) -> Dict[str, str]:
    return {_entity_label(entity).lower(): entity_id for entity_id, entity in observed.entities.items()}


def _phrase_for_action(name: str, targets: Tuple[str, ...], observed: ObservedWorldState) -> str:
    labels = [_entity_label(observed.entities[t]) for t in targets]
    if name == "add_energy":
        return f"add energy to {labels[0]}"
    if name == "remove_energy":
        return f"remove energy from {labels[0]}"
    if name == "seal":
        return f"seal {labels[0]}"
    if name == "unseal":
        return f"unseal {labels[0]}"
    if name == "connect":
        return f"connect {labels[0]} and {labels[1]}"
    if name == "disconnect":
        return f"disconnect {labels[0]} and {labels[1]}"
    return "wait"


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
    def build_prompt(observed: ObservedWorldState, max_actions: int = 8) -> str:
        observation_text = describe_observation(observed)
        options = ActionInterface.available_actions(observed)[:max_actions]
        option_phrases = [_phrase_for_action(name, targets, observed) for name, targets in options]
        options_text = ("Available actions: " + "; ".join(option_phrases) + ".") if option_phrases else ""
        ask = (
            "Choose one action, state what you predict will happen as a result, "
            "and say how confident you are. Note anything you are unsure about."
        )
        return " ".join(part for part in (observation_text, options_text, ask) if part)

    @staticmethod
    def interpret_expression(expression: str, observed: ObservedWorldState, confidence: float) -> InterpretedAction:
        text = str(expression or "")
        lowered = text.lower()
        label_to_id = _label_to_entity_id(observed)

        identified_entities = tuple(sorted(
            entity_id for label, entity_id in label_to_id.items() if label and label in lowered
        ))
        believed_relations = tuple(
            (rel.source_id, rel.relation_type, rel.target_id)
            for rel in observed.relationships
            if _entity_label(observed.entities[rel.source_id]).lower() in lowered
            and _entity_label(observed.entities[rel.target_id]).lower() in lowered
        )

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        evidence_cited = tuple(
            s for s in sentences
            if any(label in s.lower() for label in label_to_id if label)
            or any(prop in s.lower() for prop in PROPERTIES)
        )
        stated_unknowns = tuple(s for s in sentences if any(marker in s.lower() for marker in _UNKNOWN_MARKERS))

        predicted_consequence: Optional[Dict[str, Any]] = None
        for label, entity_id in label_to_id.items():
            if not label or label not in lowered:
                continue
            for prop_name in observed.entities[entity_id].properties:
                if prop_name not in lowered:
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

        action_type = next((name for name, patterns in _ACTION_VERB_PATTERNS if any(p in lowered for p in patterns)), None)
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
    expression_fidelity: Optional[Dict[str, Any]] = None   # Stage 5


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
        "expression_fidelity": step.expression_fidelity,
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
        expression_fidelity=data.get("expression_fidelity"),
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


def run_episode_step(
    trace: EpisodeTrace,
    systems: Dict[str, Any],
    episode_runtime_context: Dict[str, Any],
    world_state: WorldState,
    rule_engine: HiddenRuleEngine,
    boundary: ObservationBoundary,
    agent_id: str,
) -> WorldState:
    """Drive one turn of an episode through Aurora's real live-response
    bridge. Enforces capture-then-consequence structurally: interpretation is
    recorded before HiddenRuleEngine.step() is ever called."""
    import aurora as _aurora

    observed = boundary.observe(world_state, agent_id)
    prompt_text = ActionInterface.build_prompt(observed)

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

    interpreted = ActionInterface.interpret_expression(expression, observed, confidence)

    trace.record_interpretation(
        tick=world_state.tick,
        observation_text=prompt_text,
        action=interpreted.action,
        intent=interpreted.intent,
        interpretation=interpreted.interpretation,
    )

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
    """Five independent scores. No blended fitness number -- the original
    proposal's objection to one number standing in for all of them applies
    here directly. None means the dimension was not applicable to this turn
    (e.g. no prediction was made), not that it scored zero."""
    state_accuracy: Optional[float]
    prediction_accuracy: Optional[float]
    causal_discrimination: Optional[float]
    evidence_discipline: Optional[float]
    revision_quality: Optional[float]

    def as_dimension_scores(self) -> Dict[str, float]:
        mapping = {
            "causal_state_accuracy": self.state_accuracy,
            "causal_prediction_accuracy": self.prediction_accuracy,
            "causal_discrimination": self.causal_discrimination,
            "evidence_discipline": self.evidence_discipline,
            "revision_quality": self.revision_quality,
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
    def revision_quality(
        original: CapturedInterpretation,
        revised: Optional[CapturedInterpretation],
        prediction_was_wrong: Optional[bool],
    ) -> Optional[float]:
        if revised is None or not prediction_was_wrong:
            return None
        changed = (
            original.predicted_consequence != revised.predicted_consequence
            or original.believed_relations != revised.believed_relations
        )
        return 1.0 if changed else 0.0

    @classmethod
    def evaluate(
        cls,
        interpretation: CapturedInterpretation,
        world_before: WorldState,
        consequence: WorldState,
        observed_before: ObservedWorldState,
        engine: "HiddenRuleEngine",
        revised_interpretation: Optional[CapturedInterpretation] = None,
    ) -> CausalEvaluationResult:
        prediction_score = cls.prediction_accuracy(interpretation, world_before, consequence)
        prediction_was_wrong = (prediction_score == 0.0) if prediction_score is not None else None
        return CausalEvaluationResult(
            state_accuracy=cls.state_accuracy(interpretation, world_before),
            prediction_accuracy=prediction_score,
            causal_discrimination=cls.causal_discrimination(interpretation, engine),
            evidence_discipline=cls.evidence_discipline(interpretation, observed_before),
            revision_quality=cls.revision_quality(interpretation, revised_interpretation, prediction_was_wrong),
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
    )
    step.causal_scores = result.as_dimension_scores()
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
        f"Now: {describe_observation(observed_after)} "
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

    revised = ActionInterface.interpret_expression(expression, observed_after, confidence).interpretation

    step.backprojection = {
        "original_interpretation": asdict(step.interpretation),
        "reconciliation_prompt": reconciliation_prompt,
        "revised_interpretation": asdict(revised),
    }
    return revised
