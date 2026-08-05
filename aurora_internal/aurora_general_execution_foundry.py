"""
aurora_general_execution_foundry.py
===================================

Constraint-native general execution foundry for Aurora.

This module expands the operational synthesis chamber into a quarantined
substrate capable of expressing:

* iterative programs whose semantic loop is open-ended but whose runtime is
  always governed by fuel, time, depth, and memory budgets;
* recursive functions with explicit call-depth limits;
* persistent, long-lived state machines that survive process restarts;
* capability-scoped tool plans learned from demonstrations;
* entirely new Python source generated from a promoted intermediate program,
  or supplied as a candidate and executed only after AST validation inside a
  resource-limited child process.

"Unbounded" refers to expressive form, not permission to consume unbounded
host resources. No candidate can access files, networks, processes, imports,
credentials, or tools unless a separately registered capability explicitly
grants that operation. Tool handlers remain outside generated Python.

Developmental law:

    recurring unmet need
      -> X/T/N/B/A pressure
      -> generalized program or machine candidate
      -> quarantined execution
      -> varied holdout evidence
      -> WARP promotion
      -> constraint genealogy admission

Authors: Sunni (Sir) Morningstar and Ceph
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import multiprocessing as mp
import os
import queue
import resource
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from aurora_persistence_utils import atomic_write_json
from aurora_warp_protocol import CoverageGap, WarpCapable, WarpComponent
from aurora_internal.aurora_meaning_evolution import canonical_signature

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
_POSITIVE_ISTATE = {"X": "I_IS", "T": "I_CAN", "N": "I_DO", "B": "I_SAW", "A": "I_DID"}
_NEGATIVE_ISTATE = {"X": "I_ISNT", "T": "I_CANNOT", "N": "I_DONOT", "B": "I_SOUGHT", "A": "I_DIDNT"}

_MAX_TASKS = 96
_MAX_EXAMPLES = 128
_MIN_TRAINING = 3
_MIN_DISTINCT_TRAINING = 3
_MIN_VALIDATION = 4
_MIN_DISTINCT_VALIDATION = 3
_MAX_PROGRAM_NODES = 160
_DEFAULT_FUEL = 4096
_DEFAULT_RECURSION = 48
_DEFAULT_WALL_SECONDS = 1.5
_DEFAULT_STATE_BYTES = 262_144
_MAX_TOOL_CALLS = 24


@dataclass(frozen=True)
class GeneralPrimitiveSpec:
    name: str
    roots: Tuple[str, ...]
    description: str


GENERAL_PRIMITIVES: Dict[str, GeneralPrimitiveSpec] = {
    "INPUT": GeneralPrimitiveSpec("INPUT", ("X",), "admit current input"),
    "CONST": GeneralPrimitiveSpec("CONST", ("X", "A"), "admit an invariant"),
    "VAR": GeneralPrimitiveSpec("VAR", ("X", "T", "B"), "retrieve a persistent local identity"),
    "SET": GeneralPrimitiveSpec("SET", ("T", "N", "B", "A"), "change a bounded local identity"),
    "BLOCK": GeneralPrimitiveSpec("BLOCK", ("T", "N", "A"), "sequence operations through time"),
    "IF": GeneralPrimitiveSpec("IF", ("X", "B", "A"), "select a branch across a distinction"),
    "WHILE": GeneralPrimitiveSpec("WHILE", ("T", "N", "B", "A"), "repeat while a bounded relation persists"),
    "FOR_EACH": GeneralPrimitiveSpec("FOR_EACH", ("X", "T", "N", "B", "A"), "transform each admitted member"),
    "FUNCTION": GeneralPrimitiveSpec("FUNCTION", ("X", "T", "B", "A"), "preserve an executable relation"),
    "CALL": GeneralPrimitiveSpec("CALL", ("T", "N", "B", "A"), "apply a preserved executable relation"),
    "RETURN": GeneralPrimitiveSpec("RETURN", ("T", "B", "A"), "close an operation with a result"),
    "STATE_GET": GeneralPrimitiveSpec("STATE_GET", ("X", "T", "B"), "retrieve long-lived state"),
    "STATE_SET": GeneralPrimitiveSpec("STATE_SET", ("T", "N", "B", "A"), "change long-lived state"),
    "STATE_DELETE": GeneralPrimitiveSpec("STATE_DELETE", ("T", "N", "B", "A"), "remove long-lived state"),
    "TOOL": GeneralPrimitiveSpec("TOOL", ("X", "N", "B", "A"), "invoke an explicitly granted capability"),
    "LIST": GeneralPrimitiveSpec("LIST", ("X", "T", "B", "A"), "construct an ordered collection"),
    "MAP": GeneralPrimitiveSpec("MAP", ("X", "B", "A"), "construct a keyed collection"),
    "GET": GeneralPrimitiveSpec("GET", ("X", "B", "A"), "select a bounded member"),
    "APPEND": GeneralPrimitiveSpec("APPEND", ("T", "N", "B", "A"), "extend an ordered collection"),
    "LEN": GeneralPrimitiveSpec("LEN", ("X", "B"), "measure bounded extent"),
    "ADD": GeneralPrimitiveSpec("ADD", ("N", "A"), "combine magnitudes"),
    "SUB": GeneralPrimitiveSpec("SUB", ("T", "N", "A"), "express ordered difference"),
    "MUL": GeneralPrimitiveSpec("MUL", ("N", "B", "A"), "scale magnitudes"),
    "DIV": GeneralPrimitiveSpec("DIV", ("N", "B", "A"), "form a protected ratio"),
    "MOD": GeneralPrimitiveSpec("MOD", ("T", "N", "B"), "preserve cyclic remainder"),
    "NEG": GeneralPrimitiveSpec("NEG", ("N", "B"), "reverse polarity"),
    "EQ": GeneralPrimitiveSpec("EQ", ("X", "B", "A"), "test equivalence"),
    "NE": GeneralPrimitiveSpec("NE", ("X", "B", "A"), "test distinction"),
    "LT": GeneralPrimitiveSpec("LT", ("T", "B", "A"), "test lower order"),
    "LE": GeneralPrimitiveSpec("LE", ("T", "B", "A"), "test bounded lower order"),
    "GT": GeneralPrimitiveSpec("GT", ("T", "B", "A"), "test greater order"),
    "GE": GeneralPrimitiveSpec("GE", ("T", "B", "A"), "test bounded greater order"),
    "AND": GeneralPrimitiveSpec("AND", ("N", "B", "A"), "require joint truth"),
    "OR": GeneralPrimitiveSpec("OR", ("N", "B", "A"), "admit either truth"),
    "NOT": GeneralPrimitiveSpec("NOT", ("X", "B", "A"), "invert a truth relation"),
}


@dataclass
class ExecutionLimits:
    fuel: int = _DEFAULT_FUEL
    recursion_depth: int = _DEFAULT_RECURSION
    wall_seconds: float = _DEFAULT_WALL_SECONDS
    state_bytes: int = _DEFAULT_STATE_BYTES
    tool_calls: int = _MAX_TOOL_CALLS


@dataclass
class CapabilitySpec:
    name: str
    roots: Tuple[str, ...] = ("X", "N", "B", "A")
    description: str = ""
    side_effect_level: int = 0
    confirmation_required: bool = False
    max_calls_per_run: int = 4
    input_keys: Tuple[str, ...] = ()


@dataclass
class GeneralExample:
    example_id: str
    input_value: Any
    expected_output: Any
    validation: bool = False
    source: str = "experience"
    created_at: float = field(default_factory=time.time)


@dataclass
class GeneralProgram:
    program_id: str
    program: Dict[str, Any]
    functions: Dict[str, Dict[str, Any]]
    entry: str
    kind: str
    primitive_sequence: List[str]
    root_constraints: List[str]
    canonical_signature: str
    node_count: int
    source_python: str = ""
    status: str = "trial"
    training_score: float = 0.0
    validation_score: float = 0.0
    warp_component_id: str = ""
    genealogy_ability_id: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class GeneralTask:
    task_id: str
    need_description: str
    root_pressure: Dict[str, float]
    examples: List[GeneralExample] = field(default_factory=list)
    candidate: Optional[GeneralProgram] = None
    conflict_count: int = 0
    synthesis_attempts: int = 0
    status: str = "observing"
    warp_component_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class ToolPlan:
    plan_id: str
    task_id: str
    steps: List[Dict[str, Any]]
    roots: List[str]
    canonical_signature: str
    status: str = "trial"
    validation_count: int = 0
    genealogy_ability_id: str = ""


@dataclass
class StateMachineDefinition:
    machine_id: str
    initial_state: str
    transitions: Dict[str, Dict[str, Dict[str, Any]]]
    roots: List[str]
    canonical_signature: str
    status: str = "trial"
    validation_count: int = 0
    genealogy_ability_id: str = ""


class _ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        super().__init__("return")
        self.value = value


class ExecutionBudgetExceeded(RuntimeError):
    pass


class CapabilityDenied(PermissionError):
    pass


def _stable_hash(value: Any, length: int = 16) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _clone(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return copy.deepcopy(value)


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(_equal(left[k], right[k]) for k in left)
    return left == right


def _normalize_pressure(values: Mapping[str, Any]) -> Dict[str, float]:
    raw = {axis: max(0.0, float(dict(values or {}).get(axis, 0.0) or 0.0)) for axis in AXES}
    total = sum(raw.values()) or 1.0
    return {axis: round(raw[axis] / total, 6) for axis in AXES}


def _pressure_for(input_value: Any, output_value: Any, kind: str = "program") -> Dict[str, float]:
    pressure = {"X": 0.60, "T": 0.75, "N": 0.95, "B": 0.75, "A": 0.90}
    if isinstance(input_value, (list, tuple)):
        pressure["T"] += 0.25
        pressure["B"] += 0.15
    if kind in {"state_machine", "recursive", "loop"}:
        pressure["T"] += 0.35
    if kind == "tool_plan":
        pressure["B"] += 0.35
        pressure["A"] += 0.20
    if kind == "python":
        pressure["X"] += 0.15
        pressure["B"] += 0.30
    return _normalize_pressure(pressure)


def _warp_profile(pressure: Mapping[str, Any]) -> Dict[str, float]:
    roots = _normalize_pressure(pressure)
    profile: Dict[str, float] = {}
    for axis in AXES:
        value = roots[axis]
        profile[_NEGATIVE_ISTATE[axis]] = value
        profile[_POSITIVE_ISTATE[axis]] = value * 0.10
    profile.update({"REC_SURFACE": 0.06, "REC_SHALLOW": 0.18, "REC_MODERATE": 0.55, "REC_DEEP": 0.80, "REC_CORE": 0.72})
    return profile


def _walk_nodes(node: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(node, Mapping):
        yield node
        for value in node.values():
            yield from _walk_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_nodes(value)


def _node_count(program: Mapping[str, Any], functions: Mapping[str, Mapping[str, Any]]) -> int:
    return sum(1 for _ in _walk_nodes(program)) + sum(sum(1 for _ in _walk_nodes(body)) for body in functions.values())


def _primitive_sequence(program: Mapping[str, Any], functions: Mapping[str, Mapping[str, Any]]) -> List[str]:
    out: List[str] = []
    for root in [program, *functions.values()]:
        for node in _walk_nodes(root):
            op = str(node.get("op", "") or "")
            if op:
                out.append(op)
    return out


def _roots_for(sequence: Sequence[str], extra: Sequence[str] = ()) -> List[str]:
    roots: set[str] = set(extra)
    for name in sequence:
        spec = GENERAL_PRIMITIVES.get(name)
        if spec:
            roots.update(spec.roots)
    return [axis for axis in AXES if axis in roots]


def validate_general_program(program: Mapping[str, Any], functions: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    functions = {str(key): dict(value) for key, value in dict(functions or {}).items()}
    count = _node_count(dict(program or {}), functions)
    if count <= 0:
        return {"valid": False, "reason": "empty_program"}
    if count > _MAX_PROGRAM_NODES:
        return {"valid": False, "reason": "program_node_limit", "node_count": count}
    function_names = set(functions)
    primitives: List[str] = []
    for root in [dict(program or {}), *functions.values()]:
        for node in _walk_nodes(root):
            op = str(node.get("op", "") or "")
            if not op:
                continue
            primitives.append(op)
            if op not in GENERAL_PRIMITIVES:
                return {"valid": False, "reason": "unknown_general_primitive", "detail": op}
            if op == "CALL" and str(node.get("name", "") or "") not in function_names:
                return {"valid": False, "reason": "unknown_function", "detail": str(node.get("name", "") or "")}
            if op == "TOOL" and not str(node.get("name", "") or "").strip():
                return {"valid": False, "reason": "tool_name_required"}
            if op in {"VAR", "SET"} and not str(node.get("name", "") or "").strip():
                return {"valid": False, "reason": "variable_name_required"}
    roots = _roots_for(primitives)
    return {
        "valid": True,
        "node_count": count,
        "primitive_sequence": primitives,
        "root_constraints": roots,
        "canonical_signature": canonical_signature(roots or AXES),
    }


class CapabilityBroker:
    """Capability-scoped tool broker. Handlers are runtime-only and never persisted."""

    def __init__(self) -> None:
        self._specs: Dict[str, CapabilitySpec] = {}
        self._handlers: Dict[str, Callable[[Mapping[str, Any]], Any]] = {}
        self._grants: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def register(self, spec: CapabilitySpec, handler: Callable[[Mapping[str, Any]], Any]) -> None:
        if not callable(handler):
            raise TypeError("capability_handler_must_be_callable")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def grant(self, task_id: str, tool_name: str, *, allow_side_effects: bool = False, confirmation: str = "") -> None:
        spec = self._specs.get(tool_name)
        if spec is None:
            raise KeyError(f"unknown_capability:{tool_name}")
        if spec.side_effect_level > 0 and not allow_side_effects:
            raise CapabilityDenied("side_effect_grant_required")
        if spec.confirmation_required and not confirmation:
            raise CapabilityDenied("confirmation_required")
        self._grants.setdefault(task_id, {})[tool_name] = {
            "allow_side_effects": bool(allow_side_effects),
            "confirmation": str(confirmation or ""),
            "granted_at": time.time(),
        }

    def revoke(self, task_id: str, tool_name: str) -> None:
        self._grants.get(task_id, {}).pop(tool_name, None)

    def call(self, task_id: str, tool_name: str, arguments: Mapping[str, Any], call_counts: MutableMapping[str, int]) -> Any:
        spec = self._specs.get(tool_name)
        handler = self._handlers.get(tool_name)
        grant = self._grants.get(task_id, {}).get(tool_name)
        if spec is None or handler is None:
            raise CapabilityDenied(f"capability_unavailable:{tool_name}")
        if grant is None:
            raise CapabilityDenied(f"capability_not_granted:{tool_name}")
        count = int(call_counts.get(tool_name, 0)) + 1
        if count > max(1, int(spec.max_calls_per_run)):
            raise CapabilityDenied(f"capability_call_limit:{tool_name}")
        args = dict(arguments or {})
        if spec.input_keys and not set(args).issubset(set(spec.input_keys)):
            raise CapabilityDenied(f"capability_argument_boundary:{tool_name}")
        call_counts[tool_name] = count
        return handler(args)

    def manifest(self) -> List[Dict[str, Any]]:
        return [asdict(self._specs[name]) for name in sorted(self._specs)]


class GeneralProgramExecutor:
    def __init__(
        self,
        *,
        task_id: str,
        state: MutableMapping[str, Any],
        broker: Optional[CapabilityBroker] = None,
        limits: Optional[ExecutionLimits] = None,
    ) -> None:
        self.task_id = task_id
        self.state = state
        self.broker = broker
        self.limits = limits or ExecutionLimits()
        self.fuel = max(1, int(self.limits.fuel))
        self.deadline = time.monotonic() + max(0.01, float(self.limits.wall_seconds))
        self.call_depth = 0
        self.tool_counts: Dict[str, int] = {}
        self.functions: Dict[str, Dict[str, Any]] = {}

    def _tick(self, amount: int = 1) -> None:
        self.fuel -= max(1, int(amount))
        if self.fuel < 0:
            raise ExecutionBudgetExceeded("fuel_exhausted")
        if time.monotonic() > self.deadline:
            raise ExecutionBudgetExceeded("wall_time_exceeded")

    def execute(self, program: Mapping[str, Any], input_value: Any, functions: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Any:
        self.functions = {str(k): dict(v) for k, v in dict(functions or {}).items()}
        env: Dict[str, Any] = {"input": _clone(input_value)}
        try:
            return self._eval(dict(program or {}), env)
        except _ReturnSignal as signal_value:
            return signal_value.value

    def _eval(self, node: Any, env: MutableMapping[str, Any]) -> Any:
        self._tick()
        if not isinstance(node, Mapping):
            return _clone(node)
        op = str(node.get("op", "") or "")
        if op == "INPUT": return _clone(env.get("input"))
        if op == "CONST": return _clone(node.get("value"))
        if op == "VAR": return _clone(env.get(str(node.get("name", ""))))
        if op == "SET":
            value = self._eval(node.get("value"), env)
            env[str(node.get("name", ""))] = _clone(value)
            return value
        if op == "BLOCK":
            result = None
            for child in list(node.get("body") or []):
                result = self._eval(child, env)
            return result
        if op == "IF":
            branch = node.get("then") if bool(self._eval(node.get("condition"), env)) else node.get("else")
            return self._eval(branch or {"op": "CONST", "value": None}, env)
        if op == "WHILE":
            result = None
            while bool(self._eval(node.get("condition"), env)):
                result = self._eval(node.get("body") or {"op": "CONST", "value": None}, env)
                self._tick()
            return result
        if op == "FOR_EACH":
            sequence = self._eval(node.get("iterable"), env)
            result = None
            for index, item in enumerate(list(sequence or [])):
                self._tick()
                env[str(node.get("item", "item"))] = _clone(item)
                env[str(node.get("index", "index"))] = index
                result = self._eval(node.get("body") or {"op": "CONST", "value": None}, env)
            return result
        if op == "RETURN":
            raise _ReturnSignal(self._eval(node.get("value"), env))
        if op == "CALL":
            name = str(node.get("name", "") or "")
            definition = self.functions.get(name)
            if definition is None:
                raise KeyError(f"unknown_function:{name}")
            self.call_depth += 1
            if self.call_depth > max(1, int(self.limits.recursion_depth)):
                self.call_depth -= 1
                raise ExecutionBudgetExceeded("recursion_depth_exceeded")
            try:
                parameters = list(definition.get("params") or [])
                arguments = [self._eval(arg, env) for arg in list(node.get("args") or [])]
                local_env: Dict[str, Any] = {"input": env.get("input")}
                local_env.update({str(name): _clone(arguments[i]) if i < len(arguments) else None for i, name in enumerate(parameters)})
                try:
                    return self._eval(definition.get("body") or {}, local_env)
                except _ReturnSignal as signal_value:
                    return signal_value.value
            finally:
                self.call_depth -= 1
        if op == "STATE_GET":
            key = str(self._eval(node.get("key"), env))
            return _clone(self.state.get(key, self._eval(node.get("default", {"op": "CONST", "value": None}), env)))
        if op == "STATE_SET":
            key = str(self._eval(node.get("key"), env))
            value = self._eval(node.get("value"), env)
            provisional = dict(self.state)
            provisional[key] = _clone(value)
            size = len(json.dumps(provisional, default=str).encode("utf-8"))
            if size > max(1024, int(self.limits.state_bytes)):
                raise ExecutionBudgetExceeded("persistent_state_limit")
            self.state[key] = _clone(value)
            return value
        if op == "STATE_DELETE":
            key = str(self._eval(node.get("key"), env))
            return self.state.pop(key, None)
        if op == "TOOL":
            if self.broker is None:
                raise CapabilityDenied("no_capability_broker")
            if sum(self.tool_counts.values()) >= max(1, int(self.limits.tool_calls)):
                raise CapabilityDenied("run_tool_call_limit")
            arguments = self._eval(node.get("arguments", {"op": "MAP", "fields": {}}), env)
            if not isinstance(arguments, Mapping):
                raise TypeError("tool_arguments_must_be_mapping")
            return _clone(self.broker.call(self.task_id, str(node.get("name", "")), arguments, self.tool_counts))
        if op == "LIST": return [self._eval(x, env) for x in list(node.get("items") or [])]
        if op == "MAP": return {str(k): self._eval(v, env) for k, v in dict(node.get("fields") or {}).items()}
        if op == "GET":
            obj = self._eval(node.get("object"), env)
            key = self._eval(node.get("key"), env)
            return _clone(obj[key])
        if op == "APPEND":
            target_name = str(node.get("target", "") or "")
            target = env.get(target_name)
            if not isinstance(target, list):
                raise TypeError("append_target_not_list")
            target.append(_clone(self._eval(node.get("value"), env)))
            return target
        if op == "LEN": return len(self._eval(node.get("value"), env))
        if op == "NOT": return not bool(self._eval(node.get("value"), env))
        if op in {"ADD", "SUB", "MUL", "DIV", "MOD", "EQ", "NE", "LT", "LE", "GT", "GE", "AND", "OR"}:
            left = self._eval(node.get("left"), env)
            if op == "AND" and not bool(left): return False
            if op == "OR" and bool(left): return True
            right = self._eval(node.get("right"), env)
            if op == "ADD": return left + right
            if op == "SUB": return left - right
            if op == "MUL": return left * right
            if op == "DIV":
                if float(right) == 0.0: raise ZeroDivisionError("division_by_zero")
                return left / right
            if op == "MOD": return left % right
            if op == "EQ": return _equal(left, right)
            if op == "NE": return not _equal(left, right)
            if op == "LT": return left < right
            if op == "LE": return left <= right
            if op == "GT": return left > right
            if op == "GE": return left >= right
            if op == "AND": return bool(left) and bool(right)
            if op == "OR": return bool(left) or bool(right)
        if op == "NEG": return -self._eval(node.get("value"), env)
        raise ValueError(f"unknown_general_primitive:{op}")


# ---------------------------------------------------------------------------
# Candidate synthesis
# ---------------------------------------------------------------------------

def _program_sum_loop() -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], str]:
    program = {
        "op": "BLOCK",
        "body": [
            {"op": "SET", "name": "acc", "value": {"op": "CONST", "value": 0}},
            {"op": "FOR_EACH", "item": "item", "iterable": {"op": "INPUT"}, "body": {
                "op": "SET", "name": "acc", "value": {"op": "ADD", "left": {"op": "VAR", "name": "acc"}, "right": {"op": "VAR", "name": "item"}}
            }},
            {"op": "RETURN", "value": {"op": "VAR", "name": "acc"}},
        ],
    }
    return program, {}, "loop"


def _program_product_loop() -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], str]:
    program = {
        "op": "BLOCK",
        "body": [
            {"op": "SET", "name": "acc", "value": {"op": "CONST", "value": 1}},
            {"op": "FOR_EACH", "item": "item", "iterable": {"op": "INPUT"}, "body": {
                "op": "SET", "name": "acc", "value": {"op": "MUL", "left": {"op": "VAR", "name": "acc"}, "right": {"op": "VAR", "name": "item"}}
            }},
            {"op": "RETURN", "value": {"op": "VAR", "name": "acc"}},
        ],
    }
    return program, {}, "loop"


def _program_factorial_recursive() -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], str]:
    functions = {
        "factorial": {
            "params": ["n"],
            "body": {"op": "IF", "condition": {"op": "LE", "left": {"op": "VAR", "name": "n"}, "right": {"op": "CONST", "value": 1}},
                     "then": {"op": "RETURN", "value": {"op": "CONST", "value": 1}},
                     "else": {"op": "RETURN", "value": {"op": "MUL", "left": {"op": "VAR", "name": "n"}, "right": {
                         "op": "CALL", "name": "factorial", "args": [{"op": "SUB", "left": {"op": "VAR", "name": "n"}, "right": {"op": "CONST", "value": 1}}]
                     }}}}
        }
    }
    program = {"op": "RETURN", "value": {"op": "CALL", "name": "factorial", "args": [{"op": "INPUT"}]}}
    return program, functions, "recursive"


def _program_fibonacci_recursive() -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], str]:
    functions = {
        "fib": {
            "params": ["n"],
            "body": {"op": "IF", "condition": {"op": "LE", "left": {"op": "VAR", "name": "n"}, "right": {"op": "CONST", "value": 1}},
                     "then": {"op": "RETURN", "value": {"op": "VAR", "name": "n"}},
                     "else": {"op": "RETURN", "value": {"op": "ADD", "left": {
                         "op": "CALL", "name": "fib", "args": [{"op": "SUB", "left": {"op": "VAR", "name": "n"}, "right": {"op": "CONST", "value": 1}}]
                     }, "right": {
                         "op": "CALL", "name": "fib", "args": [{"op": "SUB", "left": {"op": "VAR", "name": "n"}, "right": {"op": "CONST", "value": 2}}]
                     }}}}
        }
    }
    program = {"op": "RETURN", "value": {"op": "CALL", "name": "fib", "args": [{"op": "INPUT"}]}}
    return program, functions, "recursive"


def _candidate_templates() -> List[Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], str]]:
    return [_program_sum_loop(), _program_product_loop(), _program_factorial_recursive(), _program_fibonacci_recursive()]


def _run_candidate(program: Mapping[str, Any], functions: Mapping[str, Mapping[str, Any]], value: Any, *, limits: Optional[ExecutionLimits] = None) -> Any:
    return GeneralProgramExecutor(task_id="candidate", state={}, limits=limits).execute(program, value, functions)


def synthesize_general_program(examples: Sequence[GeneralExample]) -> Optional[Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], str]]:
    training = [example for example in examples if not example.validation]
    if len(training) < _MIN_TRAINING:
        return None
    for program, functions, kind in _candidate_templates():
        try:
            if all(_equal(_run_candidate(program, functions, example.input_value), example.expected_output) for example in training):
                return _clone(program), _clone(functions), kind
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Python generation and sandbox
# ---------------------------------------------------------------------------

_ALLOWED_AST_NODES = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign, ast.AugAssign,
    ast.Expr, ast.If, ast.For, ast.While, ast.Break, ast.Continue, ast.Pass, ast.Name, ast.Load,
    ast.Store, ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.BinOp, ast.UnaryOp, ast.BoolOp,
    ast.Compare, ast.Call, ast.Subscript, ast.Slice, ast.Index, ast.Add, ast.Sub, ast.Mult,
    ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.Not, ast.And, ast.Or, ast.Eq,
    ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.IfExp, ast.Attribute,
}
_ALLOWED_CALLS = {"range", "len", "enumerate", "min", "max", "sum", "abs", "all", "any", "sorted", "zip", "list", "dict", "tuple", "set", "bool", "int", "float", "str"}
_FORBIDDEN_NAMES = {"__import__", "eval", "exec", "compile", "open", "input", "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr", "help", "breakpoint", "memoryview", "super", "type", "object"}


def validate_python_source(source: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(str(source or ""), mode="exec")
    except SyntaxError as exc:
        return {"valid": False, "reason": "syntax_error", "detail": str(exc)}
    definitions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    if "aurora_program" not in definitions:
        return {"valid": False, "reason": "aurora_program_required"}
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_AST_NODES:
            return {"valid": False, "reason": "forbidden_ast_node", "detail": type(node).__name__}
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            return {"valid": False, "reason": "forbidden_name", "detail": node.id}
        if isinstance(node, ast.Attribute):
            if node.attr not in {"get", "pop", "append"} or not isinstance(node.value, ast.Name):
                return {"valid": False, "reason": "forbidden_attribute", "detail": node.attr}
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in _ALLOWED_CALLS and node.func.id not in definitions:
                    return {"valid": False, "reason": "unapproved_call", "detail": node.func.id}
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr not in {"get", "pop", "append"}:
                    return {"valid": False, "reason": "unapproved_method", "detail": node.func.attr}
            else:
                return {"valid": False, "reason": "dynamic_call_forbidden"}
    return {"valid": True, "functions": sorted(definitions), "ast_nodes": sum(1 for _ in ast.walk(tree))}


def _sandbox_worker(source: str, input_value: Any, state: Dict[str, Any], limits: Dict[str, Any], connection: Any) -> None:
    try:
        memory_bytes = max(32 * 1024 * 1024, int(limits.get("memory_bytes", 96 * 1024 * 1024)))
        try:
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
            resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (8, 8))
            resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
        except Exception:
            pass
        fuel = [max(1, int(limits.get("fuel", _DEFAULT_FUEL)))]
        deadline = time.monotonic() + max(0.05, float(limits.get("wall_seconds", _DEFAULT_WALL_SECONDS)))
        def tracer(frame: Any, event: str, arg: Any) -> Any:
            if event in {"line", "call"}:
                fuel[0] -= 1
                if fuel[0] < 0:
                    raise ExecutionBudgetExceeded("python_fuel_exhausted")
                if time.monotonic() > deadline:
                    raise ExecutionBudgetExceeded("python_wall_time_exceeded")
            return tracer
        safe_builtins = {name: __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name) for name in _ALLOWED_CALLS}
        namespace: Dict[str, Any] = {"__builtins__": safe_builtins}
        compiled = compile(source, "<aurora_synthesized>", "exec", dont_inherit=True, optimize=2)
        sys.settrace(tracer)
        exec(compiled, namespace, namespace)
        function = namespace["aurora_program"]
        result = function(_clone(input_value), _clone(state))
        sys.settrace(None)
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], Mapping):
            output_value, new_state = result
        else:
            output_value, new_state = result, state
        connection.send({"ok": True, "output": _clone(output_value), "state": _clone(new_state)})
    except BaseException as exc:
        try:
            connection.send({"ok": False, "error": type(exc).__name__, "detail": str(exc)})
        except Exception:
            pass


def execute_python_sandbox(source: str, input_value: Any, state: Optional[Mapping[str, Any]] = None, *, limits: Optional[ExecutionLimits] = None) -> Dict[str, Any]:
    validation = validate_python_source(source)
    if not validation.get("valid"):
        return {"executed": False, **validation}
    lim = limits or ExecutionLimits()
    context = mp.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    process = context.Process(target=_sandbox_worker, args=(source, _clone(input_value), dict(state or {}), {
        "fuel": lim.fuel,
        "wall_seconds": lim.wall_seconds,
        "memory_bytes": max(256 * 1024 * 1024, lim.state_bytes * 32),
    }, child_connection))
    process.daemon = True
    process.start()
    process.join(timeout=max(0.1, lim.wall_seconds + 0.75))
    if process.is_alive():
        process.terminate()
        process.join(timeout=0.5)
        return {"executed": False, "reason": "sandbox_timeout"}
    if not parent_connection.poll(0.25):
        return {"executed": False, "reason": "sandbox_no_result", "exitcode": process.exitcode}
    record = parent_connection.recv()
    if not record.get("ok"):
        return {"executed": False, "reason": record.get("error", "sandbox_error"), "detail": record.get("detail", "")}
    return {"executed": True, "output": record.get("output"), "state": record.get("state"), "validation": validation}


def program_to_python(program: Mapping[str, Any], functions: Mapping[str, Mapping[str, Any]], entry: str = "aurora_program") -> str:
    """Transpile the general IR into new, AST-valid Python source."""
    counter = [0]
    def name(prefix: str) -> str:
        counter[0] += 1
        return f"_{prefix}_{counter[0]}"
    def expr(node: Any) -> str:
        if not isinstance(node, Mapping): return repr(node)
        op = str(node.get("op", "") or "")
        if op == "INPUT": return "input_value"
        if op == "CONST": return repr(node.get("value"))
        if op == "VAR": return str(node.get("name", "value"))
        if op == "GET": return f"({expr(node.get('object'))})[{expr(node.get('key'))}]"
        if op == "LEN": return f"len({expr(node.get('value'))})"
        if op == "NEG": return f"(-{expr(node.get('value'))})"
        binary = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "%", "EQ": "==", "NE": "!=", "LT": "<", "LE": "<=", "GT": ">", "GE": ">=", "AND": "and", "OR": "or"}
        if op in binary: return f"({expr(node.get('left'))} {binary[op]} {expr(node.get('right'))})"
        if op == "NOT": return f"(not {expr(node.get('value'))})"
        if op == "LIST": return "[" + ", ".join(expr(x) for x in list(node.get("items") or [])) + "]"
        if op == "MAP": return "{" + ", ".join(f"{k!r}: {expr(v)}" for k, v in dict(node.get("fields") or {}).items()) + "}"
        if op == "CALL": return f"{node.get('name')}({', '.join(expr(x) for x in list(node.get('args') or []))})"
        if op == "STATE_GET": return f"state.get({expr(node.get('key'))}, {expr(node.get('default', {'op':'CONST','value':None}))})"
        raise ValueError(f"expression_not_transpilable:{op}")
    def statements(node: Mapping[str, Any], indent: int = 1) -> List[str]:
        pad = "    " * indent
        op = str(node.get("op", "") or "")
        if op == "BLOCK":
            out: List[str] = []
            for child in list(node.get("body") or []): out.extend(statements(child, indent))
            return out or [pad + "pass"]
        if op == "SET": return [pad + f"{node.get('name')} = {expr(node.get('value'))}"]
        if op == "RETURN": return [pad + f"return {expr(node.get('value'))}"]
        if op == "IF":
            out = [pad + f"if {expr(node.get('condition'))}:"]
            out.extend(statements(node.get("then") or {"op":"BLOCK","body":[]}, indent + 1))
            if node.get("else") is not None:
                out.append(pad + "else:")
                out.extend(statements(node.get("else"), indent + 1))
            return out
        if op == "WHILE":
            out = [pad + f"while {expr(node.get('condition'))}:"]
            out.extend(statements(node.get("body") or {"op":"BLOCK","body":[]}, indent + 1))
            return out
        if op == "FOR_EACH":
            item = str(node.get("item", "item"))
            index = str(node.get("index", "index"))
            out = [pad + f"for {index}, {item} in enumerate({expr(node.get('iterable'))}):"]
            out.extend(statements(node.get("body") or {"op":"BLOCK","body":[]}, indent + 1))
            return out
        if op == "STATE_SET": return [pad + f"state[{expr(node.get('key'))}] = {expr(node.get('value'))}"]
        if op == "STATE_DELETE": return [pad + f"state.pop({expr(node.get('key'))}, None)"]
        if op == "APPEND": return [pad + f"{node.get('target')}.append({expr(node.get('value'))})"]
        return [pad + expr(node)]
    lines: List[str] = []
    for function_name, definition in functions.items():
        params = ", ".join(str(x) for x in list(definition.get("params") or []))
        lines.append(f"def {function_name}({params}):")
        lines.extend(statements(definition.get("body") or {"op":"BLOCK","body":[]}, 1))
        lines.append("")
    lines.append(f"def {entry}(input_value, state):")
    lines.extend(statements(program, 1))
    if not any(line.lstrip().startswith("return ") for line in lines[-max(1, len(lines)):]):
        lines.append("    return None")
    return "\n".join(lines).rstrip() + "\n"


class AuroraGeneralExecutionFoundry(WarpCapable):
    """Generalized but capability-contained synthesis, execution, and promotion."""

    def __init__(self, *, state_dir: str = "aurora_state", persist: bool = True, genealogy: Any = None) -> None:
        self.state_dir = str(state_dir or "aurora_state")
        self.persist = bool(persist)
        self.storage_path = os.path.join(self.state_dir, "general_execution_foundry.json")
        self.systems: Dict[str, Any] = {}
        self.tasks: Dict[str, GeneralTask] = {}
        self.program_states: Dict[str, Dict[str, Any]] = {}
        self.tool_plans: Dict[str, ToolPlan] = {}
        self.tool_demos: Dict[str, List[Dict[str, Any]]] = {}
        self.state_machines: Dict[str, StateMachineDefinition] = {}
        self.machine_instances: Dict[str, Dict[str, Any]] = {}
        self.broker = CapabilityBroker()
        self._component_task: Dict[str, str] = {}
        self._active_task_id = ""
        self._tick = 0
        self._init_warp(genealogy=genealogy)
        self._load()

    def attach_systems(self, systems: Mapping[str, Any]) -> None:
        self.systems = systems if isinstance(systems, dict) else dict(systems or {})
        genealogy = self.systems.get("genealogy")
        if genealogy is not None:
            self.set_warp_genealogy(genealogy)
        if isinstance(self.systems, dict):
            self.systems["submit_general_program_example"] = self.observe_example
            self.systems["submit_general_program_candidate"] = self.submit_program_candidate
            self.systems["submit_python_candidate"] = self.submit_python_candidate
            self.systems["submit_state_transition"] = self.observe_transition
            self.systems["submit_tool_demonstration"] = self.observe_tool_demonstration
            self.systems["execute_general_ability"] = self.execute

    def _warp_level_name(self) -> str:
        return "general_execution_foundry"

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        profiles: Dict[str, Dict[str, float]] = {}
        for name, spec in GENERAL_PRIMITIVES.items():
            profile: Dict[str, float] = {}
            for axis in AXES:
                profile[_POSITIVE_ISTATE[axis]] = 0.72 if axis in spec.roots else 0.03
                profile[_NEGATIVE_ISTATE[axis]] = 0.10 if axis in spec.roots else 0.02
            profile.update({"REC_SURFACE": 0.05, "REC_SHALLOW": 0.15, "REC_MODERATE": 0.35, "REC_DEEP": 0.55, "REC_CORE": 0.45})
            profiles[f"general_primitive:{name}"] = profile
        return profiles

    def _warp_params(self, gap: CoverageGap, parent_ids: List[str]) -> Dict[str, Any]:
        task = self.tasks.get(self._active_task_id)
        roots = [axis for axis in AXES if task and task.root_pressure.get(axis, 0.0) >= 0.10] or list(AXES)
        return {"task_id": self._active_task_id, "need_description": task.need_description if task else "", "root_constraints": roots, "canonical_signature": canonical_signature(roots), "parent_ids": list(parent_ids or []), "origin": "generalized_unmet_operation"}

    def _integrate_warp(self, component: WarpComponent) -> None:
        task_id = str(dict(component.parameters or {}).get("task_id", "") or self._active_task_id)
        task = self.tasks.get(task_id)
        if task is None: return
        task.warp_component_id = component.component_id
        self._component_task[component.component_id] = task_id
        if task.candidate: task.candidate.warp_component_id = component.component_id
        task.status = "warp_trial"
        self._persist()

    def _score_trial(self, component: WarpComponent) -> float:
        task = self.tasks.get(self._component_task.get(component.component_id, ""))
        if task is None or task.candidate is None or task.conflict_count:
            return 0.0
        training = [e for e in task.examples if not e.validation]
        validation = [e for e in task.examples if e.validation]
        if len(validation) < _MIN_VALIDATION or len({_stable_hash(e.input_value) for e in validation}) < _MIN_DISTINCT_VALIDATION:
            return 0.0
        train_score = self._score(task, training)
        validation_score = self._score(task, validation)
        task.candidate.training_score = train_score
        task.candidate.validation_score = validation_score
        if train_score < 1.0 or validation_score < 1.0:
            return 0.0
        complexity = min(1.0, task.candidate.node_count / float(_MAX_PROGRAM_NODES))
        return max(0.0, min(1.0, 0.96 - 0.14 * complexity))

    def _dissolve_warp(self, component_id: str) -> None:
        task = self.tasks.get(self._component_task.get(component_id, ""))
        if task:
            task.status = "dissolved"
            if task.candidate: task.candidate.status = "dissolved"
        self._persist()

    def register_capability(self, spec: CapabilitySpec, handler: Callable[[Mapping[str, Any]], Any]) -> None:
        self.broker.register(spec, handler)

    def grant_capability(self, task_id: str, tool_name: str, **kwargs: Any) -> None:
        self.broker.grant(str(task_id), str(tool_name), **kwargs)

    def observe_example(self, task_id: str, input_value: Any, expected_output: Any, *, validation: bool = False, source: str = "experience", need_description: str = "") -> Dict[str, Any]:
        key = str(task_id or "").strip()
        if not key: raise ValueError("task_id_required")
        task = self.tasks.get(key)
        if task is None:
            if len(self.tasks) >= _MAX_TASKS:
                oldest = min(self.tasks.values(), key=lambda item: item.updated_at)
                self.tasks.pop(oldest.task_id, None)
            task = GeneralTask(task_id=key, need_description=str(need_description or "unresolved generalized operation"), root_pressure=_pressure_for(input_value, expected_output))
            self.tasks[key] = task
        elif need_description:
            task.need_description = str(need_description)
        input_hash = _stable_hash(input_value, 24)
        for existing in task.examples:
            if _stable_hash(existing.input_value, 24) == input_hash and not _equal(existing.expected_output, expected_output):
                task.conflict_count += 1
        task.examples.append(GeneralExample("GEX:" + _stable_hash({"task": key, "input": input_value, "output": expected_output, "validation": validation, "n": len(task.examples)}), _clone(input_value), _clone(expected_output), bool(validation), str(source or "experience")))
        task.examples = task.examples[-_MAX_EXAMPLES:]
        task.updated_at = time.time()
        self._tick += 1
        if not validation:
            self._active_task_id = key
            try:
                component = self.check_and_extend(_warp_profile(task.root_pressure), source=f"general_execution:{key}", tick=self._tick)
                if component is not None:
                    task.warp_component_id = component.component_id
                    self._component_task[component.component_id] = key
            finally:
                self._active_task_id = ""
            training = [e for e in task.examples if not e.validation]
            if len(training) >= _MIN_TRAINING and len({_stable_hash(e.input_value) for e in training}) >= _MIN_DISTINCT_TRAINING and task.warp_component_id and task.candidate is None and not task.conflict_count:
                self.synthesize(key)
        elif task.candidate is not None:
            result = self.execute(key, input_value, allow_trial=True)
            if not result.get("executed") or not _equal(result.get("output"), expected_output):
                task.status = "validation_failed"
                task.candidate.status = "failed"
            else:
                task.status = "validation_active"
            self.evaluate_development()
        self._persist()
        return self.task_status(key)

    def synthesize(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(str(task_id or ""))
        if task is None: return {"synthesized": False, "reason": "unknown_task"}
        task.synthesis_attempts += 1
        synthesized = synthesize_general_program(task.examples)
        if synthesized is None:
            task.status = "unsynthesized_gap"
            self._persist()
            return {"synthesized": False, "reason": "no_general_program_in_current_span"}
        program, functions, kind = synthesized
        sequence = _primitive_sequence(program, functions)
        roots = _roots_for(sequence)
        source = program_to_python(program, functions)
        program_id = "GEN:" + _stable_hash({"task": task.task_id, "program": program, "functions": functions}, 18)
        task.candidate = GeneralProgram(program_id, program, functions, "aurora_program", kind, sequence, roots, canonical_signature(roots or AXES), _node_count(program, functions), source_python=source, status="trial", warp_component_id=task.warp_component_id)
        task.status = "candidate_trial"
        self._persist()
        return {"synthesized": True, "task_id": task.task_id, "candidate": asdict(task.candidate), "python_validation": validate_python_source(source)}

    def submit_program_candidate(
        self,
        task_id: str,
        program: Mapping[str, Any],
        *,
        functions: Optional[Mapping[str, Mapping[str, Any]]] = None,
        kind: str = "general",
        need_description: str = "",
    ) -> Dict[str, Any]:
        validation = validate_general_program(program, functions)
        if not validation.get("valid"):
            return {"accepted": False, **validation}
        key = str(task_id or "").strip()
        if not key:
            return {"accepted": False, "reason": "task_id_required"}
        task = self.tasks.get(key)
        if task is None:
            task = GeneralTask(
                key,
                str(need_description or "proposed generalized executable relation"),
                _pressure_for({}, {}, str(kind or "general")),
            )
            self.tasks[key] = task
        elif need_description:
            task.need_description = str(need_description)
        program_copy = _clone(dict(program or {}))
        functions_copy = _clone(dict(functions or {}))
        source = ""
        try:
            # Tool-bearing programs stay in the capability broker IR because
            # generated Python is intentionally unable to reach tools.
            if "TOOL" not in list(validation.get("primitive_sequence") or []):
                source = program_to_python(program_copy, functions_copy)
        except Exception:
            source = ""
        program_id = "GENIR:" + _stable_hash(
            {"task": key, "program": program_copy, "functions": functions_copy}, 18
        )
        task.candidate = GeneralProgram(
            program_id=program_id,
            program=program_copy,
            functions=functions_copy,
            entry="aurora_program",
            kind=str(kind or "general"),
            primitive_sequence=list(validation.get("primitive_sequence") or []),
            root_constraints=list(validation.get("root_constraints") or AXES),
            canonical_signature=str(validation.get("canonical_signature") or canonical_signature(AXES)),
            node_count=int(validation.get("node_count", 1) or 1),
            source_python=source,
            status="trial",
            warp_component_id=task.warp_component_id,
        )
        task.status = "candidate_trial"
        self._persist()
        return {
            "accepted": True,
            "task_id": key,
            "program_id": program_id,
            "validation": validation,
            "python_generated": bool(source),
        }

    def submit_python_candidate(self, task_id: str, source: str, *, need_description: str = "") -> Dict[str, Any]:
        validation = validate_python_source(source)
        if not validation.get("valid"):
            return {"accepted": False, **validation}
        key = str(task_id or "").strip()
        if not key: return {"accepted": False, "reason": "task_id_required"}
        task = self.tasks.get(key)
        if task is None:
            task = GeneralTask(key, str(need_description or "candidate executable relation"), _pressure_for({}, {}, "python"))
            self.tasks[key] = task
        program_id = "PYGEN:" + _stable_hash(source, 18)
        roots = list(AXES)
        task.candidate = GeneralProgram(program_id, {}, {}, "aurora_program", "python", ["FUNCTION", "CALL"], roots, canonical_signature(roots), int(validation.get("ast_nodes", 1)), source_python=str(source), status="trial", warp_component_id=task.warp_component_id)
        task.status = "candidate_trial"
        self._persist()
        return {"accepted": True, "task_id": key, "program_id": program_id, "validation": validation}

    def execute(self, task_id: str, input_value: Any, *, allow_trial: bool = True, limits: Optional[ExecutionLimits] = None) -> Dict[str, Any]:
        task = self.tasks.get(str(task_id or ""))
        if task is None or task.candidate is None: return {"executed": False, "reason": "no_candidate"}
        if task.candidate.status != "promoted" and not allow_trial: return {"executed": False, "reason": "candidate_not_promoted"}
        state = self.program_states.setdefault(task.task_id, {})
        try:
            if task.candidate.kind == "python":
                result = execute_python_sandbox(task.candidate.source_python, input_value, state, limits=limits)
                if result.get("executed"):
                    self.program_states[task.task_id] = dict(result.get("state") or {})
                    self._persist()
                return {**result, "task_id": task.task_id, "program_id": task.candidate.program_id, "status": task.candidate.status}
            executor = GeneralProgramExecutor(task_id=task.task_id, state=state, broker=self.broker, limits=limits)
            output = executor.execute(task.candidate.program, input_value, task.candidate.functions)
            self._persist()
            return {"executed": True, "task_id": task.task_id, "program_id": task.candidate.program_id, "status": task.candidate.status, "output": _clone(output), "state": _clone(state), "fuel_remaining": executor.fuel, "tool_calls": dict(executor.tool_counts)}
        except Exception as exc:
            return {"executed": False, "reason": type(exc).__name__, "detail": str(exc)}

    def observe_transition(self, machine_id: str, state: str, event: str, next_state: str, *, actions: Optional[Sequence[Mapping[str, Any]]] = None, initial_state: str = "") -> Dict[str, Any]:
        key = str(machine_id or "").strip()
        if not key: raise ValueError("machine_id_required")
        machine = self.state_machines.get(key)
        if machine is None:
            roots = list(AXES)
            machine = StateMachineDefinition(key, str(initial_state or state), {}, roots, canonical_signature(roots))
            self.state_machines[key] = machine
        transitions = machine.transitions.setdefault(str(state), {})
        record = {"next_state": str(next_state), "actions": [_clone(dict(action)) for action in list(actions or [])]}
        if event in transitions and transitions[event] != record:
            return {"accepted": False, "reason": "contradictory_transition"}
        transitions[str(event)] = record
        if sum(len(events) for events in machine.transitions.values()) >= 3:
            machine.status = "trial"
        self._persist()
        return self.machine_status(key)

    def step_machine(self, machine_id: str, instance_id: str, event: str, payload: Any = None, *, task_id: str = "", limits: Optional[ExecutionLimits] = None) -> Dict[str, Any]:
        machine = self.state_machines.get(str(machine_id or ""))
        if machine is None: return {"stepped": False, "reason": "unknown_machine"}
        instance_key = f"{machine.machine_id}:{instance_id}"
        instance = self.machine_instances.setdefault(instance_key, {"state": machine.initial_state, "data": {}, "history": []})
        current = str(instance.get("state", machine.initial_state))
        transition = machine.transitions.get(current, {}).get(str(event))
        if transition is None: return {"stepped": False, "reason": "no_transition", "state": current}
        action_results: List[Any] = []
        action_task = str(task_id or f"machine:{machine.machine_id}")
        for action in list(transition.get("actions") or []):
            op = str(action.get("op", "") or "")
            if op == "set":
                instance["data"][str(action.get("key", ""))] = _clone(action.get("value", payload))
            elif op == "tool":
                result = self.broker.call(action_task, str(action.get("name", "")), dict(action.get("arguments") or {"payload": payload}), {})
                action_results.append(_clone(result))
        instance["state"] = str(transition.get("next_state", current))
        instance["history"] = (list(instance.get("history") or []) + [{"from": current, "event": str(event), "to": instance["state"], "at": time.time()}])[-128:]
        machine.validation_count += 1
        if machine.validation_count >= 4 and machine.status != "promoted":
            machine.status = "promoted"
            machine.genealogy_ability_id = self._register_nonprogram_genealogy(
                kind="state_machine",
                identity=machine.machine_id,
                component_id=f"STATE_MACHINE:{machine.machine_id}",
                primitives=["STATE_GET", "IF", "STATE_SET"],
                roots=machine.roots,
                evidence=machine.validation_count,
                node_count=max(1, sum(len(events) for events in machine.transitions.values())),
                detail={"transitions": machine.transitions, "initial_state": machine.initial_state},
            )
        self._persist()
        return {"stepped": True, "machine_id": machine.machine_id, "instance_id": instance_id, "previous_state": current, "state": instance["state"], "data": _clone(instance["data"]), "action_results": action_results, "status": machine.status}

    def observe_tool_demonstration(self, task_id: str, input_value: Any, steps: Sequence[Mapping[str, Any]], expected_output: Any = None, *, validation: bool = False) -> Dict[str, Any]:
        key = str(task_id or "").strip()
        if not key: raise ValueError("task_id_required")
        demos = self.tool_demos.setdefault(key, [])
        demos.append({"input": _clone(input_value), "steps": [_clone(dict(step)) for step in steps], "expected_output": _clone(expected_output), "validation": bool(validation)})
        demos[:] = demos[-_MAX_EXAMPLES:]
        training = [demo for demo in demos if not demo["validation"]]
        if (
            len(training) >= 3
            and len({_stable_hash(demo["input"]) for demo in training}) >= 3
            and key not in self.tool_plans
        ):
            plan = self._synthesize_tool_plan(key, training)
            if plan is not None:
                self.tool_plans[key] = plan
        if validation and key in self.tool_plans:
            result = self.execute_tool_plan(key, input_value)
            if result.get("executed") and (expected_output is None or _equal(result.get("output"), expected_output)):
                self.tool_plans[key].validation_count += 1
                if self.tool_plans[key].validation_count >= 4 and self.tool_plans[key].status != "promoted":
                    self.tool_plans[key].status = "promoted"
                    self.tool_plans[key].genealogy_ability_id = self._register_nonprogram_genealogy(
                        kind="tool_plan",
                        identity=self.tool_plans[key].plan_id,
                        component_id=f"TOOL_PLAN:{key}",
                        primitives=["TOOL", "BLOCK"],
                        roots=self.tool_plans[key].roots,
                        evidence=self.tool_plans[key].validation_count,
                        node_count=max(1, len(self.tool_plans[key].steps)),
                        detail={"steps": self.tool_plans[key].steps},
                    )
        self._persist()
        return self.tool_plan_status(key)

    def _synthesize_tool_plan(self, task_id: str, demos: Sequence[Mapping[str, Any]]) -> Optional[ToolPlan]:
        sequences = [[str(step.get("tool", "")) for step in list(demo.get("steps") or [])] for demo in demos]
        if not sequences or any(sequence != sequences[0] for sequence in sequences[1:]) or not all(sequences[0]):
            return None
        templates: List[Dict[str, Any]] = []
        for step_index, tool_name in enumerate(sequences[0]):
            arg_templates: Dict[str, Any] = {}
            all_args = [dict(list(demo.get("steps") or [])[step_index].get("arguments") or {}) for demo in demos]
            keys = set(all_args[0]) if all_args else set()
            if any(set(args) != keys for args in all_args[1:]): return None
            for key in keys:
                values = [args[key] for args in all_args]
                if all(_equal(values[0], value) for value in values[1:]):
                    arg_templates[key] = {"const": _clone(values[0])}
                    continue
                paths = _matching_input_paths([demo["input"] for demo in demos], values)
                if not paths: return None
                arg_templates[key] = {"input_path": list(paths[0])}
            templates.append({"tool": tool_name, "arguments": arg_templates})
        roots = list(AXES)
        return ToolPlan("TPLAN:" + _stable_hash({"task": task_id, "steps": templates}), task_id, templates, roots, canonical_signature(roots))

    def execute_tool_plan(self, task_id: str, input_value: Any) -> Dict[str, Any]:
        plan = self.tool_plans.get(str(task_id or ""))
        if plan is None: return {"executed": False, "reason": "no_tool_plan"}
        results: List[Any] = []
        counts: Dict[str, int] = {}
        try:
            for step in plan.steps:
                arguments: Dict[str, Any] = {}
                for key, template in dict(step.get("arguments") or {}).items():
                    if "const" in template: arguments[key] = _clone(template["const"])
                    else: arguments[key] = _select_path(input_value, list(template.get("input_path") or []))
                results.append(_clone(self.broker.call(plan.task_id, str(step.get("tool", "")), arguments, counts)))
            return {"executed": True, "output": results[-1] if results else None, "results": results, "status": plan.status}
        except Exception as exc:
            return {"executed": False, "reason": type(exc).__name__, "detail": str(exc)}

    def evaluate_development(self) -> Tuple[List[str], List[str]]:
        promoted, dissolved = self.evaluate_warp_trials()
        for component_id in promoted:
            task = self.tasks.get(self._component_task.get(component_id, ""))
            if task and task.candidate:
                task.status = "promoted"
                task.candidate.status = "promoted"
                task.candidate.genealogy_ability_id = self._register_genealogy(task, self._warp_promoted.get(component_id))
        for component_id in dissolved:
            task = self.tasks.get(self._component_task.get(component_id, ""))
            if task:
                task.status = "dissolved"
                if task.candidate: task.candidate.status = "dissolved"
        self._persist()
        return promoted, dissolved

    def _score(self, task: GeneralTask, examples: Sequence[GeneralExample]) -> float:
        if not examples: return 0.0
        passed = 0
        for example in examples:
            result = self.execute(task.task_id, example.input_value, allow_trial=True)
            if result.get("executed") and _equal(result.get("output"), example.expected_output): passed += 1
        return passed / len(examples)

    def _register_genealogy(self, task: GeneralTask, component: Optional[WarpComponent]) -> str:
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        candidate = task.candidate
        if genealogy is None or candidate is None: return ""
        payload = {"task_id": task.task_id, "program_id": candidate.program_id, "component_id": candidate.warp_component_id, "constraints": candidate.root_constraints, "canonical_signature": candidate.canonical_signature, "primitive_sequence": candidate.primitive_sequence, "program": candidate.program, "functions": candidate.functions, "source_python": candidate.source_python, "program_kind": candidate.kind, "parent_ids": list(getattr(component, "parent_ids", []) or []), "trial_score": float(getattr(component, "trial_score_ema", 0.0) or 0.0), "training_examples": len([e for e in task.examples if not e.validation]), "validation_examples": len([e for e in task.examples if e.validation]), "node_count": candidate.node_count, "need_description": task.need_description}
        if hasattr(genealogy, "register_emergent_general_execution"):
            try:
                result = dict(genealogy.register_emergent_general_execution(payload) or {})
                return str(result.get("ability_id", "") or "")
            except Exception:
                return ""
        return ""

    def _register_nonprogram_genealogy(
        self,
        *,
        kind: str,
        identity: str,
        component_id: str,
        primitives: Sequence[str],
        roots: Sequence[str],
        evidence: int,
        node_count: int,
        detail: Mapping[str, Any],
    ) -> str:
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        if genealogy is None or not hasattr(genealogy, "register_emergent_general_execution"):
            return ""
        payload = {
            "task_id": str(identity),
            "program_id": str(identity),
            "component_id": str(component_id),
            "constraints": list(roots or AXES),
            "canonical_signature": canonical_signature(list(roots or AXES)),
            "primitive_sequence": list(primitives),
            "program": dict(detail or {}),
            "functions": {},
            "source_python": "",
            "program_kind": str(kind),
            "parent_ids": [],
            "trial_score": 1.0,
            "training_examples": max(0, int(evidence)),
            "validation_examples": max(0, int(evidence)),
            "node_count": max(1, int(node_count)),
            "need_description": f"emergent {kind}",
        }
        try:
            result = dict(genealogy.register_emergent_general_execution(payload) or {})
            return str(result.get("ability_id", "") or "")
        except Exception:
            return ""

    def task_status(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(str(task_id or ""))
        if task is None: return {"exists": False, "task_id": str(task_id or "")}
        training = [e for e in task.examples if not e.validation]
        validation = [e for e in task.examples if e.validation]
        return {"exists": True, "task_id": task.task_id, "status": task.status, "need_description": task.need_description, "training_examples": len(training), "validation_examples": len(validation), "distinct_training_inputs": len({_stable_hash(e.input_value) for e in training}), "distinct_validation_inputs": len({_stable_hash(e.input_value) for e in validation}), "conflicts": task.conflict_count, "warp_component_id": task.warp_component_id, "candidate": asdict(task.candidate) if task.candidate else None}

    def machine_status(self, machine_id: str) -> Dict[str, Any]:
        machine = self.state_machines.get(str(machine_id or ""))
        if machine is None: return {"exists": False, "machine_id": str(machine_id or "")}
        return {"exists": True, **asdict(machine), "transition_count": sum(len(events) for events in machine.transitions.values()), "instances": sum(1 for key in self.machine_instances if key.startswith(machine.machine_id + ":"))}

    def tool_plan_status(self, task_id: str) -> Dict[str, Any]:
        plan = self.tool_plans.get(str(task_id or ""))
        return {"exists": plan is not None, **(asdict(plan) if plan else {"task_id": str(task_id or "")})}

    def trace_to_roots(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(str(task_id or ""))
        if task is None or task.candidate is None: return {"available": False, "task_id": str(task_id or "")}
        primitive_lineage = []
        for name in task.candidate.primitive_sequence:
            spec = GENERAL_PRIMITIVES.get(name)
            if spec: primitive_lineage.append({"primitive": name, "roots": list(spec.roots), "description": spec.description})
        return {"available": True, "task_id": task.task_id, "program_id": task.candidate.program_id, "program_kind": task.candidate.kind, "status": task.candidate.status, "root_constraints": task.candidate.root_constraints, "canonical_signature": task.candidate.canonical_signature, "primitive_lineage": primitive_lineage, "warp_component_id": task.warp_component_id, "genealogy_ability_id": task.candidate.genealogy_ability_id}

    def status(self) -> Dict[str, Any]:
        return {"tasks": len(self.tasks), "candidate_trials": sum(1 for task in self.tasks.values() if task.candidate and task.candidate.status == "trial"), "promoted": sum(1 for task in self.tasks.values() if task.candidate and task.candidate.status == "promoted"), "state_machines": len(self.state_machines), "machine_instances": len(self.machine_instances), "tool_plans": len(self.tool_plans), "registered_capabilities": len(self.broker.manifest()), "primitive_count": len(GENERAL_PRIMITIVES), "storage_path": self.storage_path, "warp": self.warp_status()}

    def _load(self) -> None:
        if not self.persist or not os.path.exists(self.storage_path): return
        try:
            raw = dict(json.load(open(self.storage_path, "r", encoding="utf-8")) or {})
            self._tick = int(raw.get("tick", 0) or 0)
            for key, item in dict(raw.get("tasks") or {}).items():
                rec = dict(item or {})
                candidate = GeneralProgram(**dict(rec.get("candidate") or {})) if rec.get("candidate") else None
                examples = [GeneralExample(**dict(example or {})) for example in list(rec.get("examples") or [])]
                self.tasks[key] = GeneralTask(task_id=str(rec.get("task_id", key)), need_description=str(rec.get("need_description", "")), root_pressure=dict(rec.get("root_pressure") or {}), examples=examples, candidate=candidate, conflict_count=int(rec.get("conflict_count", 0)), synthesis_attempts=int(rec.get("synthesis_attempts", 0)), status=str(rec.get("status", "observing")), warp_component_id=str(rec.get("warp_component_id", "")), created_at=float(rec.get("created_at", time.time())), updated_at=float(rec.get("updated_at", time.time())))
                if self.tasks[key].warp_component_id: self._component_task[self.tasks[key].warp_component_id] = key
            self.program_states = dict(raw.get("program_states") or {})
            self.tool_plans = {key: ToolPlan(**dict(value or {})) for key, value in dict(raw.get("tool_plans") or {}).items()}
            self.tool_demos = dict(raw.get("tool_demos") or {})
            self.state_machines = {key: StateMachineDefinition(**dict(value or {})) for key, value in dict(raw.get("state_machines") or {}).items()}
            self.machine_instances = dict(raw.get("machine_instances") or {})
            warp = dict(raw.get("warp_state") or {})
            for component_id, item in dict(warp.get("trials") or {}).items():
                component = _restore_component(item)
                self._warp_trials[component_id] = component
            for component_id, item in dict(warp.get("promoted") or {}).items():
                component = _restore_component(item)
                self._warp_promoted[component_id] = component
        except Exception:
            self.tasks = {}
            self.program_states = {}
            self.tool_plans = {}
            self.tool_demos = {}
            self.state_machines = {}
            self.machine_instances = {}

    def _persist(self) -> None:
        if not self.persist: return
        os.makedirs(self.state_dir, exist_ok=True)
        payload = {"schema_version": 1, "tick": self._tick, "tasks": {key: asdict(value) for key, value in self.tasks.items()}, "program_states": self.program_states, "tool_plans": {key: asdict(value) for key, value in self.tool_plans.items()}, "tool_demos": self.tool_demos, "state_machines": {key: asdict(value) for key, value in self.state_machines.items()}, "machine_instances": self.machine_instances, "capability_manifest": self.broker.manifest(), "warp_state": {"trials": {key: _component_record(value) for key, value in self._warp_trials.items()}, "promoted": {key: _component_record(value) for key, value in self._warp_promoted.items()}}, "updated_at": time.time()}
        atomic_write_json(Path(self.storage_path), payload, indent=2, default=str)


def _matching_input_paths(inputs: Sequence[Any], outputs: Sequence[Any]) -> List[Tuple[Any, ...]]:
    if not inputs or len(inputs) != len(outputs): return []
    candidates = list(_iter_paths(inputs[0]))
    matches: List[Tuple[Any, ...]] = []
    for path, _ in candidates:
        try:
            if all(_equal(_select_path(inputs[index], path), outputs[index]) for index in range(len(inputs))): matches.append(path)
        except Exception:
            continue
    return sorted(matches, key=lambda path: (len(path), tuple(str(x) for x in path)))


def _iter_paths(value: Any, prefix: Tuple[Any, ...] = (), depth: int = 0) -> Iterable[Tuple[Tuple[Any, ...], Any]]:
    yield prefix, value
    if depth >= 5: return
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda item: str(item)):
            yield from _iter_paths(value[key], prefix + (key,), depth + 1)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _iter_paths(item, prefix + (index,), depth + 1)


def _select_path(value: Any, path: Sequence[Any]) -> Any:
    current = value
    for part in path:
        current = current[part]
    return _clone(current)


def _component_record(component: WarpComponent) -> Dict[str, Any]:
    return {"component_id": component.component_id, "level": component.level, "axis_profile": dict(component.axis_profile), "parent_ids": list(component.parent_ids), "name": component.name, "parameters": _clone(component.parameters), "trial_tick": int(component.trial_tick), "trial_score_ema": float(component.trial_score_ema), "promoted": bool(component.promoted), "dissolved": bool(component.dissolved), "created_at": float(component.created_at), "sixth_axis_signal": float(component.sixth_axis_signal), "topology_gap_ref": component.topology_gap_ref}


def _restore_component(record: Mapping[str, Any]) -> WarpComponent:
    rec = dict(record or {})
    return WarpComponent(component_id=str(rec.get("component_id", "")), level=str(rec.get("level", "general_execution_foundry")), axis_profile={str(key): float(value or 0.0) for key, value in dict(rec.get("axis_profile") or {}).items()}, parent_ids=[str(value) for value in list(rec.get("parent_ids") or [])], name=rec.get("name"), parameters=_clone(dict(rec.get("parameters") or {})), trial_tick=int(rec.get("trial_tick", 0)), trial_score_ema=float(rec.get("trial_score_ema", 0.0)), promoted=bool(rec.get("promoted", False)), dissolved=bool(rec.get("dissolved", False)), created_at=float(rec.get("created_at", time.time())), sixth_axis_signal=float(rec.get("sixth_axis_signal", 0.0)), topology_gap_ref=rec.get("topology_gap_ref"))


__all__ = [
    "AuroraGeneralExecutionFoundry", "CapabilityBroker", "CapabilitySpec", "ExecutionLimits",
    "GeneralProgramExecutor", "GENERAL_PRIMITIVES", "synthesize_general_program",
    "validate_general_program", "validate_python_source", "execute_python_sandbox", "program_to_python",
]
