"""Dependency-aware, compute-once values for one live Aurora turn.

Only *pure derivations* belong here. Operations that learn, spend energy,
record consequences, or mutate persistent state still execute normally.

Publish compact source revisions (not whole crystal stores) whenever a
meaningful input/action changes. Readers share the same derived result until
one of its declared dependencies changes. Derived dependencies are refreshed
recursively, and if an upstream calculation produces the same result its
downstream consumers remain valid.

All returned values are defensive deep copies. The graph dies with its
TurnLedger; it never becomes a second store of developmental memory.
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple


@dataclass
class _Source:
    value: Any
    revision: int = 1


@dataclass
class _Derived:
    dependencies: Tuple[str, ...]
    factory: Callable[[Mapping[str, Any]], Any]
    definition_version: Any = 0
    revision: int = 0
    signature: Optional[Tuple[Any, ...]] = None
    value: Any = None
    ready: bool = False


class TurnComputeGraph:
    """Per-turn dependency graph; no global cache or implicit state tracking.

    A caller MUST publish a new source revision when the result of a
    dependency could change. To avoid expensive comparisons, publish stable
    small revision tokens for large mutable organs rather than whole objects.
    """

    def __init__(self) -> None:
        self._sources: Dict[str, _Source] = {}
        self._derived: Dict[str, _Derived] = {}
        self._guard = threading.RLock()
        self.hits = 0
        self.computations = 0
        self.source_changes = 0

    @staticmethod
    def _same(left: Any, right: Any) -> bool:
        try:
            return bool(left == right)
        except (TypeError, ValueError):
            return False

    def publish(self, name: str, value: Any) -> bool:
        """Record source input. Return True only when its content changed."""
        name = str(name)
        with self._guard:
            if name in self._derived:
                raise ValueError(f"derived key cannot be a source: {name}")
            snapshot = copy.deepcopy(value)
            prior = self._sources.get(name)
            if prior is not None and self._same(prior.value, snapshot):
                return False
            revision = prior.revision + 1 if prior is not None else 1
            self._sources[name] = _Source(snapshot, revision)
            self.source_changes += 1
            return True

    def derive(
        self,
        name: str,
        dependencies: Sequence[str],
        factory: Callable[[Mapping[str, Any]], Any],
        *,
        definition_version: Any = 0,
    ) -> Any:
        """Register/read a pure computation from explicitly named inputs.

        The compute callback receives independent copies of its dependencies.
        A new definition_version invalidates an implementation that changed;
        mere callback recreation does not count as changed behavior.
        """
        name = str(name)
        deps = tuple(str(dep) for dep in dependencies)
        if name in deps:
            raise ValueError(f"self-dependent computation: {name}")
        if len(set(deps)) != len(deps):
            raise ValueError(f"duplicate dependency in: {name}")
        with self._guard:
            if name in self._sources:
                raise ValueError(f"source key cannot be a derivation: {name}")
            current = self._derived.get(name)
            if current is None:
                current = _Derived(dependencies=deps, factory=factory,
                                   definition_version=copy.deepcopy(definition_version))
                self._derived[name] = current
            else:
                if current.dependencies != deps:
                    raise ValueError(f"cannot change dependency declaration for: {name}")
                if not self._same(current.definition_version, definition_version):
                    current.definition_version = copy.deepcopy(definition_version)
                    current.signature = None
                current.factory = factory
            return self._resolve(name, ())[0]

    def read(self, name: str) -> Any:
        """Read current result and refresh only stale dependencies as needed."""
        with self._guard:
            return self._resolve(str(name), ())[0]

    def _resolve(self, name: str, ancestry: Tuple[str, ...]) -> Tuple[Any, int]:
        if name in ancestry:
            raise ValueError("circular computation: " + " -> ".join((*ancestry, name)))
        source = self._sources.get(name)
        if source is not None:
            return copy.deepcopy(source.value), source.revision
        item = self._derived.get(name)
        if item is None:
            raise KeyError(f"unpublished dependency: {name}")
        lineage = (*ancestry, name)
        dep_values: Dict[str, Any] = {}
        dep_revs = []
        for dependency in item.dependencies:
            value, revision = self._resolve(dependency, lineage)
            dep_values[dependency] = value
            dep_revs.append(revision)
        signature = (tuple(dep_revs), copy.deepcopy(item.definition_version))
        if item.ready and self._same(item.signature, signature):
            self.hits += 1
            return copy.deepcopy(item.value), item.revision
        # Do not cache exceptions, partial results or side effects.
        output = item.factory(dep_values)
        # A pure factory may not mutate its own published inputs while running.
        # This check also guards against unexpected re-entrant publishes.
        for dep, previous in zip(item.dependencies, dep_revs):
            if self._resolve(dep, lineage)[1] != previous:
                raise RuntimeError(f"dependency changed during computation: {name}/{dep}")
        snapshot = copy.deepcopy(output)
        changed = not item.ready or not self._same(item.value, snapshot)
        item.value = snapshot
        item.signature = signature
        item.ready = True
        if changed:
            item.revision += 1
        self.computations += 1
        return copy.deepcopy(item.value), item.revision

    def status(self) -> Dict[str, int]:
        """Small diagnostic counters; never expose cached private content."""
        with self._guard:
            return {
                "sources": len(self._sources),
                "derivations": len(self._derived),
                "cache_hits": self.hits,
                "computations": self.computations,
                "source_changes": self.source_changes,
            }
