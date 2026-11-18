"""Composition space referencing real source anatomy and observed host services.

Only structural compatibility is resolved here. A graph is a hypothesis until
its consequences are independently observed. No arbitrary source is executed.
"""
from __future__ import annotations

import copy
import threading
import time

from .common import digest, read_json, write_json


class BlueprintSpace:
    def __init__(self, state_dir):
        from pathlib import Path
        self.path = Path(state_dir) / "computational_blueprints.json"
        self._lock = threading.RLock()
        data = read_json(self.path, {})
        self.nodes = data.get("nodes", {})
        self.compositions = data.get("compositions", {})
        self._resolved = data.get("resolved", {})
        self._source_stamp = None
        self._inventory_stamp = None

    def _save(self):
        write_json(self.path, {"schema": 1, "nodes": self.nodes, "compositions": self.compositions,
                               "resolved": dict(list(self._resolved.items())[-2000:])})

    def register(self, node_id, descriptor):
        with self._lock:
            node = copy.deepcopy(descriptor)
            node["id"] = str(node_id)
            node.pop("version", None)
            node["version"] = digest(node)
            changed = self.nodes.get(node_id, {}).get("version") != node["version"]
            self.nodes[node_id] = node
            return changed

    def import_real(self, systems, host):
        with self._lock:
            current = set()
            lineage = systems.get("function_lineage")
            source_stamp = (lineage.status().get("source_manifest_hash") if lineage is not None else None)
            inventory_stamp = host.inventory.get("version")
            if self._source_stamp == source_stamp and self._inventory_stamp == inventory_stamp and self.nodes:
                return {"nodes": len(self.nodes), "reused_source_map": True}
            functions = lineage.all_functions() if lineage is not None else {}
            if not functions:
                intro = systems.get("system_introspection")
                functions = getattr(intro, "_function_index", {}) if intro is not None else {}
            for fid, rec in functions.items():
                key = "source:" + str(fid)
                current.add(key)
                self.register(key, {"kind": "source_function", "provenance": "existing_source_anatomy",
                                    "anatomy_ref": str(fid),
                                    "source": {k: rec[k] for k in ("file", "qualname", "line", "end_line", "source_hash", "signature_text") if k in rec},
                                    "inputs": {}, "outputs": {},
                                    "semantics": "unverified", "dependencies": []})
            inventory = host.inventory
            # OS/software records remain opaque blueprints when their internals
            # are not exposed; their existence never fabricates an implementation.
            for group in ("os", "cpu", "gpu", "storage", "network", "services", "software", "applications"):
                rows = inventory.get(group) or []
                if isinstance(rows, dict):
                    rows = [{"name": k, "executable": v} for k, v in rows.items()]
                for record in rows:
                    key = f"host:{group}:" + str(record.get("Name") or record.get("name") or record.get("DeviceID") or digest(record))
                    current.add(key)
                    self.register(key, {"kind": "host_" + group, "provenance": "os_enumeration",
                                        "observed": record, "inputs": {}, "outputs": {},
                                        "semantics": "opaque_host_interface", "dependencies": []})
            for i, rec in enumerate(inventory.get("devices") or []):
                key = "device:" + str(rec.get("DeviceID") or rec.get("id") or digest(rec))
                current.add(key)
                self.register(key, {"kind": "os_device", "provenance": "os_enumeration", "observed": rec,
                                    "inputs": {}, "outputs": {}, "semantics": "unverified",
                                    "resources": {key: "exclusive"}, "dependencies": []})
            from aurora_internal.tool_registry import available_tools
            for tool in available_tools():
                key = "service:" + tool
                current.add(key)
                self.register(key, {"kind": "tool_service", "provenance": "existing_tool_registry",
                                    "operation": tool, "inputs": {}, "outputs": {},
                                    "semantics": "requires_live_operation", "dependencies": []})
            for key in list(self.nodes):
                if key.startswith(("source:", "device:", "service:", "host:")) and key not in current and key != "host:machine":
                    # Removal is consequential: old compositions report missing
                    # components instead of silently using a stale blueprint.
                    del self.nodes[key]
            self.register("host:machine", {"kind": "host", "provenance": "observed_os_exposure",
                                           "inventory": inventory, "inputs": {}, "outputs": {},
                                           "semantics": "unverified", "dependencies": []})
            self._save()
            self._source_stamp, self._inventory_stamp = source_stamp, inventory_stamp
            return {"nodes": len(self.nodes), "functions": len(functions)}

    def compose(self, name, components, connections=None):
        with self._lock:
            if not name or not components or len(components) > 256:
                raise ValueError("name and 1-256 components required")
            if len(set(components)) != len(components):
                raise ValueError("duplicate component")
            if any(c not in self.nodes for c in components):
                raise ValueError("unknown component")
            edges = copy.deepcopy(connections or [])
            if len(edges) > 1024:
                raise ValueError("too many connections")
            for edge in edges:
                if edge.get("from") not in components or edge.get("to") not in components:
                    raise ValueError("connection outside composition")
            # Cycles are useful hypotheses, but cannot be resolved as a pure DAG.
            graph = {c: [] for c in components}
            for e in edges:
                graph[e["from"]].append(e["to"])
            visiting, done = set(), set()
            def visit(c):
                if c in visiting:
                    raise ValueError("cyclic computation needs an explicit state/clock contract")
                if c not in done:
                    visiting.add(c)
                    for target in graph[c]:
                        visit(target)
                    visiting.remove(c)
                    done.add(c)
            for c in components:
                visit(c)
            self.compositions[str(name)] = {"components": list(components), "connections": edges}
            self._save()
            return self.resolve(str(name))

    def _dependency_version(self, node_id, seen=None):
        seen = set(seen or ())
        if node_id in seen:
            return "cyclic_dependency"
        node = self.nodes.get(node_id)
        if node is None:
            return "missing"
        seen.add(node_id)
        return digest([node["version"], [(d, self._dependency_version(d, seen))
                                        for d in node.get("dependencies", [])]])

    def resolve(self, name):
        with self._lock:
            composition = self.compositions[name]
            versions = {c: self._dependency_version(c) for c in composition["components"]}
            checks, computed, reused = [], 0, 0
            resources = {}
            missing = [c for c in versions if c not in self.nodes]
            for c in composition["components"]:
                for resource, mode in self.nodes.get(c, {}).get("resources", {}).items():
                    resources.setdefault(resource, []).append((c, mode))
            conflicts = {r: [c for c, _ in users] for r, users in resources.items()
                         if len(users) > 1 and any(mode == "exclusive" for _, mode in users)}
            for edge in composition["connections"]:
                key = digest([edge, versions[edge["from"]], versions[edge["to"]]])
                if key in self._resolved:
                    check = copy.deepcopy(self._resolved[key])
                    reused += 1
                else:
                    source = self.nodes.get(edge["from"], {})
                    target = self.nodes.get(edge["to"], {})
                    out = source.get("outputs", {}).get(edge.get("out"))
                    inp = target.get("inputs", {}).get(edge.get("in"))
                    check = {"connection": edge, "compatible": None if out is None or inp is None else out == inp,
                             "basis": "declared_interface_contract", "operationally_verified": False}
                    self._resolved[key] = check
                    computed += 1
                checks.append(check)
            result = {"name": name, "versions": versions, "checks": checks, "resource_conflicts": conflicts,
                      "missing_components": missing, "recomputed_interactions": computed,
                      "reused_interactions": reused, "epistemic_status": "composition_hypothesis",
                      "operationally_verified": False,
                      "unresolved_semantics": [c for c in versions if self.nodes.get(c, {}).get("semantics") != "verified"]}
            self._save()
            return result

    def view(self, query="", limit=100):
        with self._lock:
            keys = [k for k in self.nodes if query.lower() in k.lower()]
            return {"total": len(self.nodes), "matches": len(keys),
                    "nodes": [self.nodes[k] for k in keys[:min(500, max(1, int(limit)))]],
                    "compositions": copy.deepcopy(self.compositions)}
