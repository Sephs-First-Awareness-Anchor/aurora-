"""
aurora_operational_synthesis.py
===============================

Constraint-native operational synthesis chamber for Aurora.

The chamber gives Aurora an executable but quarantined substrate in which a
repeatedly needed operation can be composed from root-derived primitives,
tested against lived examples, challenged with unseen cases, and promoted into
constraint genealogy only after demonstrated generalization.

It does not generate Python source, call eval/exec, or install a prefabricated
catalogue of domain abilities. Programs are small typed data-flow trees whose
atomic operations declare X/T/N/B/A ancestry. The first supported structural
families are deliberately general:

* projection and reconstruction of sequences or mappings;
* scalar arithmetic over selected values;
* bounded comparisons and logical composition.

These are an operational substrate, not named skills. A positional transform,
a numeric relation, a field projection, or a predicate can all emerge from the
same primitives when examples exert sufficient pressure.

Developmental law:

    repeated unmet operation
        -> root pressure / WARP trial
        -> enumerated constraint-derived candidate programs
        -> exact training fit with simplicity pressure
        -> unseen validation
        -> WARP promotion
        -> genealogy admission

Authors: Sunni (Sir) Morningstar and Ceph
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from aurora_persistence_utils import atomic_write_json
from aurora_warp_protocol import CoverageGap, WarpCapable, WarpComponent
from aurora_internal.aurora_meaning_evolution import canonical_signature

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
_NEGATIVE_ISTATE = {
    "X": "I_ISNT",
    "T": "I_CANNOT",
    "N": "I_DONOT",
    "B": "I_SOUGHT",
    "A": "I_DIDNT",
}
_POSITIVE_ISTATE = {
    "X": "I_IS",
    "T": "I_CAN",
    "N": "I_DO",
    "B": "I_SAW",
    "A": "I_DID",
}

_MIN_TRAINING_EXAMPLES = 3
_MIN_DISTINCT_TRAINING_INPUTS = 3
_MIN_VALIDATION_EXAMPLES = 2
_MIN_DISTINCT_VALIDATION_INPUTS = 2
_MAX_TASKS = 128
_MAX_EXAMPLES_PER_TASK = 96
_MAX_PROGRAM_NODES = 48
_MAX_ENUMERATED_SIGNATURES = 12000
_MAX_NUMERIC_DEPTH = 2
_EPSILON = 1e-9


@dataclass(frozen=True)
class PrimitiveSpec:
    name: str
    roots: Tuple[str, ...]
    description: str
    arity: int = 0


# Atomic operators are described through the five roots. Parameterized SELECT
# and CONST nodes are structural uses of the same primitives, not separate
# abilities for every index or literal.
PRIMITIVES: Dict[str, PrimitiveSpec] = {
    "INPUT": PrimitiveSpec("INPUT", ("X",), "admit the current input as an existing structure"),
    "SELECT": PrimitiveSpec("SELECT", ("X", "B", "A"), "select one bounded part of an admitted structure", 1),
    "CONST": PrimitiveSpec("CONST", ("X", "A"), "admit a selected invariant value", 1),
    "SEQUENCE": PrimitiveSpec("SEQUENCE", ("X", "T", "B", "A"), "construct an ordered bounded output", -1),
    "MAPPING": PrimitiveSpec("MAPPING", ("X", "B", "A"), "construct a keyed bounded output", -1),
    "ADD": PrimitiveSpec("ADD", ("N", "A"), "combine numeric magnitude through directed change", 2),
    "SUB": PrimitiveSpec("SUB", ("T", "N", "A"), "express numeric difference across ordered states", 2),
    "MUL": PrimitiveSpec("MUL", ("N", "B", "A"), "scale one magnitude through another bounded magnitude", 2),
    "DIV": PrimitiveSpec("DIV", ("N", "B", "A"), "relate magnitudes through a protected ratio", 2),
    "NEG": PrimitiveSpec("NEG", ("N", "B"), "reverse numeric polarity", 1),
    "ABS": PrimitiveSpec("ABS", ("X", "N", "B"), "preserve numeric magnitude while removing polarity", 1),
    "EQ": PrimitiveSpec("EQ", ("X", "B", "A"), "select whether two structures are equivalent", 2),
    "NE": PrimitiveSpec("NE", ("X", "B", "A"), "select whether two structures remain distinct", 2),
    "LT": PrimitiveSpec("LT", ("T", "B", "A"), "select an ordered lower relation", 2),
    "LE": PrimitiveSpec("LE", ("T", "B", "A"), "select a bounded lower-or-equal relation", 2),
    "GT": PrimitiveSpec("GT", ("T", "B", "A"), "select an ordered greater relation", 2),
    "GE": PrimitiveSpec("GE", ("T", "B", "A"), "select a bounded greater-or-equal relation", 2),
    "NOT": PrimitiveSpec("NOT", ("X", "B", "A"), "invert a bounded truth relation", 1),
    "AND": PrimitiveSpec("AND", ("N", "B", "A"), "require joint truth across bounded relations", 2),
    "OR": PrimitiveSpec("OR", ("N", "B", "A"), "admit either of two bounded relations", 2),
}


@dataclass
class SynthesisExample:
    example_id: str
    input_value: Any
    expected_output: Any
    validation: bool = False
    source: str = "experience"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SynthesizedProgram:
    program_id: str
    tree: Dict[str, Any]
    primitive_sequence: List[str]
    root_constraints: List[str]
    canonical_signature: str
    node_count: int
    training_score: float
    validation_score: float = 0.0
    status: str = "trial"
    created_at: float = field(default_factory=time.time)
    warp_component_id: str = ""
    genealogy_ability_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SynthesisTask:
    task_id: str
    need_description: str
    structural_signature: str = ""
    root_pressure: Dict[str, float] = field(default_factory=dict)
    examples: List[SynthesisExample] = field(default_factory=list)
    candidate: Optional[SynthesizedProgram] = None
    conflict_count: int = 0
    synthesis_attempts: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    warp_component_id: str = ""
    status: str = "observing"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return payload


def _stable_hash(payload: Any, length: int = 14) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _json_clone(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return copy.deepcopy(value)


def _values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if not (math.isfinite(float(left)) and math.isfinite(float(right))):
            return left == right
        return abs(float(left) - float(right)) <= _EPSILON
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_values_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left.keys()) == set(right.keys()) and all(_values_equal(left[k], right[k]) for k in left)
    return left == right


def _type_shape(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return type(value).__name__
    if isinstance(value, Mapping):
        return {
            "kind": "mapping",
            "keys": sorted(str(k) for k in value.keys()),
            "values": {str(k): _type_shape(value[k], depth + 1) for k in sorted(value, key=lambda x: str(x))},
        }
    if isinstance(value, (list, tuple)):
        return {
            "kind": "sequence",
            "length": len(value),
            "items": [_type_shape(v, depth + 1) for v in value[:8]],
        }
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if value is None:
        return "none"
    return type(value).__name__


def _normalize_pressure(pressure: Mapping[str, Any]) -> Dict[str, float]:
    vals = {ax: max(0.0, float(dict(pressure or {}).get(ax, 0.0) or 0.0)) for ax in AXES}
    total = sum(vals.values()) or 1.0
    return {ax: round(vals[ax] / total, 6) for ax in AXES}


def _task_pressure(input_value: Any, expected_output: Any) -> Dict[str, float]:
    """Represent the unmet operation as pressure on the five roots."""
    pressure = {"X": 0.60, "T": 0.55, "N": 0.90, "B": 0.75, "A": 0.85}
    if isinstance(input_value, (list, tuple)) or isinstance(expected_output, (list, tuple)):
        pressure["T"] += 0.30
        pressure["B"] += 0.25
    if isinstance(input_value, Mapping) or isinstance(expected_output, Mapping):
        pressure["X"] += 0.20
        pressure["B"] += 0.30
    if isinstance(expected_output, bool):
        pressure["B"] += 0.25
        pressure["A"] += 0.15
    return _normalize_pressure(pressure)


def _warp_profile(root_pressure: Mapping[str, Any]) -> Dict[str, float]:
    root = _normalize_pressure(root_pressure)
    profile: Dict[str, float] = {}
    for ax in AXES:
        magnitude = float(root.get(ax, 0.0) or 0.0)
        profile[_NEGATIVE_ISTATE[ax]] = round(magnitude, 6)
        profile[_POSITIVE_ISTATE[ax]] = round(magnitude * 0.12, 6)
    profile.update({
        "REC_SURFACE": 0.10,
        "REC_SHALLOW": 0.20,
        "REC_MODERATE": 0.65,
        "REC_DEEP": 0.72,
        "REC_CORE": 0.55,
    })
    return profile


def _iter_paths(value: Any, prefix: Tuple[Any, ...] = (), depth: int = 0) -> Iterable[Tuple[Tuple[Any, ...], Any]]:
    yield prefix, value
    if depth >= 4:
        return
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda x: str(x)):
            yield from _iter_paths(value[key], prefix + (key,), depth + 1)
    elif isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            yield from _iter_paths(item, prefix + (idx,), depth + 1)


def _select_path(value: Any, path: Sequence[Any]) -> Any:
    current = value
    for part in path:
        if isinstance(current, Mapping):
            current = current[part]
        elif isinstance(current, (list, tuple)) and isinstance(part, int):
            current = current[part]
        else:
            raise KeyError(path)
    return current


def _node_count(tree: Mapping[str, Any]) -> int:
    if not isinstance(tree, Mapping):
        return 0
    total = 1
    for arg in list(tree.get("args") or []):
        if isinstance(arg, Mapping):
            total += _node_count(arg)
    for child in dict(tree.get("fields") or {}).values():
        if isinstance(child, Mapping):
            total += _node_count(child)
    return total


def _primitive_sequence(tree: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    def walk(node: Mapping[str, Any]) -> None:
        op = str(node.get("op", "") or "")
        if op:
            out.append(op)
        for arg in list(node.get("args") or []):
            if isinstance(arg, Mapping):
                walk(arg)
        for child in dict(node.get("fields") or {}).values():
            if isinstance(child, Mapping):
                walk(child)
    walk(tree)
    return out


def _program_roots(tree: Mapping[str, Any]) -> List[str]:
    roots: List[str] = []
    for name in _primitive_sequence(tree):
        spec = PRIMITIVES.get(name)
        if spec:
            roots.extend(spec.roots)
    return [ax for ax in AXES if ax in set(roots)]


def execute_program(tree: Mapping[str, Any], input_value: Any, *, budget: int = 256) -> Any:
    """Execute a pure bounded synthesis tree. No source execution is possible."""
    remaining = [max(1, int(budget))]

    def run(node: Mapping[str, Any]) -> Any:
        remaining[0] -= 1
        if remaining[0] < 0:
            raise RuntimeError("operation_budget_exceeded")
        op = str(node.get("op", "") or "")
        if op == "INPUT":
            return _json_clone(input_value)
        if op == "SELECT":
            return _json_clone(_select_path(input_value, list(node.get("path") or [])))
        if op == "CONST":
            return _json_clone(node.get("value"))
        if op == "SEQUENCE":
            return [run(arg) for arg in list(node.get("args") or [])]
        if op == "MAPPING":
            return {str(k): run(v) for k, v in dict(node.get("fields") or {}).items()}

        args = [run(arg) for arg in list(node.get("args") or [])]
        if op == "ADD": return args[0] + args[1]
        if op == "SUB": return args[0] - args[1]
        if op == "MUL": return args[0] * args[1]
        if op == "DIV":
            if abs(float(args[1])) <= _EPSILON:
                raise ZeroDivisionError("protected_ratio_zero")
            return args[0] / args[1]
        if op == "NEG": return -args[0]
        if op == "ABS": return abs(args[0])
        if op == "EQ": return _values_equal(args[0], args[1])
        if op == "NE": return not _values_equal(args[0], args[1])
        if op == "LT": return args[0] < args[1]
        if op == "LE": return args[0] <= args[1]
        if op == "GT": return args[0] > args[1]
        if op == "GE": return args[0] >= args[1]
        if op == "NOT": return not bool(args[0])
        if op == "AND": return bool(args[0]) and bool(args[1])
        if op == "OR": return bool(args[0]) or bool(args[1])
        raise ValueError(f"unknown_synthesis_primitive:{op}")

    return run(dict(tree or {}))


def _program_signature(tree: Mapping[str, Any]) -> str:
    return json.dumps(tree, sort_keys=True, separators=(",", ":"), default=str)


def _candidate_output_signature(tree: Mapping[str, Any], examples: Sequence[SynthesisExample]) -> Optional[str]:
    values: List[Any] = []
    try:
        for example in examples:
            values.append(execute_program(tree, example.input_value))
    except Exception:
        return None
    return _stable_hash(values, 24)


def _fits(tree: Mapping[str, Any], examples: Sequence[SynthesisExample]) -> bool:
    try:
        return all(_values_equal(execute_program(tree, e.input_value), e.expected_output) for e in examples)
    except Exception:
        return False


def _select_candidates(examples: Sequence[SynthesisExample]) -> List[Dict[str, Any]]:
    if not examples:
        return []
    path_sets: List[Dict[Tuple[Any, ...], Any]] = [dict(_iter_paths(e.input_value)) for e in examples]
    common_paths = set(path_sets[0])
    for paths in path_sets[1:]:
        common_paths &= set(paths)
    candidates: List[Dict[str, Any]] = []
    for path in sorted(common_paths, key=lambda p: (len(p), tuple(str(x) for x in p))):
        candidates.append({"op": "SELECT", "path": list(path)})
    return candidates


def _constant_candidate(outputs: Sequence[Any]) -> Optional[Dict[str, Any]]:
    if outputs and all(_values_equal(outputs[0], item) for item in outputs[1:]):
        return {"op": "CONST", "value": _json_clone(outputs[0])}
    return None


def _synthesize_numeric_scalar(examples: Sequence[SynthesisExample], outputs: Sequence[Any]) -> Optional[Dict[str, Any]]:
    if not outputs or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in outputs):
        return None
    atoms = _select_candidates(examples)
    const = _constant_candidate(outputs)
    if const is not None:
        atoms.append(const)
    for value in (-2, -1, 0, 1, 2):
        atoms.append({"op": "CONST", "value": value})

    valid_atoms: List[Dict[str, Any]] = []
    for atom in atoms:
        sig = _candidate_output_signature(atom, examples)
        if sig is not None:
            valid_atoms.append(atom)
            if _fits(atom, [SynthesisExample("tmp", e.input_value, outputs[i]) for i, e in enumerate(examples)]):
                return atom

    target_examples = [SynthesisExample(f"target:{i}", e.input_value, outputs[i]) for i, e in enumerate(examples)]
    unary_ops = ("NEG", "ABS")
    binary_ops = ("ADD", "SUB", "MUL", "DIV")
    frontier = list(valid_atoms)
    seen_programs = {_program_signature(p) for p in frontier}
    seen_outputs: Dict[str, Dict[str, Any]] = {}
    for p in frontier:
        sig = _candidate_output_signature(p, examples)
        if sig:
            seen_outputs.setdefault(sig, p)

    for _depth in range(_MAX_NUMERIC_DEPTH):
        new_frontier: List[Dict[str, Any]] = []
        pool = list(seen_outputs.values())
        for child in frontier:
            for op in unary_ops:
                node = {"op": op, "args": [child]}
                key = _program_signature(node)
                if key in seen_programs or _node_count(node) > _MAX_PROGRAM_NODES:
                    continue
                seen_programs.add(key)
                sig = _candidate_output_signature(node, examples)
                if sig is None or sig in seen_outputs:
                    continue
                seen_outputs[sig] = node
                new_frontier.append(node)
                if _fits(node, target_examples):
                    return node
                if len(seen_outputs) >= _MAX_ENUMERATED_SIGNATURES:
                    return None
        for left in pool:
            for right in pool:
                for op in binary_ops:
                    node = {"op": op, "args": [left, right]}
                    key = _program_signature(node)
                    if key in seen_programs or _node_count(node) > _MAX_PROGRAM_NODES:
                        continue
                    seen_programs.add(key)
                    sig = _candidate_output_signature(node, examples)
                    if sig is None or sig in seen_outputs:
                        continue
                    seen_outputs[sig] = node
                    new_frontier.append(node)
                    if _fits(node, target_examples):
                        return node
                    if len(seen_outputs) >= _MAX_ENUMERATED_SIGNATURES:
                        return None
        frontier = new_frontier
        if not frontier:
            break
    return None


def _synthesize_boolean_scalar(examples: Sequence[SynthesisExample], outputs: Sequence[Any]) -> Optional[Dict[str, Any]]:
    if not outputs or not all(isinstance(v, bool) for v in outputs):
        return None
    target_examples = [SynthesisExample(f"bool:{i}", e.input_value, outputs[i]) for i, e in enumerate(examples)]
    atoms = _select_candidates(examples)
    const = _constant_candidate(outputs)
    if const is not None:
        return const
    numeric_atoms = []
    for atom in atoms:
        sig = _candidate_output_signature(atom, examples)
        if sig is None:
            continue
        try:
            vals = [execute_program(atom, e.input_value) for e in examples]
        except Exception:
            continue
        if all(isinstance(v, (int, float, str, bool)) for v in vals):
            numeric_atoms.append(atom)
    constants = [{"op": "CONST", "value": v} for v in (-1, 0, 1, True, False)]
    pool = numeric_atoms + constants
    for left in pool:
        for right in pool:
            for op in ("EQ", "NE", "LT", "LE", "GT", "GE"):
                node = {"op": op, "args": [left, right]}
                if _fits(node, target_examples):
                    return node
    return None


def _synthesize_value(examples: Sequence[SynthesisExample], outputs: Sequence[Any]) -> Optional[Dict[str, Any]]:
    if not examples or len(examples) != len(outputs):
        return None

    # Direct input/path projection is the simplest possible explanation.
    target_examples = [SynthesisExample(f"projection:{i}", e.input_value, outputs[i]) for i, e in enumerate(examples)]
    for candidate in _select_candidates(examples):
        if _fits(candidate, target_examples):
            return candidate
    const = _constant_candidate(outputs)
    if const is not None:
        return const

    if all(isinstance(v, (list, tuple)) for v in outputs):
        lengths = {len(v) for v in outputs}
        if len(lengths) != 1:
            return None
        length = next(iter(lengths))
        args: List[Dict[str, Any]] = []
        for idx in range(length):
            child_outputs = [v[idx] for v in outputs]
            child = _synthesize_value(examples, child_outputs)
            if child is None:
                return None
            args.append(child)
        node = {"op": "SEQUENCE", "args": args}
        return node if _node_count(node) <= _MAX_PROGRAM_NODES else None

    if all(isinstance(v, Mapping) for v in outputs):
        keys = [set(v.keys()) for v in outputs]
        if not keys or any(k != keys[0] for k in keys[1:]):
            return None
        fields: Dict[str, Dict[str, Any]] = {}
        for key in sorted(keys[0], key=lambda x: str(x)):
            child_outputs = [v[key] for v in outputs]
            child = _synthesize_value(examples, child_outputs)
            if child is None:
                return None
            fields[str(key)] = child
        node = {"op": "MAPPING", "fields": fields}
        return node if _node_count(node) <= _MAX_PROGRAM_NODES else None

    numeric = _synthesize_numeric_scalar(examples, outputs)
    if numeric is not None:
        return numeric
    boolean = _synthesize_boolean_scalar(examples, outputs)
    if boolean is not None:
        return boolean
    return None


def synthesize_program(examples: Sequence[SynthesisExample]) -> Optional[Dict[str, Any]]:
    training = [e for e in examples if not e.validation]
    if len(training) < _MIN_TRAINING_EXAMPLES:
        return None
    outputs = [e.expected_output for e in training]
    tree = _synthesize_value(training, outputs)
    if tree is None or _node_count(tree) > _MAX_PROGRAM_NODES:
        return None
    return tree


def describe_program(tree: Mapping[str, Any]) -> str:
    op = str(dict(tree or {}).get("op", "") or "")
    if op == "SELECT":
        path = list(dict(tree or {}).get("path") or [])
        return "select input" + (" at " + ".".join(str(x) for x in path) if path else "")
    if op == "CONST":
        return f"emit invariant {dict(tree or {}).get('value')!r}"
    if op == "SEQUENCE":
        return "construct sequence [" + ", ".join(describe_program(x) for x in list(dict(tree or {}).get("args") or [])) + "]"
    if op == "MAPPING":
        return "construct mapping {" + ", ".join(f"{k}: {describe_program(v)}" for k, v in dict(dict(tree or {}).get("fields") or {}).items()) + "}"
    args = list(dict(tree or {}).get("args") or [])
    if len(args) == 1:
        return f"{op.lower()}({describe_program(args[0])})"
    if len(args) == 2:
        return f"{op.lower()}({describe_program(args[0])}, {describe_program(args[1])})"
    return op.lower()


def _component_record(component: WarpComponent) -> Dict[str, Any]:
    return {
        "component_id": component.component_id,
        "level": component.level,
        "axis_profile": dict(component.axis_profile),
        "parent_ids": list(component.parent_ids),
        "name": component.name,
        "parameters": copy.deepcopy(component.parameters),
        "trial_tick": int(component.trial_tick),
        "trial_score_ema": float(component.trial_score_ema),
        "promoted": bool(component.promoted),
        "dissolved": bool(component.dissolved),
        "created_at": float(component.created_at),
        "sixth_axis_signal": float(component.sixth_axis_signal),
        "topology_gap_ref": component.topology_gap_ref,
    }


def _restore_component(record: Mapping[str, Any]) -> WarpComponent:
    rec = dict(record or {})
    return WarpComponent(
        component_id=str(rec.get("component_id", "") or ""),
        level=str(rec.get("level", "operational_synthesis") or "operational_synthesis"),
        axis_profile={str(k): float(v or 0.0) for k, v in dict(rec.get("axis_profile") or {}).items()},
        parent_ids=[str(x) for x in list(rec.get("parent_ids") or [])],
        name=rec.get("name"),
        parameters=copy.deepcopy(dict(rec.get("parameters") or {})),
        trial_tick=int(rec.get("trial_tick", 0) or 0),
        trial_score_ema=float(rec.get("trial_score_ema", 0.0) or 0.0),
        promoted=bool(rec.get("promoted", False)),
        dissolved=bool(rec.get("dissolved", False)),
        created_at=float(rec.get("created_at", time.time()) or time.time()),
        sixth_axis_signal=float(rec.get("sixth_axis_signal", 0.0) or 0.0),
        topology_gap_ref=rec.get("topology_gap_ref"),
    )


class AuroraOperationalSynthesisChamber(WarpCapable):
    """Quarantined synthesis and promotion of previously missing operations."""

    def __init__(
        self,
        *,
        state_dir: str = "aurora_state",
        persist: bool = True,
        genealogy: Any = None,
    ) -> None:
        self.state_dir = str(state_dir or "aurora_state")
        self.persist = bool(persist)
        self.storage_path = os.path.join(self.state_dir, "operational_synthesis_state.json")
        self.systems: Dict[str, Any] = {}
        self._tasks: Dict[str, SynthesisTask] = {}
        self._active_task_id: str = ""
        self._profile_task: Dict[str, str] = {}
        self._component_task: Dict[str, str] = {}
        self._tick = 0
        self._init_warp(genealogy=genealogy)
        self._load()

    def attach_systems(self, systems: Mapping[str, Any]) -> None:
        self.systems = dict(systems or {}) if not isinstance(systems, dict) else systems
        genealogy = self.systems.get("genealogy")
        if genealogy is not None:
            self.set_warp_genealogy(genealogy)
            # Surface and subsurface boots may attach at different times. A
            # program already promoted while genealogy was unavailable is
            # admitted the moment a real genealogy object becomes reachable.
            if hasattr(genealogy, "register_emergent_operational_synthesis"):
                for task in self._tasks.values():
                    if (
                        task.candidate is not None
                        and task.candidate.status == "promoted"
                        and not task.candidate.genealogy_ability_id
                    ):
                        component = self._warp_promoted.get(task.warp_component_id)
                        task.candidate.genealogy_ability_id = self._register_genealogy(task, component)
        # Expose one domain-neutral intake seam. Other Aurora organs can feed
        # structured before/after evidence without importing this module or
        # acquiring authority over synthesis/promotion.
        if isinstance(self.systems, dict):
            self.systems["submit_operational_example"] = self.observe_example
            self.systems["submit_operational_experience"] = self.observe_experience
        sedi = self.systems.get("sedimemory")
        if sedi is not None:
            try:
                self.connect_sedimemory(sedi)
            except Exception:
                pass

    def _warp_level_name(self) -> str:
        return "operational_synthesis"

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        profiles: Dict[str, Dict[str, float]] = {}
        for name, spec in PRIMITIVES.items():
            profile: Dict[str, float] = {}
            for ax in AXES:
                active = ax in spec.roots
                profile[_POSITIVE_ISTATE[ax]] = 0.72 if active else 0.03
                profile[_NEGATIVE_ISTATE[ax]] = 0.10 if active else 0.02
            profile["REC_SURFACE"] = 0.10
            profile["REC_SHALLOW"] = 0.20
            profile["REC_MODERATE"] = 0.45
            profile["REC_DEEP"] = 0.30
            profile["REC_CORE"] = 0.15
            profiles[f"primitive:{name}"] = profile
        for task in self._tasks.values():
            if task.candidate and task.candidate.status == "promoted" and task.warp_component_id:
                comp = self._warp_promoted.get(task.warp_component_id)
                if comp is not None:
                    profiles[comp.component_id] = dict(comp.axis_profile)
        return profiles

    def _warp_params(self, gap: CoverageGap, parent_ids: List[str]) -> Dict[str, Any]:
        task_id = self._active_task_id or self._profile_task.get(_stable_hash(gap.axis_profile, 20), "")
        task = self._tasks.get(task_id)
        roots = [ax for ax in AXES if task and float(task.root_pressure.get(ax, 0.0) or 0.0) >= 0.10]
        return {
            "task_id": task_id,
            "need_description": str(task.need_description if task else ""),
            "root_constraints": roots or list(AXES),
            "canonical_signature": canonical_signature(roots or AXES),
            "parent_ids": list(parent_ids or []),
            "origin": "persistent_unmet_operation",
        }

    def _integrate_warp(self, component: WarpComponent) -> None:
        task_id = str(dict(component.parameters or {}).get("task_id", "") or self._active_task_id)
        task = self._tasks.get(task_id)
        if task is None:
            return
        task.warp_component_id = component.component_id
        self._component_task[component.component_id] = task_id
        task.status = "warp_trial"
        if task.candidate is not None:
            task.candidate.warp_component_id = component.component_id
        self._persist()

    def _score_trial(self, component: WarpComponent) -> float:
        task = self._tasks.get(self._component_task.get(component.component_id, ""))
        if task is None or task.candidate is None:
            return 0.0
        training = [e for e in task.examples if not e.validation]
        validation = [e for e in task.examples if e.validation]
        if len(validation) < _MIN_VALIDATION_EXAMPLES:
            return 0.0
        distinct_validation = {_stable_hash(e.input_value, 18) for e in validation}
        if len(distinct_validation) < _MIN_DISTINCT_VALIDATION_INPUTS:
            return 0.0
        train_score = self._score_examples(task.candidate.tree, training)
        validation_score = self._score_examples(task.candidate.tree, validation)
        task.candidate.training_score = train_score
        task.candidate.validation_score = validation_score
        if train_score < 1.0 or validation_score < 1.0 or task.conflict_count:
            return 0.0
        complexity = min(1.0, float(task.candidate.node_count) / float(_MAX_PROGRAM_NODES))
        return max(0.0, min(1.0, 0.97 - 0.12 * complexity))

    def _dissolve_warp(self, component_id: str) -> None:
        task = self._tasks.get(self._component_task.get(component_id, ""))
        if task is not None:
            task.status = "dissolved"
            if task.candidate is not None:
                task.candidate.status = "dissolved"
        self._persist()

    def observe_experience(self, experience: Mapping[str, Any]) -> Dict[str, Any]:
        """Accept a domain-neutral structured experience from another organ.

        Required evidence is an input structure and an expected/resulting
        output structure. The caller may supply any domain label for its own
        bookkeeping, but domain never participates in program synthesis.
        """
        rec = dict(experience or {})
        input_value = rec.get("input_value", rec.get("input", rec.get("before")))
        expected_output = rec.get(
            "expected_output",
            rec.get("output", rec.get("after", rec.get("expected"))),
        )
        if input_value is None or expected_output is None:
            return {"accepted": False, "reason": "structured_input_and_output_required"}
        task_id = str(rec.get("task_id", "") or rec.get("persistence_key", "") or "").strip()
        if not task_id:
            task_id = "OPTASK:" + _stable_hash({
                "need": rec.get("need_description", rec.get("unresolved_text", "")),
                "input_shape": _type_shape(input_value),
                "output_shape": _type_shape(expected_output),
            }, 16)
        result = self.observe_example(
            task_id,
            input_value,
            expected_output,
            validation=bool(rec.get("validation", rec.get("holdout", False))),
            source=str(rec.get("source", "structured_experience") or "structured_experience"),
            need_description=str(rec.get("need_description", rec.get("unresolved_text", "")) or ""),
        )
        result["accepted"] = True
        return result

    def observe_example(
        self,
        task_id: str,
        input_value: Any,
        expected_output: Any,
        *,
        validation: bool = False,
        source: str = "experience",
        need_description: str = "",
    ) -> Dict[str, Any]:
        task_key = str(task_id or "").strip()
        if not task_key:
            raise ValueError("task_id_required")
        task = self._tasks.get(task_key)
        if task is None:
            if len(self._tasks) >= _MAX_TASKS:
                oldest = min(self._tasks.values(), key=lambda x: x.updated_at)
                self._tasks.pop(oldest.task_id, None)
            task = SynthesisTask(
                task_id=task_key,
                need_description=str(need_description or "unresolved operation"),
                structural_signature=_stable_hash({
                    "input": _type_shape(input_value),
                    "output": _type_shape(expected_output),
                }, 20),
                root_pressure=_task_pressure(input_value, expected_output),
            )
            self._tasks[task_key] = task
        elif need_description:
            task.need_description = str(need_description)

        # Contradictory evidence for the same exact input is retained as a
        # conflict, not silently overwritten.
        input_hash = _stable_hash(input_value, 20)
        for existing in task.examples:
            if _stable_hash(existing.input_value, 20) == input_hash and not _values_equal(existing.expected_output, expected_output):
                task.conflict_count += 1

        example = SynthesisExample(
            example_id="SYNEX:" + _stable_hash({
                "task": task_key,
                "input": input_value,
                "output": expected_output,
                "validation": validation,
                "n": len(task.examples),
            }, 16),
            input_value=_json_clone(input_value),
            expected_output=_json_clone(expected_output),
            validation=bool(validation),
            source=str(source or "experience"),
        )
        task.examples.append(example)
        task.examples = task.examples[-_MAX_EXAMPLES_PER_TASK:]
        task.updated_at = time.time()
        self._tick += 1

        training = [e for e in task.examples if not e.validation]
        if not validation:
            # Every unmet example contributes one observation of the same root
            # pressure. WARP therefore decides when the need has persisted; the
            # enumerator is only allowed to act once the examples are varied
            # enough to distinguish an operation from rote recall.
            profile = _warp_profile(task.root_pressure)
            self._active_task_id = task_key
            self._profile_task[_stable_hash(profile, 20)] = task_key
            try:
                component = self.check_and_extend(
                    profile,
                    source=f"operational_synthesis:{task_key}",
                    tick=self._tick,
                )
                if component is not None:
                    task.warp_component_id = component.component_id
                    self._component_task[component.component_id] = task_key
            finally:
                self._active_task_id = ""

            distinct_inputs = {_stable_hash(e.input_value, 20) for e in training}
            if (
                len(training) >= _MIN_TRAINING_EXAMPLES
                and len(distinct_inputs) >= _MIN_DISTINCT_TRAINING_INPUTS
                and task.warp_component_id
                and (task.candidate is None or task.candidate.status in {"dissolved", "failed"})
            ):
                self.synthesize(task_key)

        if validation and task.candidate is not None:
            try:
                predicted = execute_program(task.candidate.tree, input_value)
                correct = _values_equal(predicted, expected_output)
            except Exception:
                predicted = None
                correct = False
            if not correct:
                task.status = "validation_failed"
                task.candidate.status = "failed"
            else:
                task.status = "validation_active"
            self.evaluate_development()
        self._persist()
        return self.task_status(task_key)

    def synthesize(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(str(task_id or ""))
        if task is None:
            return {"synthesized": False, "reason": "unknown_task"}
        training = [e for e in task.examples if not e.validation]
        distinct_inputs = {_stable_hash(e.input_value, 20) for e in training}
        if len(training) < _MIN_TRAINING_EXAMPLES or len(distinct_inputs) < _MIN_DISTINCT_TRAINING_INPUTS:
            return {"synthesized": False, "reason": "insufficient_varied_examples"}
        if task.conflict_count:
            return {"synthesized": False, "reason": "contradictory_examples"}
        task.synthesis_attempts += 1
        tree = synthesize_program(training)
        if tree is None:
            task.status = "unsynthesized_gap"
            self._persist()
            return {"synthesized": False, "reason": "no_program_in_current_primitive_span"}
        score = self._score_examples(tree, training)
        primitives = _primitive_sequence(tree)
        roots = _program_roots(tree)
        program_id = "SYN:" + _stable_hash({"task": task.task_id, "tree": tree}, 16)
        candidate = SynthesizedProgram(
            program_id=program_id,
            tree=tree,
            primitive_sequence=primitives,
            root_constraints=roots,
            canonical_signature=canonical_signature(roots or AXES),
            node_count=_node_count(tree),
            training_score=score,
            status="trial",
            warp_component_id=task.warp_component_id,
        )
        task.candidate = candidate
        task.status = "candidate_trial"
        if task.warp_component_id:
            self._component_task[task.warp_component_id] = task.task_id
        self._persist()
        return {
            "synthesized": True,
            "task_id": task.task_id,
            "program": candidate.to_dict(),
            "description": describe_program(tree),
        }

    def execute(self, task_id: str, input_value: Any, *, allow_trial: bool = True) -> Dict[str, Any]:
        task = self._tasks.get(str(task_id or ""))
        if task is None or task.candidate is None:
            return {"executed": False, "reason": "no_candidate"}
        if task.candidate.status != "promoted" and not allow_trial:
            return {"executed": False, "reason": "candidate_not_promoted"}
        try:
            output = execute_program(task.candidate.tree, input_value)
            return {
                "executed": True,
                "task_id": task.task_id,
                "program_id": task.candidate.program_id,
                "status": task.candidate.status,
                "output": output,
            }
        except Exception as exc:
            return {"executed": False, "reason": type(exc).__name__, "detail": str(exc)}

    def evaluate_development(self) -> Tuple[List[str], List[str]]:
        promoted, dissolved = self.evaluate_warp_trials()
        for component_id in promoted:
            task = self._tasks.get(self._component_task.get(component_id, ""))
            if task is None or task.candidate is None:
                continue
            task.status = "promoted"
            task.candidate.status = "promoted"
            task.candidate.genealogy_ability_id = self._register_genealogy(task, self._warp_promoted.get(component_id))
        for component_id in dissolved:
            task = self._tasks.get(self._component_task.get(component_id, ""))
            if task is not None:
                task.status = "dissolved"
                if task.candidate is not None:
                    task.candidate.status = "dissolved"
        self._persist()
        return promoted, dissolved

    def task_status(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(str(task_id or ""))
        if task is None:
            return {"exists": False, "task_id": str(task_id or "")}
        training = [e for e in task.examples if not e.validation]
        validation = [e for e in task.examples if e.validation]
        return {
            "exists": True,
            "task_id": task.task_id,
            "status": task.status,
            "need_description": task.need_description,
            "training_examples": len(training),
            "validation_examples": len(validation),
            "distinct_training_inputs": len({_stable_hash(e.input_value, 20) for e in training}),
            "distinct_validation_inputs": len({_stable_hash(e.input_value, 20) for e in validation}),
            "conflicts": task.conflict_count,
            "warp_component_id": task.warp_component_id,
            "candidate": task.candidate.to_dict() if task.candidate else None,
            "description": describe_program(task.candidate.tree) if task.candidate else "",
        }

    def trace_task_to_roots(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(str(task_id or ""))
        if task is None or task.candidate is None:
            return {"available": False, "task_id": str(task_id or "")}
        primitives = []
        for name in task.candidate.primitive_sequence:
            spec = PRIMITIVES.get(name)
            if spec is None:
                continue
            primitives.append({
                "primitive": name,
                "roots": list(spec.roots),
                "description": spec.description,
            })
        return {
            "available": True,
            "task_id": task.task_id,
            "program_id": task.candidate.program_id,
            "status": task.candidate.status,
            "program_description": describe_program(task.candidate.tree),
            "canonical_signature": task.candidate.canonical_signature,
            "root_constraints": list(task.candidate.root_constraints),
            "primitive_lineage": primitives,
            "warp_component_id": task.warp_component_id,
            "genealogy_ability_id": task.candidate.genealogy_ability_id,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "tasks": len(self._tasks),
            "observing": sum(1 for t in self._tasks.values() if t.status == "observing"),
            "candidate_trials": sum(1 for t in self._tasks.values() if t.candidate and t.candidate.status == "trial"),
            "promoted": sum(1 for t in self._tasks.values() if t.candidate and t.candidate.status == "promoted"),
            "dissolved": sum(1 for t in self._tasks.values() if t.status == "dissolved"),
            "primitive_count": len(PRIMITIVES),
            "warp": self.warp_status(),
            "storage_path": self.storage_path,
        }

    def primitive_catalog(self) -> List[Dict[str, Any]]:
        return [asdict(PRIMITIVES[name]) for name in sorted(PRIMITIVES)]

    @staticmethod
    def _score_examples(tree: Mapping[str, Any], examples: Sequence[SynthesisExample]) -> float:
        if not examples:
            return 0.0
        passed = 0
        for example in examples:
            try:
                if _values_equal(execute_program(tree, example.input_value), example.expected_output):
                    passed += 1
            except Exception:
                pass
        return passed / float(len(examples))

    def _register_genealogy(self, task: SynthesisTask, component: Optional[WarpComponent]) -> str:
        candidate = task.candidate
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        if candidate is None or genealogy is None:
            return ""
        payload = {
            "task_id": task.task_id,
            "program_id": candidate.program_id,
            "component_id": candidate.warp_component_id,
            "constraints": list(candidate.root_constraints),
            "canonical_signature": candidate.canonical_signature,
            "primitive_sequence": list(candidate.primitive_sequence),
            "program_tree": copy.deepcopy(candidate.tree),
            "program_description": describe_program(candidate.tree),
            "parent_ids": list(getattr(component, "parent_ids", []) or []),
            "trial_score": float(getattr(component, "trial_score_ema", 0.0) or 0.0),
            "training_examples": len([e for e in task.examples if not e.validation]),
            "validation_examples": len([e for e in task.examples if e.validation]),
            "node_count": candidate.node_count,
            "need_description": task.need_description,
        }
        if hasattr(genealogy, "register_emergent_operational_synthesis"):
            try:
                result = dict(genealogy.register_emergent_operational_synthesis(payload) or {})
                return str(result.get("ability_id", "") or "")
            except Exception:
                return ""
        return ""

    def _load(self) -> None:
        if not self.persist or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                raw = dict(json.load(handle) or {})
            self._tick = int(raw.get("tick", 0) or 0)
            for task_id, item in dict(raw.get("tasks") or {}).items():
                rec = dict(item or {})
                examples = [SynthesisExample(**dict(e or {})) for e in list(rec.get("examples") or [])]
                cand_rec = rec.get("candidate")
                candidate = SynthesizedProgram(**dict(cand_rec or {})) if cand_rec else None
                task = SynthesisTask(
                    task_id=str(rec.get("task_id", task_id) or task_id),
                    need_description=str(rec.get("need_description", "") or ""),
                    structural_signature=str(rec.get("structural_signature", "") or ""),
                    root_pressure={ax: float(dict(rec.get("root_pressure") or {}).get(ax, 0.0) or 0.0) for ax in AXES},
                    examples=examples,
                    candidate=candidate,
                    conflict_count=int(rec.get("conflict_count", 0) or 0),
                    synthesis_attempts=int(rec.get("synthesis_attempts", 0) or 0),
                    created_at=float(rec.get("created_at", time.time()) or time.time()),
                    updated_at=float(rec.get("updated_at", time.time()) or time.time()),
                    warp_component_id=str(rec.get("warp_component_id", "") or ""),
                    status=str(rec.get("status", "observing") or "observing"),
                )
                self._tasks[task.task_id] = task
                if task.warp_component_id:
                    self._component_task[task.warp_component_id] = task.task_id
            warp_state = dict(raw.get("warp_state") or {})
            for component_id, item in dict(warp_state.get("trials") or {}).items():
                component = _restore_component(item)
                if component.component_id:
                    self._warp_trials[component.component_id] = component
            for component_id, item in dict(warp_state.get("promoted") or {}).items():
                component = _restore_component(item)
                if component.component_id:
                    self._warp_promoted[component.component_id] = component
            self._warp_dissolved_count = int(warp_state.get("dissolved_count", 0) or 0)
        except Exception:
            self._tasks = {}
            self._component_task = {}

    def _persist(self) -> None:
        if not self.persist:
            return
        os.makedirs(self.state_dir, exist_ok=True)
        payload = {
            "schema_version": 1,
            "tick": self._tick,
            "tasks": {task_id: task.to_dict() for task_id, task in self._tasks.items()},
            "primitive_catalog": self.primitive_catalog(),
            "warp_state": {
                "trials": {cid: _component_record(comp) for cid, comp in self._warp_trials.items()},
                "promoted": {cid: _component_record(comp) for cid, comp in self._warp_promoted.items()},
                "dissolved_count": int(self._warp_dissolved_count),
            },
            "updated_at": time.time(),
        }
        atomic_write_json(Path(self.storage_path), payload, indent=2, default=str)


__all__ = [
    "AuroraOperationalSynthesisChamber",
    "PrimitiveSpec",
    "PRIMITIVES",
    "SynthesisExample",
    "SynthesisTask",
    "SynthesizedProgram",
    "execute_program",
    "synthesize_program",
    "describe_program",
]
