#!/usr/bin/env python3
"""
aurora_knowledge_graph.py -- Aurora's codebase knowledge graph, built from source and from what runs.

The graph is generated, never hand-edited.  Every node and edge says where it came from, and
every edge carries a basis that keeps three kinds of knowledge apart:

    declared      a document, the fix registry, the layer ownership doc or the ontology says so
    implemented   the code says so (Python's own parser, or a structural parse of Rust, Dart,
                  Kotlin and Java)
    observed      it actually executed during a recorded run (see aurora_kg_observe.py)

An edge can hold more than one basis; one that is only declared is a claim the code has not
backed yet, and one that is implemented but never observed is a path no recorded run took.

What it maps, beyond structure:
    information flow    FEEDS edges follow a value from where it is produced (a call's return,
                        a field, a store, a bus slot, a pipeline signal) to where it lands
                        (another field, store, slot, a callee's argument, a function's return)
    state holders       Field nodes for instance attributes and module-level state
    concurrency         SPAWNS (threads, timers, executors, tasks, services) and PASSES_CALLBACK
    language bridges    Endpoint nodes join Dart, Kotlin, Python and Rust: MethodChannel methods,
                        EventChannel events, Chaquopy calls, HTTP paths and ACM frame headers
    subsystems          declared and inferred responsibilities, kept apart
    coverage            every unresolved call, unexamined file and unobserved path stays listed

Usage:
    python scripts/aurora_knowledge_graph.py build
    python scripts/aurora_knowledge_graph.py build --runtime knowledge_graph/runtime
    python scripts/aurora_knowledge_graph.py check
    python scripts/aurora_knowledge_graph.py query --find SediMemory
    python scripts/aurora_knowledge_graph.py query --node mod:aurora_sedimemory
    python scripts/aurora_knowledge_graph.py query --impact mod:aurora_internal.aurora_leverage_scalar
    python scripts/aurora_knowledge_graph.py query --path fn:aurora.boot_aurora store:aurora_oets_web.json
    python scripts/aurora_knowledge_graph.py trace field:aurora_bridge._praxis --direction both
    python scripts/aurora_knowledge_graph.py investigate praxis --question "Praxis initialized but reported as not"
    python scripts/aurora_knowledge_graph.py diff knowledge_graph other_branch/knowledge_graph
    python scripts/aurora_knowledge_graph.py export --format nodelink
    python scripts/aurora_knowledge_graph.py schema

Outputs (default directory: knowledge_graph/):
    graph/meta.json             counts, hash, commit, coverage totals
    graph/nodes.jsonl           every node, one per line, sorted
    graph/edges/<TYPE>.jsonl    every edge of one type, one per line, sorted (first 3 evidence sites)
    evidence/<TYPE>.jsonl       the full evidence list of every edge that has more than 3 sites
    coverage/                   files.jsonl, unresolved_calls.jsonl, unobserved.json, COVERAGE.md
    runtime/                    recorded observations this build folded in
    schema.json, ontology.json  what this build enforced and used
    SUMMARY.md, SUBSYSTEMS.md   findings; implemented, declared and observed kept apart
    index.html                  self-contained interactive view
    exports/                    gitignored: single-file node-link JSON, GraphML, JSON-LD

Standard library only.  Python 3.9+.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr as xml_quoteattr

SCHEMA_VERSION = "2.0.0"
GENERATOR_VERSION = "2.0.0"
AUTHORS = "Sunni (Sir) Morningstar & Cael Devo"
EVIDENCE_CAP = 3
DOCSTRING_CAP = 200
SIGNATURE_CAP = 240

# ===========================================================================
# SECTION 1 -- SCHEMA
# Every node type, every edge type, and which node types each edge may join.
# The build validates every edge against this before it writes anything.
# ===========================================================================

NODE_TYPES: Dict[str, Dict[str, Any]] = {
    "Repository": {"prefix": "repo", "description": "The repository root."},
    "Package": {"prefix": "pkg", "description": "A Python package (a directory with __init__.py)."},
    "Module": {"prefix": "mod", "description": "A Python source file. role: core, internal, package_init, test, script, tool, app."},
    "Class": {"prefix": "cls", "description": "A class, struct, enum, trait or object definition. language: python, rust, dart, kotlin, java."},
    "Function": {"prefix": "fn", "description": "A function or method in any analysed language. kind: function, method, staticmethod, classmethod, property, nested."},
    "Constant": {"prefix": "const", "description": "An UPPER_CASE module- or class-level assignment."},
    "Field": {"prefix": "field", "description": "A state holder: an instance or class attribute, or module-level state that functions change. kind: instance, class, module_state."},
    "ExternalDependency": {"prefix": "ext", "description": "A top-level import outside the repo. ecosystem: stdlib, builtins, third_party."},
    "SourceFile": {"prefix": "src", "description": "A non-Python source file (Rust, Dart, Kotlin, Java, shell, workflow, web)."},
    "StateStore": {"prefix": "store", "description": "A persisted file the code reads or writes, named relative to the state dir."},
    "EnvVar": {"prefix": "env", "description": "An environment variable the code reads or sets."},
    "BusChannel": {"prefix": "bus", "description": "A systems[\"_key\"] bus slot: signals passed between organs."},
    "Organ": {"prefix": "organ", "description": "A systems[\"key\"] slot holding a live subsystem object."},
    "Signal": {"prefix": "signal", "description": "A key of a turn's pipeline state (pipeline_state[\"key\"])."},
    "Endpoint": {"prefix": "endpoint", "description": "A point where one runtime or language hands work to another. protocol: methodchannel, eventchannel, chaquopy, http, frame, android_intent."},
    "Layer": {"prefix": "layer", "description": "An architectural layer, L0-L8, or the Orchestrator."},
    "Subsystem": {"prefix": "subsys", "description": "A responsibility: a layer, a named Aurora subsystem or an organ's implementation. basis says whether it is declared or inferred."},
    "ConstraintAxis": {"prefix": "axis", "description": "One of the five canonical constraint axes X, T, N, B, A."},
    "IStatePair": {"prefix": "istate", "description": "One of the five I-State polarity pairs."},
    "NonCompDimension": {"prefix": "ncdim", "description": "One of the five Non-Comp representational dimensions."},
    "NonComp": {"prefix": "nc", "description": "One of the 25 Non-Comps (axis x dimension)."},
    "ManifoldEntry": {"prefix": "manifold", "description": "One file in the constraint manifold directory."},
    "Concept": {"prefix": "concept", "description": "A named Aurora subsystem or a stage of a canonical sequence."},
    "DoctrineRule": {"prefix": "rule", "description": "A FIX-### entry of the known fixes registry."},
    "Document": {"prefix": "doc", "description": "A Markdown document in the repo."},
}

CODE = ["Module", "Class", "Function"]
CHANNELS = ["Field", "StateStore", "EnvVar", "BusChannel", "Organ", "Signal"]
VOCAB = ["ConstraintAxis", "IStatePair", "NonComp", "NonCompDimension", "Concept"]

EDGE_TYPES: Dict[str, Dict[str, Any]] = {
    "CONTAINS": {"source": ["Repository", "Package", "Module", "Class", "Function", "SourceFile"],
                 "target": ["Package", "Module", "Class", "Function", "Constant", "SourceFile", "Document", "Field"],
                 "description": "Structural ownership: repo > package > module or source file > class > method."},
    "IMPORTS": {"source": ["Module", "SourceFile"], "target": ["Module", "Package", "ExternalDependency", "SourceFile"],
                "description": "An import. attrs: names (imported symbols), lazy (inside a function)."},
    "INHERITS": {"source": ["Class"], "target": ["Class", "ExternalDependency"],
                 "description": "A base class, implemented trait or interface. attrs: names (base name when external)."},
    "OVERRIDES": {"source": ["Function"], "target": ["Function"],
                  "description": "A method that redefines a method of a base class."},
    "CALLS": {"source": CODE, "target": ["Function"],
              "description": "A call. confidence 1.0 exact or observed, 0.9 self/super, 0.8 typed, 0.6-0.7 by unique name in Rust, Dart, Kotlin, Java."},
    "INSTANTIATES": {"source": CODE, "target": ["Class"], "description": "A constructor call."},
    "READS": {"source": CODE, "target": CHANNELS,
              "description": "Reads a field, persisted file, environment variable, bus slot or pipeline signal."},
    "WRITES": {"source": CODE, "target": CHANNELS,
               "description": "Writes or mutates a field, persisted file, environment variable, bus slot or pipeline signal."},
    "REFERENCES": {"source": CODE, "target": ["StateStore"],
                   "description": "Names a persisted file without a read or write visible in the same statement."},
    "FEEDS": {"source": ["Function", "Class", "Endpoint"] + CHANNELS, "target": ["Function"] + CHANNELS + ["Endpoint"],
              "description": "Information flow: a value produced by the source lands in the target. attrs: via (functions where "
                             "the hand-off happens), roles (assign, argument, receiver, return, store_write, payload)."},
    "PERSISTS_TO": {"source": ["Class"], "target": ["StateStore"],
                    "description": "A class whose methods write this store (derived from WRITES)."},
    "REGISTERS": {"source": CODE, "target": ["Organ"], "description": "Places an object into a systems slot."},
    "USES_ORGAN": {"source": CODE, "target": ["Organ"], "description": "Reads a systems slot to use the organ in it."},
    "IMPLEMENTED_BY": {"source": ["Organ"], "target": ["Class"], "description": "The class of the object registered in the slot."},
    "SPAWNS": {"source": CODE + ["SourceFile"], "target": ["Function", "Class"],
               "description": "Starts work that runs later or elsewhere. attrs: mechanisms (thread, timer, executor, task, "
                              "call_later, atexit, signal, android_service)."},
    "PASSES_CALLBACK": {"source": CODE, "target": ["Function"],
                        "description": "Hands a function reference to other code to call later. attrs: to (receiving callee), params."},
    "INVOKES": {"source": CODE + ["SourceFile"], "target": ["Endpoint"], "description": "Calls across a runtime or language boundary."},
    "HANDLES": {"source": CODE + ["SourceFile"], "target": ["Endpoint"], "description": "Receives calls arriving at an endpoint."},
    "ROUTES_TO": {"source": ["Endpoint"], "target": ["Function", "Class"],
                  "description": "Where an endpoint delivers the work: the function that runs on the far side."},
    "EMITS": {"source": CODE + ["SourceFile"], "target": ["Endpoint"], "description": "Sends an event, frame or message to an endpoint."},
    "SUBSCRIBES": {"source": CODE + ["SourceFile"], "target": ["Endpoint"], "description": "Listens for events, frames or messages at an endpoint."},
    "OWNED_BY": {"source": ["Module"], "target": ["Layer"], "description": "Layer ownership, as declared."},
    "MEMBER_OF": {"source": ["Module", "SourceFile"], "target": ["Subsystem"],
                  "description": "A module's part in a responsibility. attrs: method (declared_layer, organ, name_pattern, path)."},
    "PRECEDES": {"source": ["Layer", "Concept"], "target": ["Layer", "Concept"],
                 "description": "Canonical order: L0 > L8, re-entry stages, observer levels."},
    "CITES": {"source": CODE, "target": ["DoctrineRule"], "description": "Code that names a FIX-### entry."},
    "GOVERNS": {"source": ["DoctrineRule"], "target": CODE + ["StateStore", "BusChannel"],
                "description": "A registry entry that names this code or store."},
    "DOCUMENTS": {"source": ["Document"], "target": CODE + ["StateStore", "BusChannel", "Organ", "SourceFile"],
                  "description": "A document that names this code, store, bus slot or organ."},
    "TESTS": {"source": ["Module"], "target": ["Module"], "description": "A test module importing the module under test."},
    "RUNS": {"source": ["SourceFile"], "target": ["Module", "SourceFile"], "description": "A shell script, workflow or service unit launching a module or a script."},
    "EXPRESSES": {"source": CODE, "target": VOCAB,
                  "description": "Code that carries an Aurora concept. provenance ast (literals) or name (identifiers)."},
    "MAPS_TO": {"source": ["IStatePair"], "target": ["ConstraintAxis"], "description": "I-State pair of an axis."},
    "COMPOSED_OF": {"source": ["NonComp", "ManifoldEntry"], "target": ["ConstraintAxis", "NonCompDimension", "NonComp"],
                    "description": "A Non-Comp's axis and dimension; a manifold entry's Non-Comp and base axis."},
    "PART_OF": {"source": ["Concept", "Subsystem"], "target": ["Concept", "Layer", "Subsystem"],
                "description": "A stage that belongs to a sequence; a subsystem that sits in a layer."},
}

# Which provenance gives which basis.  An edge's basis is the set over all its provenances.
PROVENANCE_BASIS = {"ast": "implemented", "regex": "implemented", "structure": "implemented",
                    "filesystem": "implemented", "doc": "declared", "ontology": "declared",
                    "name": "inferred", "runtime": "observed",
                    "claim": "declared", "path": "inferred"}

# ===========================================================================
# SECTION 2 -- CANONICAL ONTOLOGY
# Aurora's fixed vocabulary.  Axis symbols, polarity order and the re-entry
# sequence follow the standing rules exactly.  Override with --ontology.
# ===========================================================================

DEFAULT_ONTOLOGY: Dict[str, Any] = {
    "constraint_axes": [
        {"symbol": "X", "name": "Existence", "adjective": "Existential", "istate": "IS/ISNT",
         "poles": ["Admissible", "Inadmissible"], "name_tokens": ["existence", "existential"]},
        {"symbol": "T", "name": "Temporal", "adjective": "Temporal", "istate": "CAN/CANT",
         "poles": ["Propagating", "Stalled"], "name_tokens": ["temporal"]},
        {"symbol": "N", "name": "Energy", "adjective": "Energetic", "istate": "DO/DONT",
         "poles": ["Sufficient", "Insufficient"], "name_tokens": ["energy", "energetic"]},
        {"symbol": "B", "name": "Boundary", "adjective": "Boundary", "istate": "SAW/SAUNT",
         "poles": ["Contained", "Dissolved"], "name_tokens": ["boundary"]},
        {"symbol": "A", "name": "Agency", "adjective": "Agentive", "istate": "DID/DIDNT",
         "poles": ["Corrective", "Drifting"], "name_tokens": ["agency", "agentive"]},
    ],
    "axis_literal_min_distinct": 4,
    "istate_pairs": ["IS/ISNT", "CAN/CANT", "DO/DONT", "SAW/SAUNT", "DID/DIDNT"],
    "noncomp_dimensions": ["POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE"],
    "noncomp_channels": 25,
    "noncomp_interaction_slots": 625,
    "layers": [
        {"id": "L0", "name": "Foundational Contract", "modules": ["foundational_contract.py"]},
        {"id": "L1", "name": "IVM Lattice", "modules": ["aurora_ivm.py"]},
        {"id": "L2", "name": "I-State Beings", "modules": ["aurora_i_state_beings.py"]},
        {"id": "L3", "name": "Dimensional Systems", "modules": ["aurora_dimensional_systems.py"]},
        {"id": "L4", "name": "Consciousness Engine", "modules": ["aurora_consciousness_engine.py"]},
        {"id": "L5", "name": "Expression & Perception", "modules": ["aurora_expression_perception.py"]},
        {"id": "L6", "name": "Behavioral Identity", "modules": ["aurora_behavioral_identity.py"]},
        {"id": "L7", "name": "Simulation Engine", "modules": ["aurora_simulation_engine.py"]},
        {"id": "L8", "name": "Governance & Persistence Gateway", "modules": ["aurora_governance_persistence_gateway.py"]},
        {"id": "ORCH", "name": "Orchestrator", "modules": ["aurora.py"]},
    ],
    "layer_ownership_doc": "docs/LAYER_MODULE_OWNERSHIP.md",
    "sequences": [
        {"id": "reentry_loop", "name": "Re-entry loop", "min_distinct": 3,
         "stages": ["STATE", "EXPRESSION", "RE-ENTRY", "RECONCILIATION", "UNDERSTANDING"]},
        {"id": "quasiarch_lattice", "name": "QuasiArch observer lattice", "min_distinct": 3,
         "stages": ["Base", "Composite", "Higher-Order", "Quasicrystal"]},
    ],
    "subsystems": [
        {"id": "sedimemory", "name": "SediMemory", "patterns": [r"sedimemory", r"sediment"]},
        {"id": "noncomp", "name": "Non-Comp physics", "patterns": [r"noncomp", r"non_comp"]},
        {"id": "leverage_scalar", "name": "Leverage scalar", "patterns": [r"leverage"]},
        {"id": "quasiarch", "name": "QuasiArch observer", "patterns": [r"quasiarch", r"quasicrystal"]},
        {"id": "crystal", "name": "Crystals", "patterns": [r"crystal"]},
        {"id": "genealogy", "name": "Constraint genealogy", "patterns": [r"genealogy", r"lineage", r"ancestry"]},
        {"id": "warp", "name": "Warp field", "patterns": [r"(^|_)warp"]},
        {"id": "praxis", "name": "Praxis", "patterns": [r"praxis"]},
        {"id": "dream", "name": "Dream substrate", "patterns": [r"dream"]},
        {"id": "istate", "name": "I-State system", "patterns": [r"i_?state"]},
        {"id": "oets", "name": "OETS ontology web", "patterns": [r"oets", r"ontolog"]},
        {"id": "icc", "name": "ICC ledger", "patterns": [r"(^|_)icc(_|$)"]},
        {"id": "rcec", "name": "RCEC", "patterns": [r"rcec"]},
        {"id": "possibility_selves", "name": "Possibility selves", "patterns": [r"possibility"]},
        {"id": "habitat", "name": "Habitat", "patterns": [r"habitat"]},
        {"id": "dual_strata", "name": "Dual strata", "patterns": [r"strata", r"subsurface"]},
        {"id": "manifold", "name": "Constraint manifold", "patterns": [r"manifold"]},
        {"id": "waveform", "name": "Waveform pressure", "patterns": [r"waveform", r"pressure"]},
        {"id": "toroidal", "name": "Toroidal circulation", "patterns": [r"toroid"]},
        {"id": "evolution", "name": "Evolution chamber", "patterns": [r"evolution", r"evolv"]},
        {"id": "language", "name": "Language faculty", "patterns": [r"language", r"lexic", r"grammar", r"vocabular"]},
        {"id": "voice", "name": "Voice", "patterns": [r"voice", r"speech"]},
        {"id": "vision", "name": "Vision", "patterns": [r"vision", r"image"]},
        {"id": "curiosity", "name": "Curiosity", "patterns": [r"curiosity"]},
        {"id": "persistence", "name": "Persistence", "patterns": [r"persist", r"checkpoint"]},
        {"id": "telemetry", "name": "Telemetry", "patterns": [r"telemetry", r"diag"]},
    ],
    "registry_files": ["known_fixes_registry.md", "docs/REGISTRY_ADDITIONS_*.md"],
    "persistence_inventory": "PERSISTENCE_INVENTORY.md",
    "manifold_directory": "aurora_manifold_directory",
    "bus_receivers": ["systems", "_systems"],
    "boundaries": [
        {"module": "aurora_internal.aurora_leverage_scalar",
         "public": ["BandPosition", "PhaseNudge", "band_position", "LeverageBiasEngine"],
         "rule": "Leverage scalar privacy boundary: only band_position and PhaseNudge deltas cross out"},
    ],
    "forbidden_imports": [
        {"module": "crystal_engine_v3", "use_instead": "crystal_engine_v3_cleaned", "rule": "FIX-I002"},
    ],
    "signal_receivers": ["pipeline_state"],
    "signal_seed_functions": {"aurora._extract_pipeline_signals": "signals"},
    # Chaquopy loads Python from these directories; getModule("x") resolves against them first
    "chaquopy_python_roots": ["flutter_app/android/app/src/main/python"],
    # how each runtime starts, for "is this reachable from that process" questions
    "runtimes": [
        {"id": "desktop", "name": "Desktop / laptop runtime",
         "entrypoints": ["fn:aurora.boot_aurora", "fn:aurora.process_external_user_turn", "mod:aurora_daemon",
                         "mod:run_aurora", "mod:aurora_runtime"]},
        {"id": "phone", "name": "Phone (Flutter + Kotlin + Chaquopy)",
         "entrypoints": ["fn:flutter_app.android.app.src.main.python.aurora_bridge.initialize"]},
        {"id": "acm", "name": "ACM kernel (Rust, bare metal)", "entrypoints": []},
    ],
    "spawn_calls": {"Thread": "thread", "Timer": "timer", "start_new_thread": "thread", "Process": "process",
                    "submit": "executor", "run_in_executor": "executor", "create_task": "task",
                    "ensure_future": "task", "call_soon": "call_later", "call_soon_threadsafe": "call_later",
                    "call_later": "call_later", "call_at": "call_later", "register": "atexit",
                    "signal": "signal", "enter": "scheduler", "enterabs": "scheduler"},
    "spawn_receivers": {"register": ["atexit"], "signal": ["signal"], "enter": [], "enterabs": []},
    "http_client_calls": ["_request", "request", "urlopen", "get", "post", "put", "delete", "_get", "_post"],
    # the one machine-readable record of declared layer and category (claims, not proven behaviour)
    "ownership_mapping": "docs/module_ownership.json",
    # parts of the repository outside that mapping, grouped by where they live (an inferred grouping)
    # the crystal hierarchy: the repository is the king quasi, each domain a quasi
    "domains": [
        {"id": "phone", "name": "Phone app (Flutter, Kotlin, Chaquopy Python)", "prefixes": ["flutter_app/"]},
        {"id": "acm", "name": "ACM kernel (Rust)", "prefixes": ["aurora-acm/"]},
        {"id": "android_native", "name": "Android native sources", "prefixes": ["src/"]},
        {"id": "tooling", "name": "Scripts, tests, deployment and CI",
         "prefixes": ["scripts/", "tests/", "deploy/", ".github/", "tools/"]},
        {"id": "desktop", "name": "Desktop runtime (Python)", "prefixes": ["aurora_internal/", "aurora_manifold_directory/"],
         "root_python": True},
    ],
    # when the mapping declares its own domains, files it leaves out are placed by prefix on these ids
    "domain_fallback": {"tooling": "desktop", "android_native": "phone"},
    "composite_min_binding": 3,
    "areas": [
        {"id": "phone_python", "prefix": "flutter_app/android/app/src/main/python/", "name": "Phone Python bridge (Chaquopy)"},
        {"id": "phone_native", "prefix": "flutter_app/android/", "name": "Phone native layer (Kotlin)"},
        {"id": "phone_ui", "prefix": "flutter_app/", "name": "Phone app (Flutter, Dart)"},
        {"id": "acm", "prefix": "aurora-acm/", "name": "ACM kernel (Rust)"},
        {"id": "android_src", "prefix": "src/", "name": "Android and other native sources"},
        {"id": "scripts", "prefix": "scripts/", "name": "Maintenance, audit and run scripts"},
        {"id": "tests", "prefix": "tests/", "name": "Test suite"},
        {"id": "deploy", "prefix": "deploy/", "name": "Deployment"},
        {"id": "workflows", "prefix": ".github/", "name": "CI workflows"},
    ],
    "exclude_dirs": [".git", "__pycache__", "node_modules", "build", ".dart_tool", ".gradle", "target",
                     "aurora_state", "aurora_state_test", "aurora_logs", "vector_data", ".venv", "venv",
                     "knowledge_graph", ".pytest_cache", ".mypy_cache"],
}

# ===========================================================================
# SECTION 3 -- PATTERNS AND SMALL HELPERS
# ===========================================================================

STORE_EXTENSIONS = ("json", "jsonl", "ndjson", "json.gz", "jsonl.gz", "gz", "db", "sqlite", "sqlite3",
                    "pkl", "pickle", "npy", "npz", "csv", "log", "pt", "parquet", "h5")
_STORE_RE = re.compile(r"^[\w\-{}./<>~]*[\w\-}]\.(?:" + "|".join(re.escape(e) for e in STORE_EXTENSIONS) + r")$")
_FIX_RE = re.compile(r"\bFIX-[A-Z]\d{3,4}[a-z]?\b")
_REGISTRY_HEADING = re.compile(r"^(#{2,3})\s+(FIX-[A-Z]\d{3,4}[a-z]?)\b(.*)$")
_BACKTICK = re.compile(r"`([^`\n]{2,160})`")
_PYFILE = re.compile(r"(?<![\w/.])([\w][\w/\-]*\.py)\b")
_IDENT_CHAIN = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*$")
_AUTH_RE = re.compile(r"Authors?:\s*Sunni\s*\(Sir\)\s*Morningstar\s*(?:&|and)\s*Cael\s*Devo", re.I)
_PY_LAUNCH = re.compile(r"python[0-9.]*(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*(?:-m\s+([\w.]+)|([\w./\\\-]+\.py))")
_SYSTEMD_EXEC = re.compile(r"^\s*(ExecStart|ExecStartPre|ExecStartPost|ExecStop|ExecReload)\s*=\s*(.+)$")
_RUST_MOD = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+(\w+)\s*;", re.M)
_RUST_USE = re.compile(r"^\s*(?:pub\s+)?use\s+crate::([\w:]+)", re.M)
_DART_IMPORT = re.compile(r"""^\s*(?:import|export|part)\s+['"]([^'"]+\.dart)['"]""", re.M)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
WRITE_HINTS = {"dump", "write", "write_text", "write_bytes", "writelines", "save", "savez", "savez_compressed",
               "savetxt", "to_csv", "to_json", "replace", "rename", "atomic_write", "_atomic_write",
               "save_json", "write_json", "dump_json", "_write_json", "_save_json", "persist", "touch",
               "unlink", "copyfile", "copy", "copy2", "move", "rmtree", "mkdir"}
READ_HINTS = {"load", "loads", "read", "read_text", "read_bytes", "readlines", "exists", "is_file",
              "load_json", "read_json", "_load_json", "_read_json", "glob", "rglob", "iterdir", "stat",
              "getmtime", "getsize", "isfile", "listdir", "fromfile", "read_csv"}
MUTATORS = {"append", "extend", "update", "add", "insert", "setdefault", "pop", "popitem", "remove", "clear",
            "discard", "appendleft", "extendleft", "popleft", "put", "put_nowait", "sort", "reverse"}
SYSTEMS_READ_METHODS = {"get", "pop"}
SYSTEMS_WRITE_METHODS = {"setdefault"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
BUILTINS = set(dir(__builtins__)) if not isinstance(__builtins__, dict) else set(__builtins__.keys())


def first_line(text: Optional[str], cap: int = DOCSTRING_CAP) -> str:
    if not text:
        return ""
    for line in text.strip().splitlines():
        line = line.strip()
        if line:
            return line[:cap]
    return ""


def dotted(expr: ast.AST) -> Optional[str]:
    """Name / Attribute chain to 'a.b.c', else None."""
    parts: List[str] = []
    while isinstance(expr, ast.Attribute):
        parts.append(expr.attr)
        expr = expr.value
    if isinstance(expr, ast.Name):
        parts.append(expr.id)
        return ".".join(reversed(parts))
    return None


def call_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def complexity(node: ast.AST) -> int:
    """McCabe-style count over a def's own body (nested defs excluded)."""
    score = 1
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler, ast.Assert)):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            score += 1 + len(n.ifs)
        elif hasattr(ast, "match_case") and isinstance(n, ast.match_case):
            score += 1
        stack.extend(ast.iter_child_nodes(n))
    return score


def iter_stmts(body: Iterable[ast.stmt]) -> Iterator[ast.stmt]:
    """Every statement in a body, depth first, in source order, stopping at nested defs and classes."""
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield stmt
        for name in ("body", "orelse", "finalbody"):
            sub = getattr(stmt, name, None)
            if isinstance(sub, list) and sub and isinstance(sub[0], ast.stmt):
                yield from iter_stmts(sub)
        for handler in getattr(stmt, "handlers", None) or []:
            yield from iter_stmts(handler.body)
        for case in getattr(stmt, "cases", None) or []:
            yield from iter_stmts(case.body)


def own_exprs(stmt: ast.stmt) -> List[ast.AST]:
    """The expressions that belong to a statement itself, not to its child statements."""
    out: List[ast.AST] = []
    for _field, value in ast.iter_fields(stmt):
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, ast.stmt):
                continue
            if isinstance(item, ast.expr):
                out.append(item)
            elif isinstance(item, ast.withitem):
                out.append(item.context_expr)
                if item.optional_vars is not None:
                    out.append(item.optional_vars)
            elif isinstance(item, ast.ExceptHandler):
                if item.type is not None:
                    out.append(item.type)
            elif isinstance(item, ast.keyword):
                out.append(item.value)
            elif hasattr(ast, "match_case") and isinstance(item, ast.match_case):
                if item.guard is not None:
                    out.append(item.guard)
    return out


def walk_expr(expr: ast.AST) -> Iterator[ast.AST]:
    """ast.walk that does not enter nested defs or classes (lambdas are kept)."""
    stack = [expr]
    while stack:
        n = stack.pop()
        yield n
        for child in ast.iter_child_nodes(n):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            stack.append(child)


def joined_template(js: ast.JoinedStr) -> str:
    parts = []
    for v in js.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        else:
            parts.append("{}")
    return "".join(parts)


def normalize_store(literal: str) -> Optional[str]:
    """A string that names a persisted file, as a path relative to the state dir, or None."""
    s = literal.strip().replace("\\", "/")
    if not s or len(s) > 200 or "\n" in s or " " in s or not _STORE_RE.match(s):
        return None
    s = re.sub(r"\{[^}]*\}", "{}", s)
    s = re.sub(r"<[^>]*>/", "", s)
    if s.startswith(("/", "~")) or re.match(r"^[A-Za-z]:/", s):
        if "aurora_state/" in s:
            s = s[s.index("aurora_state/"):]
        else:
            s = s.rsplit("/", 1)[-1]
    while s.startswith("./"):
        s = s[2:]
    while s.startswith("{}/"):
        s = s[3:]
    if s.startswith("aurora_state/"):
        s = s[len("aurora_state/"):]
    stem = s.rsplit("/", 1)[-1].split(".", 1)[0]
    if len(re.sub(r"[^A-Za-z0-9]", "", stem)) < 2 or "*" in s:
        return None
    return s


def safe_xml(value: Any) -> str:
    return _CONTROL.sub("", str(value))


# ===========================================================================
# SECTION 4 -- THE GRAPH
# ===========================================================================

class Graph:
    """Nodes keyed by id; edges keyed by (source, type, target) and aggregated.

    Every evidence site is kept.  The canonical record shows the first EVIDENCE_CAP sites (sorted)
    and the count; the rest go to evidence/<TYPE>.jsonl.  provenance is the sorted set of every
    source that produced the edge, and basis follows from it (PROVENANCE_BASIS).  observed holds
    per-scenario execution counts when a recorded run took this edge."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self.evidence: Dict[Tuple[str, str, str], Set[Tuple[str, int]]] = defaultdict(set)

    def add_node(self, nid: str, ntype: str, **attrs: Any) -> str:
        node = self.nodes.get(nid)
        if node is None:
            node = {"id": nid, "type": ntype}
            self.nodes[nid] = node
        for k, v in attrs.items():
            if v is None:
                continue
            if k not in node or node[k] in (None, "", [], False):
                node[k] = v
        return nid

    def add_edge(self, src: str, etype: str, dst: str, evidence: Optional[Tuple[str, int]] = None,
                 provenance: str = "ast", confidence: float = 1.0, **attrs: Any) -> Dict[str, Any]:
        key = (src, etype, dst)
        edge = self.edges.get(key)
        if src == dst and etype not in ("CALLS", "FEEDS", "SPAWNS"):
            return edge or {}
        if edge is None:
            edge = {"source": src, "type": etype, "target": dst, "weight": 0, "provenance": [],
                    "confidence": confidence}
            self.edges[key] = edge
        if provenance != "runtime":
            edge["weight"] += 1
        if provenance not in edge["provenance"]:
            edge["provenance"] = sorted(edge["provenance"] + [provenance])
        edge["confidence"] = max(edge["confidence"], confidence)
        if evidence is not None:
            self.evidence[key].add((evidence[0], int(evidence[1])))
        for k, v in attrs.items():
            if isinstance(v, list):
                edge[k] = sorted(set(edge.get(k, [])) | set(v))
            elif isinstance(v, bool) and k == "lazy":
                edge[k] = edge.get(k, True) and v
            elif isinstance(v, dict) and k == "observed":
                obs = edge.setdefault("observed", {})
                for sk, sv in v.items():
                    obs[sk] = obs.get(sk, 0) + int(sv)
            elif v is not None and k not in edge:
                edge[k] = v
        return edge

    def finalize(self) -> None:
        """Fill evidence, evidence_count and basis on every edge; call once, after the last pass."""
        for key, edge in self.edges.items():
            ev = sorted(self.evidence.get(key, ()))
            edge["evidence"] = [[a, b] for a, b in ev[:EVIDENCE_CAP]]
            edge["evidence_count"] = len(ev)
            edge["basis"] = sorted({PROVENANCE_BASIS.get(pv, "implemented") for pv in edge["provenance"]})

    def full_evidence(self, key: Tuple[str, str, str]) -> List[List[Any]]:
        return [[a, b] for a, b in sorted(self.evidence.get(key, ()))]

    def out_edges(self) -> Dict[str, List[Dict[str, Any]]]:
        idx: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in self.edges.values():
            idx[e["source"]].append(e)
        return idx

    def in_edges(self) -> Dict[str, List[Dict[str, Any]]]:
        idx: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in self.edges.values():
            idx[e["target"]].append(e)
        return idx

    def sorted_nodes(self) -> List[Dict[str, Any]]:
        return [self.nodes[k] for k in sorted(self.nodes)]

    def sorted_edges(self) -> List[Dict[str, Any]]:
        return [self.edges[k] for k in sorted(self.edges)]

    def content_hash(self, include_observed: bool = True) -> str:
        """Hash of the graph's content.  check compares the static part only (include_observed=False),
        so a new recorded run does not make the committed graph look stale."""
        h = hashlib.sha256()
        for n in self.sorted_nodes():
            rec = n if include_observed else {k: v for k, v in n.items() if not k.startswith("observed")}
            h.update(json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        for e in self.sorted_edges():
            if not include_observed:
                if e["provenance"] == ["runtime"]:
                    continue
                rec = {k: v for k, v in e.items() if k != "observed"}
                rec["provenance"] = [x for x in e["provenance"] if x != "runtime"]
                rec["basis"] = [x for x in e.get("basis", []) if x != "observed"]
            else:
                rec = e
            h.update(json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()


# ===========================================================================
# SECTION 5 -- SOURCE MODEL
# ===========================================================================

class ClassInfo:
    def __init__(self, cid: str, name: str, qual: str, module: "ModuleInfo", node: ast.ClassDef) -> None:
        self.cid = cid
        self.name = name
        self.qual = qual
        self.module = module
        self.node = node
        self.methods: Dict[str, str] = {}
        self.nested: Dict[str, str] = {}
        self.base_ids: List[str] = []
        self.external_bases: List[str] = []
        self.attr_types: Dict[str, str] = {}
        self.holders: Dict[str, Set[str]] = defaultdict(set)
        self.assigned_attrs: Set[str] = set()   # names given a value through self.X or the class body


class FuncInfo:
    def __init__(self, fid: str, node: ast.AST, module: "ModuleInfo", ctx_cls: Optional[ClassInfo],
                 owner_cls: Optional[ClassInfo], parent: Optional["FuncInfo"]) -> None:
        self.fid = fid
        self.node = node
        self.module = module
        self.ctx_cls = ctx_cls          # class whose `self` is in scope (also for nested functions)
        self.owner_cls = owner_cls      # class this is a direct method of, if any
        self.parent = parent
        self.nested: Dict[str, str] = {}


class ModuleInfo:
    def __init__(self, path: Path, rel: str, name: str, is_init: bool, dir_is_package: bool) -> None:
        self.path = path
        self.rel = rel
        self.name = name
        self.nid = "mod:" + name
        self.is_init = is_init
        if is_init:
            self.package = name
        else:
            self.package = name.rsplit(".", 1)[0] if ("." in name and dir_is_package) else ""
        parent_dir = rel.rsplit("/", 1)[0] if "/" in rel else ""
        self.dir_prefix = parent_dir.replace("/", ".") if (parent_dir and not dir_is_package) else ""
        self.source = ""
        self.tree: Optional[ast.Module] = None
        self.aliases: Dict[str, Tuple[str, ...]] = {}
        self.star: List[str] = []
        self.defs: Dict[str, str] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.funcs: List[FuncInfo] = []
        self.holders: Dict[str, Set[str]] = defaultdict(set)
        self.spans: List[Tuple[int, int, str]] = []
        self.role = ""
        self.module_assigned: Set[str] = set()   # names bound at module level
        self.globals_declared: Set[str] = set()  # names some function declares global
        self.state_names: Set[str] = set()       # module-level names that functions change
        self.global_types: Dict[str, str] = {}   # module-level name -> class id, when known


# ===========================================================================
# SECTION 6 -- THE BUILDER
# ===========================================================================

class Builder:
    def __init__(self, root: Path, ontology: Dict[str, Any], include_tests: bool = True,
                 quiet: bool = False) -> None:
        self.root = root.resolve()
        self.ont = ontology
        self.include_tests = include_tests
        self.quiet = quiet
        self.g = Graph()
        self.mods: Dict[str, ModuleInfo] = {}
        self.mod_by_id: Dict[str, ModuleInfo] = {}
        self.mod_by_rel: Dict[str, ModuleInfo] = {}
        self.mods_by_basename: Dict[str, List[ModuleInfo]] = defaultdict(list)
        self.class_by_id: Dict[str, ClassInfo] = {}
        self.func_by_id: Dict[str, FuncInfo] = {}
        self.parent_of: Dict[str, str] = {}
        self.suffix_index: Dict[str, Set[str]] = defaultdict(set)
        self.mentioned_names: Counter = Counter()
        self.mentioned_strings: Set[str] = set()
        self.unresolved_calls: Counter = Counter()
        self.unresolved_sites: List[Tuple[str, str, int, str, str]] = []   # owner, path, line, expr, reason
        self.fn_returns: Dict[str, str] = {}      # function id -> class id from its return annotation
        self.flow_stats: Counter = Counter()
        self.file_inventory: Dict[str, Dict[str, Any]] = {}
        self.observations: List[Dict[str, Any]] = []
        self.repo_files_by_basename: Dict[str, List[str]] = defaultdict(list)
        self.repo_files: Set[str] = set()
        self.exclude = set(ontology.get("exclude_dirs", []))
        self.receivers = set(ontology.get("bus_receivers", ["systems"]))
        axes = ontology["constraint_axes"]
        self.axis_symbols = [a["symbol"] for a in axes]
        adjectives = "|".join(re.escape(a["adjective"]) for a in axes)
        dims = "|".join(d.title() for d in ontology["noncomp_dimensions"])
        # word boundaries would fail on "Agentive_Cost_of_Existence" because "_" is a word character
        self.nc_re = re.compile(r"(?<![A-Za-z])(" + adjectives + r")[_ ](" + dims + r")(?![a-z])")
        self.stats: Counter = Counter()
        self.warnings: List[str] = []

    # ---------------------------------------------------------------- logging
    def log(self, msg: str) -> None:
        if not self.quiet:
            print(f"[aurora-kg] {msg}", file=sys.stderr, flush=True)

    # ------------------------------------------------------------- discovery
    def _walk_files(self) -> Iterator[Path]:
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in self.exclude and not d.startswith(".")
                                 or d == ".github")
            for fn in sorted(filenames):
                yield Path(dirpath) / fn

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def discover(self) -> Tuple[List[Path], List[Path], List[Path]]:
        py, md, other = [], [], []
        for p in self._walk_files():
            r = self.rel(p)
            self.repo_files.add(r)
            self.repo_files_by_basename[p.name].append(r)
            if p.suffix == ".py":
                if not self.include_tests and self._is_test_rel(r):
                    continue
                py.append(p)
            elif p.suffix == ".md":
                md.append(p)
            elif self._other_language(r):
                other.append(p)
        # the state dir is excluded from scanning but its file names still identify stores
        for sd in ("aurora_state",):
            base = self.root / sd
            if base.is_dir():
                for dirpath, _dn, filenames in os.walk(base):
                    for fn in filenames:
                        r = (Path(dirpath) / fn).relative_to(self.root).as_posix()
                        self.repo_files.add(r)
                        self.repo_files_by_basename[fn].append(r)
        return py, md, other

    @staticmethod
    def _is_test_rel(r: str) -> bool:
        base = r.rsplit("/", 1)[-1]
        return r.startswith("tests/") or base.startswith("test_") or base == "conftest.py"

    @staticmethod
    def _other_language(r: str) -> Optional[str]:
        suffix_map = {".rs": "rust", ".dart": "dart", ".kt": "kotlin", ".java": "java", ".sh": "shell", ".bat": "batch",
                      ".ps1": "powershell", ".jsx": "jsx", ".js": "javascript", ".html": "html",
                      ".service": "systemd"}
        if r.startswith(".github/workflows/") and r.endswith((".yml", ".yaml")):
            return "github-workflow"
        for s, lang in suffix_map.items():
            if r.endswith(s):
                return lang
        return None

    def module_name_for(self, rel: str) -> Tuple[str, bool, bool]:
        parts = rel[:-3].split("/")
        is_init = parts[-1] == "__init__"
        if is_init:
            parts = parts[:-1]
        dir_is_package = (self.root / rel).parent.joinpath("__init__.py").exists()
        return ".".join(parts), is_init, dir_is_package

    def role_for(self, m: ModuleInfo) -> str:
        r = m.rel
        if m.is_init:
            return "package_init"
        if self._is_test_rel(r):
            return "test"
        if r.startswith("scripts/"):
            return "script"
        if r.startswith("aurora_internal/"):
            return "internal"
        if r.startswith(("flutter_app/", "aurora-acm/")):
            return "app"
        if "/" in r:
            return "tool"
        return "core"

    # ================================================================ PASS 1
    def pass_define(self, py_files: List[Path]) -> None:
        self.g.add_node("repo:aurora", "Repository", name=self.root.name, path=".")
        for p in py_files:
            rel = self.rel(p)
            name, is_init, dir_pkg = self.module_name_for(rel)
            if not name or name in self.mods:
                self.warnings.append(f"duplicate or empty module name for {rel}; skipped")
                continue
            m = ModuleInfo(p, rel, name, is_init, dir_pkg)
            self.mods[name] = m
            self.mod_by_id[m.nid] = m
            self.mod_by_rel[rel] = m
            self.mods_by_basename[p.name].append(m)
        for m in sorted(self.mods.values(), key=lambda x: x.rel):
            self._define_module(m)
        self.log(f"pass 1: {len(self.mods)} modules, {len(self.class_by_id)} classes, "
                 f"{len(self.func_by_id)} functions")

    def _package_chain(self, m: ModuleInfo) -> None:
        pkg = m.package if m.is_init else m.package
        parent = "repo:aurora"
        if pkg:
            parts = pkg.split(".")
            for i in range(1, len(parts) + 1):
                pname = ".".join(parts[:i])
                pid = "pkg:" + pname
                self.g.add_node(pid, "Package", name=pname, path="/".join(parts[:i]))
                self.g.add_edge(parent, "CONTAINS", pid, provenance="filesystem")
                parent = pid
        self.g.add_edge(parent, "CONTAINS", m.nid, provenance="filesystem")
        self.parent_of[m.nid] = parent

    def _define_module(self, m: ModuleInfo) -> None:
        import warnings
        m.source = m.path.read_text(encoding="utf-8", errors="replace")
        parse_error = None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                m.tree = ast.parse(m.source, filename=m.rel)
            except (SyntaxError, ValueError) as exc:
                parse_error = f"{type(exc).__name__}: {getattr(exc, 'msg', exc)} (line {getattr(exc, 'lineno', '?')})"
        m.role = self.role_for(m)
        # the header is a comment line (FIX-F002 puts it after the module docstring) or sits in the docstring
        module_doc = (ast.get_docstring(m.tree) or "") if m.tree else ""
        has_header = bool(_AUTH_RE.search(module_doc)) or any(
            _AUTH_RE.search(line) for line in m.source.splitlines() if line.lstrip().startswith("#"))
        base = m.rel.rsplit("/", 1)[-1]
        self.g.add_node(
            m.nid, "Module", name=m.name, path=m.rel, role=m.role,
            loc=m.source.count("\n") + (0 if m.source.endswith("\n") else 1),
            sha1=hashlib.sha1(m.source.encode("utf-8", "replace")).hexdigest()[:12],
            has_authorship_header=has_header,
            aurora_prefix=base.startswith("aurora") or m.is_init,
            docstring=first_line(ast.get_docstring(m.tree)) if m.tree else "",
            parse_error=parse_error, is_entrypoint=False,
        )
        self._package_chain(m)
        self._index_suffixes(m.nid, m.name)
        if m.tree is None:
            self.stats["parse_errors"] += 1
            return
        if any(self._is_main_guard(s) for s in m.tree.body):
            self.g.nodes[m.nid]["is_entrypoint"] = True
        # a script that does its work at import time, with no main guard
        self.g.nodes[m.nid]["runs_on_import"] = any(
            isinstance(s, ast.Expr) and isinstance(s.value, (ast.Call, ast.Await)) for s in m.tree.body)
        self._define_body(m, m.tree.body, m.nid, m.name, ctx_cls=None, in_class=None, parent_fn=None)

    @staticmethod
    def _is_main_guard(stmt: ast.stmt) -> bool:
        if not isinstance(stmt, ast.If) or not isinstance(stmt.test, ast.Compare):
            return False
        t = stmt.test
        names = [dotted(t.left)] + [c.value if isinstance(c, ast.Constant) else dotted(c) for c in t.comparators]
        return "__name__" in names and "__main__" in names

    @staticmethod
    def _iter_defs(body: Iterable[ast.stmt]) -> Iterator[ast.stmt]:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                yield stmt
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                yield stmt
            else:
                for name in ("body", "orelse", "finalbody"):
                    sub = getattr(stmt, name, None)
                    if isinstance(sub, list) and sub and isinstance(sub[0], ast.stmt):
                        yield from Builder._iter_defs(sub)
                for h in getattr(stmt, "handlers", None) or []:
                    yield from Builder._iter_defs(h.body)
                for c in getattr(stmt, "cases", None) or []:
                    yield from Builder._iter_defs(c.body)

    def _index_suffixes(self, nid: str, qual: str) -> None:
        parts = qual.split(".")
        for i in range(len(parts)):
            key = ".".join(parts[i:])
            self.suffix_index[key].add(nid)

    def _decorators(self, node: ast.AST) -> List[str]:
        out = []
        for d in getattr(node, "decorator_list", []):
            target = d.func if isinstance(d, ast.Call) else d
            name = dotted(target) or ast.unparse(target)[:60]
            out.append(name)
        return out

    def _define_body(self, m: ModuleInfo, body: List[ast.stmt], parent_id: str, qual: str,
                     ctx_cls: Optional[ClassInfo], in_class: Optional[ClassInfo],
                     parent_fn: Optional[FuncInfo]) -> None:
        for stmt in self._iter_defs(body):
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                if parent_fn is None:
                    self._define_constant(m, stmt, parent_id, qual)
                continue
            name = stmt.name
            sub_qual = f"{qual}.{name}"
            end = getattr(stmt, "end_lineno", stmt.lineno) or stmt.lineno
            decorators = self._decorators(stmt)
            if isinstance(stmt, ast.ClassDef):
                cid = "cls:" + sub_qual
                info = ClassInfo(cid, name, sub_qual, m, stmt)
                bases = []
                for b in stmt.bases:
                    try:
                        bases.append(ast.unparse(b)[:80])
                    except Exception:
                        bases.append("?")
                self.g.add_node(cid, "Class", name=name, qualname=sub_qual[len(m.name) + 1:], module=m.name,
                                path=m.rel, line=stmt.lineno, end_line=end, loc=end - stmt.lineno + 1,
                                decorators=decorators, bases=bases, docstring=first_line(ast.get_docstring(stmt)),
                                is_dataclass=any(d.split(".")[-1] == "dataclass" for d in decorators))
                self.g.add_edge(parent_id, "CONTAINS", cid, evidence=(m.rel, stmt.lineno))
                self.parent_of[cid] = parent_id
                self.class_by_id[cid] = info
                m.classes[cid] = info
                m.spans.append((stmt.lineno, end, cid))
                self._index_suffixes(cid, sub_qual)
                if in_class is not None:
                    in_class.nested[name] = cid
                elif parent_fn is not None:
                    parent_fn.nested[name] = cid
                else:
                    m.defs.setdefault(name, cid)
                self._define_body(m, stmt.body, cid, sub_qual, ctx_cls=info, in_class=info, parent_fn=None)
                continue
            fid = "fn:" + sub_qual
            is_async = isinstance(stmt, ast.AsyncFunctionDef)
            if in_class is not None:
                kind = "method"
                for d in decorators:
                    tail = d.split(".")[-1]
                    if tail in ("staticmethod", "classmethod"):
                        kind = tail
                    elif tail in ("property", "setter", "getter", "deleter", "cached_property"):
                        kind = "property"
            elif parent_fn is not None:
                kind = "nested"
            else:
                kind = "function"
            try:
                signature = ast.unparse(stmt.args)[:SIGNATURE_CAP]
            except Exception:
                signature = ""
            existing = fid in self.g.nodes
            self.g.add_node(fid, "Function", name=name, qualname=sub_qual[len(m.name) + 1:], module=m.name,
                            path=m.rel, line=stmt.lineno, end_line=end, loc=end - stmt.lineno + 1,
                            kind=kind, is_async=is_async, signature=f"({signature})", decorators=decorators,
                            docstring=first_line(ast.get_docstring(stmt)), complexity=complexity(stmt),
                            body_hash=hashlib.sha256(ast.dump(stmt, annotate_fields=False,
                                                              include_attributes=False).encode()).hexdigest()[:16],
                            early_returns=self._early_returns(stmt) or None)
            if existing:
                self.g.nodes[fid]["redefinitions"] = self.g.nodes[fid].get("redefinitions", 0) + 1
            self.g.add_edge(parent_id, "CONTAINS", fid, evidence=(m.rel, stmt.lineno))
            self.parent_of[fid] = parent_id
            info_f = FuncInfo(fid, stmt, m, ctx_cls, in_class, parent_fn)
            if not existing:
                self.func_by_id[fid] = info_f
                m.funcs.append(info_f)
            m.spans.append((stmt.lineno, end, fid))
            self._index_suffixes(fid, sub_qual)
            if in_class is not None:
                in_class.methods.setdefault(name, fid)
            elif parent_fn is not None:
                parent_fn.nested.setdefault(name, fid)
            else:
                m.defs.setdefault(name, fid)
            self._define_body(m, stmt.body, fid, sub_qual, ctx_cls=ctx_cls, in_class=None,
                              parent_fn=self.func_by_id.get(fid, info_f))

    @staticmethod
    def _early_returns(fn: ast.AST) -> List[Dict[str, Any]]:
        """Guards near the top of a function that answer early with a fixed value: where a caller can get
        a default instead of the real state (if _systems is None: return {"error": ...})."""
        out: List[Dict[str, Any]] = []
        for st in list(getattr(fn, "body", []))[:20]:
            if not isinstance(st, ast.If) or not st.body or not isinstance(st.body[-1], ast.Return):
                continue
            val = st.body[-1].value
            if val is None or isinstance(val, (ast.Constant, ast.Dict, ast.List, ast.Tuple)) or (
                    isinstance(val, ast.Call) and (dotted(val.func) or "").endswith(("dumps", "_status", "_json"))):
                try:
                    out.append({"line": st.lineno, "cond": ast.unparse(st.test)[:100],
                                "returns": ast.unparse(val)[:100] if val is not None else "None"})
                except Exception:
                    continue
        return out[:6]

    def _define_constant(self, m: ModuleInfo, stmt: ast.stmt, parent_id: str, qual: str) -> None:
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        for t in targets:
            if isinstance(t, ast.Name) and re.match(r"^[A-Z][A-Z0-9_]{2,}$", t.id):
                kid = f"const:{qual}.{t.id}"
                preview = ""
                if stmt.value is not None:
                    try:
                        preview = ast.unparse(stmt.value)[:80]
                    except Exception:
                        preview = ""
                self.g.add_node(kid, "Constant", name=t.id, module=m.name, path=m.rel, line=stmt.lineno,
                                value_preview=preview)
                self.g.add_edge(parent_id, "CONTAINS", kid, evidence=(m.rel, stmt.lineno))
                self.parent_of[kid] = parent_id

    # ================================================================ PASS 2
    def resolve_module_name(self, name: str, importer: ModuleInfo) -> Optional[str]:
        if name in self.mods:
            return name
        if importer.dir_prefix:
            cand = f"{importer.dir_prefix}.{name}"
            if cand in self.mods:
                return cand
        return None

    def resolve_relative(self, importer: ModuleInfo, level: int, module: Optional[str]) -> Optional[str]:
        pkg = importer.package.split(".") if importer.package else []
        if importer.dir_prefix and not pkg:
            pkg = importer.dir_prefix.split(".")
        drop = level - 1
        if drop > len(pkg):
            return None
        base = pkg[:len(pkg) - drop] if drop else pkg
        full = ".".join(base + ([module] if module else []))
        return full if full in self.mods else None

    def _ext_node(self, top: str) -> str:
        eco = "stdlib" if top in STDLIB else ("builtins" if top == "builtins" else "third_party")
        return self.g.add_node("ext:" + top, "ExternalDependency", name=top, ecosystem=eco)

    def pass_imports(self) -> None:
        for m in sorted(self.mods.values(), key=lambda x: x.rel):
            if m.tree is None:
                continue
            top_level: Set[int] = set()
            for stmt in iter_stmts(m.tree.body):
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    top_level.add(id(stmt))
            nodes = [n for n in ast.walk(m.tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
            nodes.sort(key=lambda n: (id(n) not in top_level, n.lineno))
            for node in nodes:
                lazy = id(node) not in top_level
                ev = (m.rel, node.lineno)
                if isinstance(node, ast.Import):
                    for a in node.names:
                        target = self._deepest_internal(a.name, m)
                        bind = a.asname or a.name.split(".")[0]
                        if target:
                            self.g.add_edge(m.nid, "IMPORTS", self.mods[target].nid, evidence=ev,
                                            names=[a.name], lazy=lazy)
                            if a.asname:
                                m.aliases.setdefault(bind, ("mod", target))
                            else:
                                head = self.resolve_module_name(a.name.split(".")[0], m)
                                if head:
                                    m.aliases.setdefault(bind, ("mod", head))
                        else:
                            top = a.name.split(".")[0]
                            self.g.add_edge(m.nid, "IMPORTS", self._ext_node(top), evidence=ev,
                                            names=[a.name], lazy=lazy)
                            m.aliases.setdefault(bind, ("ext", top, a.name if a.asname else top))
                    continue
                if node.level:
                    src_mod = self.resolve_relative(m, node.level, node.module)
                else:
                    src_mod = self.resolve_module_name(node.module or "", m) if node.module else None
                if src_mod is None:
                    if node.level or not node.module:
                        self.warnings.append(f"{m.rel}:{node.lineno} unresolved relative import")
                        continue
                    top = node.module.split(".")[0]
                    ext = self._ext_node(top)
                    self.g.add_edge(m.nid, "IMPORTS", ext, evidence=ev,
                                    names=sorted(a.name for a in node.names), lazy=lazy)
                    for a in node.names:
                        m.aliases.setdefault(a.asname or a.name, ("ext", top, f"{node.module}.{a.name}"))
                    continue
                names = []
                for a in node.names:
                    if a.name == "*":
                        m.star.append(src_mod)
                        names.append("*")
                        continue
                    names.append(a.name)
                    sub = f"{src_mod}.{a.name}"
                    if sub in self.mods:
                        self.g.add_edge(m.nid, "IMPORTS", self.mods[sub].nid, evidence=ev, names=[], lazy=lazy)
                        m.aliases.setdefault(a.asname or a.name, ("mod", sub))
                    else:
                        m.aliases.setdefault(a.asname or a.name, ("sym", src_mod, a.name))
                self.g.add_edge(m.nid, "IMPORTS", self.mods[src_mod].nid, evidence=ev, names=names, lazy=lazy)
        self.log("pass 2: imports resolved")

    def _deepest_internal(self, dotted_name: str, importer: ModuleInfo) -> Optional[str]:
        parts = dotted_name.split(".")
        for i in range(len(parts), 0, -1):
            r = self.resolve_module_name(".".join(parts[:i]), importer)
            if r:
                return r
        return None

    # ---------------------------------------------------------- resolution
    def resolve_name(self, m: ModuleInfo, name: str, depth: int = 0) -> Optional[str]:
        nid = m.defs.get(name)
        if nid:
            return nid
        a = m.aliases.get(name)
        if a:
            if a[0] == "mod":
                return self.mods[a[1]].nid
            if a[0] == "sym" and depth < 6:
                tm = self.mods.get(a[1])
                return self.resolve_name(tm, a[2], depth + 1) if tm else None
            return None
        if depth < 6:
            for s in m.star:
                tm = self.mods.get(s)
                r = self.resolve_name(tm, name, depth + 1) if tm else None
                if r:
                    return r
        return None

    def member(self, nid: str, name: str) -> Optional[str]:
        if nid.startswith("mod:"):
            mm = self.mod_by_id.get(nid)
            if mm is None:
                return None
            sub = f"{mm.name}.{name}"
            if sub in self.mods:
                return self.mods[sub].nid
            return self.resolve_name(mm, name)
        if nid.startswith("cls:"):
            c = self.class_by_id.get(nid)
            if c is None:
                return None
            if name in c.nested:
                return c.nested[name]
            return self.find_method(nid, name)
        return None

    def resolve_chain(self, m: ModuleInfo, chain: str, local: Optional[Dict[str, str]] = None) -> Optional[str]:
        parts = chain.split(".")
        cur = (local or {}).get(parts[0]) or self.resolve_name(m, parts[0])
        for p in parts[1:]:
            if cur is None:
                return None
            cur = self.member(cur, p)
        return cur

    def mro(self, cid: str) -> List[str]:
        out, seen, stack = [], set(), [cid]
        while stack:
            c = stack.pop(0)
            if c in seen:
                continue
            seen.add(c)
            out.append(c)
            info = self.class_by_id.get(c)
            if info:
                stack.extend(info.base_ids)
        return out

    def find_method(self, cid: str, name: str, skip_self: bool = False) -> Optional[str]:
        for c in self.mro(cid):
            if skip_self and c == cid:
                continue
            info = self.class_by_id.get(c)
            if info and name in info.methods:
                return info.methods[name]
        return None

    def attr_type(self, cid: str, attr: str) -> Optional[str]:
        for c in self.mro(cid):
            info = self.class_by_id.get(c)
            if info and attr in info.attr_types:
                return info.attr_types[attr]
        return None

    def class_holders(self, cid: str, attr: str) -> Set[str]:
        for c in self.mro(cid):
            info = self.class_by_id.get(c)
            if info and attr in info.holders:
                return info.holders[attr]
        return set()

    def annotation_class(self, m: ModuleInfo, ann: Optional[ast.AST]) -> Optional[str]:
        if ann is None:
            return None
        if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
            chain = ann.value.strip().strip("'\"")
            r = self.resolve_chain(m, chain) if _IDENT_CHAIN.match(chain) else None
            return r if r and r.startswith("cls:") else None
        if isinstance(ann, ast.Subscript):
            head = dotted(ann.value) or ""
            if head.split(".")[-1] in ("Optional", "Final", "ClassVar", "Annotated"):
                inner = ann.slice
                if isinstance(inner, ast.Tuple) and inner.elts:
                    inner = inner.elts[0]
                return self.annotation_class(m, inner)
            return None
        if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
            return self.annotation_class(m, ann.left) or self.annotation_class(m, ann.right)
        chain = dotted(ann)
        if chain:
            r = self.resolve_chain(m, chain)
            return r if r and r.startswith("cls:") else None
        return None

    def call_class(self, m: ModuleInfo, value: Optional[ast.AST], local: Optional[Dict[str, str]] = None) -> Optional[str]:
        """The class a value is an instance of, when the code shows it: a constructor call, a call to a
        function whose return annotation names a class, a typed local, or typed module state."""
        if isinstance(value, ast.Await):
            value = value.value
        if isinstance(value, ast.Call):
            chain = dotted(value.func)
            if chain:
                r = self.resolve_chain(m, chain, local)
                if r and r.startswith("cls:"):
                    return r
                if r and r.startswith("fn:") and r in self.fn_returns:
                    return self.fn_returns[r]
        if isinstance(value, ast.Name):
            if local and value.id in local:
                return local[value.id]
            if value.id in m.global_types:
                return m.global_types[value.id]
        return None

    # ================================================================ PASS 3
    def store_literals(self, expr: ast.AST) -> List[Tuple[str, int]]:
        found: List[Tuple[str, int]] = []
        inside: Set[int] = set()
        for n in walk_expr(expr):
            if isinstance(n, ast.JoinedStr):
                for v in n.values:
                    inside.add(id(v))
                s = normalize_store(joined_template(n))
                if s:
                    found.append((s, n.lineno))
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in inside:
                s = normalize_store(n.value)
                if s:
                    found.append((s, getattr(n, "lineno", 0)))
        return found

    def store_node(self, s: str) -> str:
        sid = "store:" + s
        if sid not in self.g.nodes:
            ext = ""
            for e in sorted(STORE_EXTENSIONS, key=len, reverse=True):
                if s.endswith("." + e):
                    ext = e
                    break
            base = s.rsplit("/", 1)[-1]
            locations = []
            if "{}" not in s:
                exact = [r for r in (f"aurora_state/{s}", s) if r in self.repo_files]
                locations = exact or sorted(self.repo_files_by_basename.get(base, []))[:5]
            self.g.add_node(sid, "StateStore", name=s, format=ext, templated="{}" in s,
                            exists_in_repo=bool(locations), locations=locations[:5])
        return sid

    def pass_classes(self) -> None:
        # return annotations that name a class type the values functions hand back
        for f in self.func_by_id.values():
            t = self.annotation_class(f.module, getattr(f.node, "returns", None))
            if t:
                self.fn_returns[f.fid] = t
        for c in sorted(self.class_by_id.values(), key=lambda x: x.cid):
            m = c.module
            for b in c.node.bases:
                target = b.value if isinstance(b, ast.Subscript) else b
                chain = dotted(target)
                if not chain:
                    continue
                r = self.resolve_chain(m, chain)
                if r and r.startswith("cls:"):
                    c.base_ids.append(r)
                    self.g.add_edge(c.cid, "INHERITS", r, evidence=(m.rel, c.node.lineno))
                    continue
                head = chain.split(".")[0]
                alias = m.aliases.get(head)
                if alias and alias[0] == "ext":
                    ext = self._ext_node(alias[1])
                elif head in BUILTINS and head != "object":
                    ext = self._ext_node("builtins")
                else:
                    if head != "object":
                        c.external_bases.append(chain)
                    continue
                c.external_bases.append(chain)
                self.g.add_edge(c.cid, "INHERITS", ext, evidence=(m.rel, c.node.lineno), names=[chain])
            node = self.g.nodes[c.cid]
            all_bases = [dotted(b.value if isinstance(b, ast.Subscript) else b) or "" for b in c.node.bases]
            node["is_enum"] = any(b.split(".")[-1] in ("Enum", "IntEnum", "StrEnum", "Flag", "IntFlag")
                                  for b in all_bases)
            node["is_exception"] = any(b.split(".")[-1].endswith(("Exception", "Error")) for b in all_bases)
            # class-body attribute types and path holders
            for stmt in c.node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    t = self.annotation_class(m, stmt.annotation) or self.call_class(m, stmt.value)
                    if t:
                        c.attr_types[stmt.target.id] = t
                if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
                    tgts = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                    stores = [s for s, _ in self.store_literals(stmt.value)]
                    for t in tgts:
                        if isinstance(t, ast.Name):
                            for s in stores:
                                c.holders[t.id].add(self.store_node(s))
        # self.attr assignments inside each class's own methods
        for f in self.func_by_id.values():
            c = f.owner_cls
            if c is None:
                continue
            m = f.module
            args = f.node.args
            local: Dict[str, str] = {}
            for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
                t = self.annotation_class(m, a.annotation)
                if t:
                    local[a.arg] = t
            for stmt in iter_stmts(f.node.body):
                if isinstance(stmt, ast.Assign):
                    tgts, value, ann = stmt.targets, stmt.value, None
                elif isinstance(stmt, ast.AnnAssign):
                    tgts, value, ann = [stmt.target], stmt.value, stmt.annotation
                else:
                    continue
                for t in tgts:
                    if isinstance(t, ast.Name):
                        typ = self.call_class(m, value, local)
                        if typ:
                            local[t.id] = typ
                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                        typ = self.annotation_class(m, ann) or self.call_class(m, value, local)
                        if typ:
                            c.attr_types.setdefault(t.attr, typ)
                        if value is not None:
                            for s, _ in self.store_literals(value):
                                c.holders[t.attr].add(self.store_node(s))
        # which attributes each class gives a value, so a self.X read can find the class that holds X
        for c in self.class_by_id.values():
            for stmt in c.node.body:
                if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                    for t in (stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]):
                        if isinstance(t, ast.Name):
                            c.assigned_attrs.add(t.id)
        for f in self.func_by_id.values():
            if f.ctx_cls is None:
                continue
            for stmt in iter_stmts(f.node.body):
                for t in self._store_targets(stmt):
                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                        f.ctx_cls.assigned_attrs.add(t.attr)
        # module state: module-level names that a function rebinds (global) or mutates in place
        for m in self.mods.values():
            if m.tree is None:
                continue
            for stmt in iter_stmts(m.tree.body):
                for t in self._store_targets(stmt):
                    for nm in self._bound_names(t):
                        m.module_assigned.add(nm)
            for f in m.funcs:
                for stmt in iter_stmts(f.node.body):
                    if isinstance(stmt, ast.Global):
                        m.globals_declared.update(stmt.names)
            for f in m.funcs:
                local_names = self._local_names(f)
                for stmt in iter_stmts(f.node.body):
                    for expr in own_exprs(stmt):
                        for n in walk_expr(expr):
                            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                                    and n.func.attr in MUTATORS and isinstance(n.func.value, ast.Name):
                                nm = n.func.value.id
                                if nm in m.module_assigned and nm not in local_names:
                                    m.state_names.add(nm)
                    for t in self._store_targets(stmt):
                        base = t
                        while isinstance(base, (ast.Subscript, ast.Attribute)):
                            base = base.value
                        if isinstance(base, ast.Name) and base is not t and base.id in m.module_assigned \
                                and base.id not in local_names:
                            m.state_names.add(base.id)
            m.state_names |= (m.globals_declared & m.module_assigned) | (m.globals_declared - m.module_assigned)
            m.state_names = {nm for nm in m.state_names if not re.match(r"^[A-Z][A-Z0-9_]{2,}$", nm)
                             and nm not in m.defs}
        # the types module state takes, from annotations and from what is assigned to it
        for m in self.mods.values():
            if m.tree is None:
                continue
            for stmt in iter_stmts(m.tree.body):
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    t = self.annotation_class(m, stmt.annotation)
                    if t:
                        m.global_types[stmt.target.id] = t
            for f in m.funcs:
                for stmt in iter_stmts(f.node.body):
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                        nm = stmt.targets[0].id
                        if nm in m.globals_declared:
                            t = self.call_class(m, stmt.value, self._param_types(m, f))
                            if t:
                                m.global_types.setdefault(nm, t)
        # module-level path holders
        for m in self.mods.values():
            if m.tree is None:
                continue
            for stmt in iter_stmts(m.tree.body):
                if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
                    tgts = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                    stores = [s for s, _ in self.store_literals(stmt.value)]
                    for t in tgts:
                        if isinstance(t, ast.Name):
                            for s in stores:
                                m.holders[t.id].add(self.store_node(s))
        self.log("pass 3: inheritance, attribute types and path holders resolved")

    # ================================================================ PASS 4
    def _is_systems(self, expr: ast.AST) -> bool:
        chain = dotted(expr)
        if not chain:
            return False
        return chain in self.receivers or chain.split(".")[-1] in self.receivers and chain.startswith("self.")

    @staticmethod
    def _store_targets(stmt: ast.stmt) -> List[ast.AST]:
        if isinstance(stmt, ast.Assign):
            out: List[ast.AST] = []
            for t in stmt.targets:
                out.extend(Builder._flatten_target(t))
            return out
        if isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            return Builder._flatten_target(stmt.target) if (not isinstance(stmt, ast.AnnAssign) or stmt.value is not None) else []
        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            return Builder._flatten_target(stmt.target)
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            out = []
            for it in stmt.items:
                if it.optional_vars is not None:
                    out.extend(Builder._flatten_target(it.optional_vars))
            return out
        return []

    @staticmethod
    def _flatten_target(t: ast.AST) -> List[ast.AST]:
        if isinstance(t, (ast.Tuple, ast.List)):
            out: List[ast.AST] = []
            for e in t.elts:
                out.extend(Builder._flatten_target(e))
            return out
        if isinstance(t, ast.Starred):
            return Builder._flatten_target(t.value)
        return [t]

    @staticmethod
    def _bound_names(t: ast.AST) -> List[str]:
        return [t.id] if isinstance(t, ast.Name) else []

    def _local_names(self, f: FuncInfo) -> Set[str]:
        """Names a function binds for itself (parameters and assignments), minus those it declares global."""
        args = f.node.args
        names = {a.arg for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)}
        if args.vararg:
            names.add(args.vararg.arg)
        if args.kwarg:
            names.add(args.kwarg.arg)
        declared: Set[str] = set()
        for stmt in iter_stmts(f.node.body):
            if isinstance(stmt, (ast.Global, ast.Nonlocal)):
                declared.update(stmt.names)
            for t in self._store_targets(stmt):
                names.update(self._bound_names(t))
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                for a in stmt.names:
                    names.add((a.asname or a.name).split(".")[0])
            for h in getattr(stmt, "handlers", None) or []:
                if h.name:
                    names.add(h.name)
        names.update(f.nested)
        return names - declared

    def pass_module_aliases(self) -> None:
        """A module-level `name = known_function` (or a class) binds name to the same definition, so call sites
        that keep the old name still resolve (for example `_clamp = clamp`)."""
        n = 0
        for m in self.mods.values():
            if m.tree is None:
                continue
            for st in m.tree.body:
                if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) \
                        and isinstance(st.value, (ast.Name, ast.Attribute)):
                    tgt = st.targets[0].id
                    if tgt in m.defs:
                        continue
                    chain = ast.unparse(st.value)
                    r = self.resolve_chain(m, chain)
                    if r and r.startswith(("fn:", "cls:")):
                        m.defs[tgt] = r
                        n += 1
        self.log(f"pass 3b: {n} module-level aliases bound to their definitions")

    def pass_dispatch_tables(self) -> None:
        """A class that maps command strings to method names in a class-level dict, and calls
        getattr(self, name)(...) in a method, dispatches to each of those methods.  Each target gets a CALLS
        edge from the dispatching method with method "dispatch_table" (implemented, by table)."""
        g = self.g
        n = 0
        for c in self.class_by_id.values():
            tables: Dict[str, List[str]] = {}
            for st in c.node.body:
                tgt = None
                if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                    tgt, val = st.targets[0].id, st.value
                elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and st.value is not None:
                    tgt, val = st.target.id, st.value
                if tgt and isinstance(val, ast.Dict) and val.values and all(
                        isinstance(v, ast.Constant) and isinstance(v.value, str) for v in val.values):
                    names = [v.value for v in val.values]
                    hits = [x for x in names if self.find_method(c.cid, x)]
                    if len(hits) >= max(2, len(names) // 2):
                        tables[tgt] = hits
            if not tables:
                continue
            for mname, fid in c.methods.items():
                fn = self.func_by_id.get(fid) if hasattr(self, "func_by_id") else None
                node = fn.node if fn is not None else None
                if node is None:
                    continue
                uses_table = any(isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == "self"
                                 and x.attr in tables for x in ast.walk(node))
                getattr_self = [x for x in ast.walk(node) if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                                and x.func.id == "getattr" and x.args and isinstance(x.args[0], ast.Name)
                                and x.args[0].id == "self"]
                if not (uses_table and getattr_self):
                    continue
                line = getattr(getattr_self[0], "lineno", node.lineno)
                for tname in [t for t in tables if any(isinstance(x, ast.Attribute) and x.attr == t
                                                       for x in ast.walk(node))]:
                    for target in tables[tname]:
                        tid = self.find_method(c.cid, target)
                        if tid:
                            g.add_edge(fid, "CALLS", tid, evidence=(c.module.rel, line), provenance="ast",
                                       confidence=0.9, method=["dispatch_table"], table=tname)
                            n += 1
        self.log(f"pass 4c: {n} calls through method dispatch tables")

    def pass_bodies(self) -> None:
        for m in sorted(self.mods.values(), key=lambda x: x.rel):
            if m.tree is None:
                continue
            self._analyze_owner(m.nid, m, m.tree.body, None, None, {})
            for c in sorted(m.classes.values(), key=lambda x: x.cid):
                self._analyze_owner(c.cid, m, c.node.body, c, None, {})
            for f in m.funcs:
                self._analyze_owner(f.fid, m, f.node.body, f.ctx_cls, f, self._param_types(m, f))
            self._citations(m)
        self._resolve_organ_receivers()
        self.log(f"pass 4: bodies analysed; {sum(self.unresolved_calls.values())} method calls left unresolved, "
                 f"{len(self.unresolved_sites)} sites recorded with a reason")

    def _resolve_organ_receivers(self) -> None:
        """systems["k"].method(): when the organ k has exactly one implementing class, the call goes to
        that class's method (confidence 0.7).  Resolved sites leave the unresolved list."""
        impl: Dict[str, List[str]] = defaultdict(list)
        for (src, et, dst) in self.g.edges:
            if et == "IMPLEMENTED_BY":
                impl[src.split(":", 1)[1]].append(dst)
        kept = []
        for site in self.unresolved_sites:
            owner, path, line, expr, reason, extra = site
            if reason == "organ_receiver" and extra and len(impl.get(extra, [])) == 1:
                meth = expr.rsplit(".", 1)[-1]
                t = self.find_method(impl[extra][0], meth)
                if t:
                    self.g.add_edge(owner, "CALLS", t, evidence=(path, line), confidence=0.7, via_organ=extra)
                    self.unresolved_calls[owner] -= 1
                    self.stats["organ_calls_resolved"] += 1
                    continue
                site = (owner, path, line, expr, "unknown_member", extra)
            kept.append(site)
        self.unresolved_sites = kept
        for owner, cnt in list(self.unresolved_calls.items()):
            if owner in self.g.nodes and self.g.nodes[owner]["type"] in ("Function", "Module"):
                self.g.nodes[owner]["unresolved_calls"] = max(cnt, 0)

    def _param_types(self, m: ModuleInfo, f: FuncInfo) -> Dict[str, str]:
        out: Dict[str, str] = {}
        args = f.node.args
        for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            t = self.annotation_class(m, a.annotation)
            if t:
                out[a.arg] = t
        return out

    def _scopes(self, f: Optional[FuncInfo]) -> List[Dict[str, str]]:
        out = []
        while f is not None:
            out.append(f.nested)
            f = f.parent
        return out

    def resolve_call(self, m: ModuleInfo, func: ast.AST, ctx_cls: Optional[ClassInfo],
                     scopes: List[Dict[str, str]], local: Dict[str, str]) -> Tuple[Optional[str], float]:
        if isinstance(func, ast.Name):
            for sc in scopes:
                if func.id in sc:
                    return sc[func.id], 1.0
            if func.id in local:
                return None, 0.0
            return self.resolve_name(m, func.id), 1.0
        if not isinstance(func, ast.Attribute):
            return None, 0.0
        if isinstance(func.value, ast.Call) and isinstance(func.value.func, ast.Name) and func.value.func.id == "super":
            if ctx_cls is not None:
                return self.find_method(ctx_cls.cid, func.attr, skip_self=True), 0.9
            return None, 0.0
        chain = dotted(func)
        if not chain:
            return None, 0.0
        parts = chain.split(".")
        head = parts[0]
        if head in ("self", "cls") and ctx_cls is not None:
            rest = parts[1:]
            if len(rest) == 1:
                r = self.find_method(ctx_cls.cid, rest[0]) or ctx_cls.nested.get(rest[0])
                return r, 0.9
            typ = self.attr_type(ctx_cls.cid, rest[0])
            cur: Optional[str] = typ
            for p in rest[1:]:
                if cur is None:
                    break
                cur = self.member(cur, p)
            return cur, 0.8
        if head in local:
            cur = local[head]
            for p in parts[1:]:
                if cur is None:
                    break
                cur = self.member(cur, p)
            return cur, 0.8
        for sc in scopes:
            if head in sc:
                cur = sc[head]
                for p in parts[1:]:
                    if cur is None:
                        break
                    cur = self.member(cur, p)
                return cur, 1.0
        if head in m.global_types:
            cur = m.global_types[head]
            for p in parts[1:]:
                if cur is None:
                    break
                cur = self.member(cur, p)
            return cur, 0.8
        return self.resolve_chain(m, chain), 1.0

    BUILTIN_TYPE_NAMES = {"dict", "list", "set", "str", "int", "float", "tuple", "bytes", "frozenset", "bool",
                          "Dict", "List", "Set", "Tuple", "Optional", "Sequence", "Mapping", "Iterable", "Any",
                          "DefaultDict", "Deque", "Counter", "OrderedDict", "deque", "defaultdict"}

    def _is_builtin_value(self, v: ast.AST) -> bool:
        if isinstance(v, (ast.Constant, ast.JoinedStr, ast.List, ast.Dict, ast.Set, ast.Tuple, ast.ListComp,
                          ast.DictComp, ast.SetComp)):
            return True
        if isinstance(v, ast.Call):
            nm = dotted(v.func) or ""
            last = nm.split(".")[-1]
            if nm in BUILTINS or last in ("defaultdict", "deque", "Counter", "OrderedDict", "Lock", "RLock",
                                          "Event", "Path", "Queue"):
                return True
            if isinstance(v.func, ast.Attribute) and isinstance(v.func.value, (ast.Constant, ast.JoinedStr)):
                return True
        return False

    def _builtin_annotation(self, ann: Optional[ast.AST]) -> bool:
        if ann is None:
            return False
        if isinstance(ann, ast.Subscript):
            ann = ann.value
        nm = (dotted(ann) or "").split(".")[-1]
        return nm in self.BUILTIN_TYPE_NAMES

    def unresolved_reason(self, m: ModuleInfo, func: ast.Attribute, ctx_cls: Optional[ClassInfo],
                          local: Dict[str, str], organ_locals: Dict[str, str],
                          builtin_locals: Set[str] = frozenset()) -> Tuple[str, Optional[str]]:
        """Why a method call has no target: external, organ_receiver (with key), untyped_local,
        untyped_parameter, untyped_attribute, untyped_module_state, unknown_member, dynamic_receiver."""
        recv = func.value
        if isinstance(recv, (ast.Constant, ast.JoinedStr, ast.List, ast.Dict, ast.Set, ast.Tuple, ast.ListComp,
                             ast.DictComp, ast.SetComp, ast.BinOp)):
            return "builtin_value", None
        if isinstance(recv, ast.Name) and recv.id in builtin_locals:
            return "builtin_value", None
        if isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id in BUILTINS:
            return "builtin_value", None
        key = self._organ_key(recv)
        if key is None and isinstance(recv, ast.Name):
            key = organ_locals.get(recv.id)
        if key is not None:
            return "organ_receiver", key
        chain = dotted(recv)
        if chain is None:
            return "dynamic_receiver", None
        head = chain.split(".")[0]
        if head in ("self", "cls") and ctx_cls is not None:
            if chain in ("self", "cls"):
                return "unknown_member", None
            return "untyped_attribute", None
        alias = m.aliases.get(head)
        if alias and alias[0] == "ext":
            return "external", alias[1]
        if head in BUILTINS or head in STDLIB:
            return "external", head
        r = self.resolve_name(m, head)
        if r and r.startswith(("mod:", "cls:")):
            return "unknown_member", None
        if r and r.startswith("const:"):
            return "untyped_module_state", None
        if head in local:
            return "unknown_member", None
        if head in m.module_assigned:
            return "untyped_module_state", None
        return "untyped_local", None

    def _analyze_owner(self, owner: str, m: ModuleInfo, body: List[ast.stmt], ctx_cls: Optional[ClassInfo],
                       f: Optional[FuncInfo], local: Dict[str, str]) -> None:
        g = self.g
        scopes = self._scopes(f)
        local = dict(local)
        organ_locals: Dict[str, str] = {}
        builtin_locals: Set[str] = set()
        params: Set[str] = set()
        if f is not None:
            _a = f.node.args
            params = {x.arg for x in list(_a.posonlyargs) + list(_a.args) + list(_a.kwonlyargs)}
            for x in list(_a.posonlyargs) + list(_a.args) + list(_a.kwonlyargs):
                if self._builtin_annotation(x.annotation):
                    builtin_locals.add(x.arg)
            if _a.vararg:
                builtin_locals.add(_a.vararg.arg)
            if _a.kwarg:
                builtin_locals.add(_a.kwarg.arg)
        local_holders: Dict[str, Set[str]] = defaultdict(set)
        literals: Dict[str, int] = {}
        nc_dims: Dict[str, int] = {}
        unresolved = 0
        is_module_owner = owner.startswith("mod:")
        main_guard_ids: Set[int] = set()
        if is_module_owner:
            for s in body:
                if self._is_main_guard(s):
                    main_guard_ids.add(id(s))
        for stmt in iter_stmts(body):
            # bare string statements are docstrings or commentary, not code
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue
            exprs = own_exprs(stmt)
            # local types and local path holders, in source order
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                tgts = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                value = stmt.value
                for t in tgts:
                    if isinstance(t, ast.Name) and value is not None:
                        okey = self._organ_key(value)
                        if okey is not None:
                            organ_locals[t.id] = okey
                        if self._is_builtin_value(value) or (isinstance(stmt, ast.AnnAssign) and
                                                             self._builtin_annotation(stmt.annotation)):
                            builtin_locals.add(t.id)
                        else:
                            builtin_locals.discard(t.id)
                        typ = self.call_class(m, value, local)
                        if typ is None and isinstance(stmt, ast.AnnAssign):
                            typ = self.annotation_class(m, stmt.annotation)
                        if typ:
                            local[t.id] = typ
                        for s, _ in self.store_literals(value):
                            local_holders[t.id].add(self.store_node(s))
                        for ref in self._holder_refs(value, m, ctx_cls, local_holders):
                            local_holders[t.id].add(ref)
            hint_write = hint_read = False
            store_hits: List[Tuple[str, int]] = []
            for expr in exprs:
                for n in walk_expr(expr):
                    if isinstance(n, ast.Name):
                        if isinstance(n.ctx, ast.Load):
                            self.mentioned_names[n.id] += 1
                    elif isinstance(n, ast.Attribute):
                        self.mentioned_names[n.attr] += 1
                        chain = dotted(n)
                        if chain and chain.startswith("NonCompDimension."):
                            nc_dims.setdefault(chain.split(".")[1], n.lineno)
                    elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                        v = n.value
                        if len(v) <= 120:
                            literals.setdefault(v, getattr(n, "lineno", 0))
                            if re.match(r"^[A-Za-z_][\w.]*$", v):
                                self.mentioned_strings.add(v)
                    if isinstance(n, ast.Call):
                        cname = call_name(n)
                        if cname in WRITE_HINTS:
                            hint_write = True
                        elif cname in READ_HINTS:
                            hint_read = True
                        if cname == "open":
                            mode = None
                            if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                                mode = n.args[1].value
                            for kw in n.keywords:
                                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                                    mode = kw.value.value
                            if isinstance(mode, str) and any(ch in mode for ch in "wax+"):
                                hint_write = True
                            else:
                                hint_read = True
                        target, conf = self.resolve_call(m, n.func, ctx_cls, scopes, local)
                        ev = (m.rel, n.lineno)
                        if target and target.startswith("fn:"):
                            g.add_edge(owner, "CALLS", target, evidence=ev, confidence=conf)
                        elif target and target.startswith("cls:"):
                            g.add_edge(owner, "INSTANTIATES", target, evidence=ev, confidence=conf)
                        elif target is None and isinstance(n.func, ast.Attribute):
                            reason, extra = self.unresolved_reason(m, n.func, ctx_cls, local, organ_locals,
                                                                   builtin_locals)
                            if reason == "untyped_local" and f is not None and isinstance(n.func.value, ast.Name) \
                                    and n.func.value.id in params:
                                reason = "untyped_parameter"
                            if reason not in ("external", "builtin_value"):
                                unresolved += 1
                            self.unresolved_sites.append((owner, m.rel, n.lineno,
                                                          (dotted(n.func) or ("<expr>." + n.func.attr))[:120],
                                                          reason, extra or ""))
                        self._env_call(owner, m, n)
                        self._systems_call(owner, m, n, local)
                    elif isinstance(n, ast.Subscript):
                        self._env_subscript(owner, m, n)
                        self._systems_subscript(owner, m, n)
                    elif isinstance(n, ast.Compare):
                        self._membership(owner, m, n)
                for s, line in self.store_literals(expr):
                    store_hits.append((self.store_node(s), line))
                for sid in self._holder_refs(expr, m, ctx_cls, local_holders):
                    store_hits.append((sid, getattr(expr, "lineno", stmt.lineno)))
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                self._organ_registration(owner, m, stmt, local)
            etype = "WRITES" if hint_write else ("READS" if hint_read else "REFERENCES")
            for sid, line in store_hits:
                g.add_edge(owner, etype, sid, evidence=(m.rel, line or stmt.lineno),
                           provenance="ast", confidence=1.0 if etype != "REFERENCES" else 0.7)
        if unresolved:
            self.unresolved_calls[owner] += unresolved
            if owner in g.nodes and g.nodes[owner]["type"] in ("Function", "Module"):
                g.nodes[owner]["unresolved_calls"] = unresolved
        self._concepts_from_literals(owner, m, literals, nc_dims)

    def _holder_refs(self, expr: ast.AST, m: ModuleInfo, ctx_cls: Optional[ClassInfo],
                     local_holders: Dict[str, Set[str]]) -> Set[str]:
        out: Set[str] = set()
        for n in walk_expr(expr):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id in local_holders:
                    out |= local_holders[n.id]
                elif n.id in m.holders:
                    out |= m.holders[n.id]
            elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                base = n.value.id
                if base in ("self", "cls") and ctx_cls is not None:
                    out |= self.class_holders(ctx_cls.cid, n.attr)
                else:
                    r = self.resolve_name(m, base)
                    if r and r.startswith("cls:"):
                        out |= self.class_holders(r, n.attr)
                    elif r and r.startswith("mod:"):
                        mm = self.mod_by_id.get(r)
                        if mm and n.attr in mm.holders:
                            out |= mm.holders[n.attr]
        return out

    # ================================================================ pass 4b: information flow
    # Intra-procedural def-use with field, signal, bus, organ, store and env channels.  A value's
    # "sources" are the channel nodes and functions it came from; when it lands in a sink the
    # builder adds source FEEDS sink, with the function where it happened in via and how in roles.
    # Function nodes stand for their return value (role return) or their parameters (role parameter),
    # so chains run across calls: field A -> fn:get_a (return) -> field B (assign in the caller).

    def _field_for_self(self, ctx_cls: ClassInfo, attr: str) -> Optional[str]:
        """The field node for self.attr: the class in the MRO that gives attr a value."""
        if attr in ctx_cls.methods or attr in ctx_cls.nested:
            return None
        for c in self.mro(ctx_cls.cid):
            info = self.class_by_id.get(c)
            if info and attr in info.assigned_attrs:
                return self._field_node(info.cid, info.module, attr, "instance")
        return None

    def _field_node(self, holder: str, m: ModuleInfo, name: str, kind: str) -> str:
        base = holder.split(":", 1)[1]
        fid = f"field:{base}.{name}"
        if fid not in self.g.nodes:
            self.g.add_node(fid, "Field", name=name, holder=holder, kind=kind, path=m.rel)
            self.g.add_edge(holder, "CONTAINS", fid, evidence=(m.rel, 0), provenance="structure")
        return fid

    def _module_field(self, m: ModuleInfo, name: str) -> Optional[str]:
        if name in m.state_names:
            return self._field_node(m.nid, m, name, "module_state")
        return None

    def _is_signal_receiver(self, expr: ast.AST, seeds: Set[str]) -> bool:
        chain = dotted(expr)
        if not chain:
            return False
        last = chain.split(".")[-1]
        return last in self.signal_receivers or (chain in seeds)

    def _organ_key(self, expr: ast.AST) -> Optional[str]:
        """systems["k"] / systems.get("k") -> organ or bus key."""
        if isinstance(expr, ast.Subscript) and self._is_systems(expr.value):
            k = expr.slice
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                return k.value
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute) and expr.func.attr == "get" \
                and self._is_systems(expr.func.value) and expr.args:
            k = expr.args[0]
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                return k.value
        return None

    def _slot_id(self, key: str) -> Optional[str]:
        if not re.match(r"^_?[A-Za-z][\w]*$", key):
            return None
        return ("bus:" if key.startswith("_") else "organ:") + key

    def pass_flow(self) -> None:
        self.signal_receivers = set(self.ont.get("signal_receivers", []))
        seeds_by_fn = {"fn:" + k: v for k, v in self.ont.get("signal_seed_functions", {}).items()}
        self.spawn_calls = dict(self.ont.get("spawn_calls", {}))
        self.spawn_receivers = {k: set(v) for k, v in self.ont.get("spawn_receivers", {}).items()}
        self.http_calls = set(self.ont.get("http_client_calls", []))
        for m in sorted(self.mods.values(), key=lambda x: x.rel):
            if m.tree is None:
                continue
            self._flow_owner(m.nid, m, m.tree.body, None, None, set())
            for f in m.funcs:
                seeds = {seeds_by_fn[f.fid]} if f.fid in seeds_by_fn else set()
                self._flow_owner(f.fid, m, f.node.body, f.ctx_cls, f, seeds)
            self._http_handlers(m)
        self.flow_stats["fields"] = sum(1 for n in self.g.nodes.values() if n["type"] == "Field")
        self.log(f"pass 4b: information flow; {self.flow_stats['feeds']} FEEDS, {self.flow_stats['fields']} fields, "
                 f"{self.flow_stats['signals']} signals, {self.flow_stats['spawns']} spawns")

    def _flow_owner(self, owner: str, m: ModuleInfo, body: List[ast.stmt], ctx_cls: Optional[ClassInfo],
                    f: Optional[FuncInfo], seeds: Set[str]) -> None:
        g = self.g
        scopes = self._scopes(f)
        types: Dict[str, str] = self._param_types(m, f) if f else {}
        local_names = self._local_names(f) if f else set()
        params: Set[str] = set()
        if f is not None:
            a = f.node.args
            params = {x.arg for x in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)} - {"self", "cls"}
            if a.vararg:
                params.add(a.vararg.arg)
            if a.kwarg:
                params.add(a.kwarg.arg)
        taint: Dict[str, Set[str]] = {p: {"@param"} for p in params}
        handles: Dict[str, Set[str]] = {}       # file handle name -> store ids
        organs_local: Dict[str, str] = {}       # local name -> organ/bus key
        signal_locals: Set[str] = set(seeds)
        for nm, src in list(taint.items()):
            if nm in self.signal_receivers:
                signal_locals.add(nm)

        def feed(src_set: Set[str], sink: str, role: str, line: int) -> None:
            for s in src_set:
                if s == "@param":
                    if f is None or f.fid == sink:
                        continue
                    s, r = f.fid, "parameter"
                else:
                    r = role
                if s == sink and r not in ("return",):
                    continue
                if s not in g.nodes or sink not in g.nodes:
                    continue
                g.add_edge(s, "FEEDS", sink, evidence=(m.rel, line), via=[owner], roles=[r], confidence=0.8)
                self.flow_stats["feeds"] += 1

        def read(nid: str, line: int) -> None:
            g.add_edge(owner, "READS", nid, evidence=(m.rel, line))

        def write(nid: str, line: int) -> None:
            g.add_edge(owner, "WRITES", nid, evidence=(m.rel, line))

        def signal(key: str) -> str:
            sid = "signal:" + key
            if sid not in g.nodes:
                g.add_node(sid, "Signal", name=key)
                self.flow_stats["signals"] += 1
            return sid

        def field_of(expr: ast.AST) -> Optional[str]:
            """The Field node an attribute or name expression denotes, if any."""
            if isinstance(expr, ast.Name):
                if expr.id in local_names and not (f and expr.id in self._globals_of(f)):
                    return None
                return self._module_field(m, expr.id)
            if isinstance(expr, ast.Attribute):
                base = expr.value
                if isinstance(base, ast.Name):
                    if base.id in ("self", "cls") and ctx_cls is not None:
                        return self._field_for_self(ctx_cls, expr.attr)
                    if base.id in types:
                        info = self.class_by_id.get(types[base.id])
                        return self._field_for_self(info, expr.attr) if info else None
                    if base.id not in local_names:
                        r = self.resolve_name(m, base.id)
                        if r and r.startswith("mod:"):
                            mm = self.mod_by_id.get(r)
                            if mm and expr.attr in mm.state_names:
                                return self._field_node(mm.nid, mm, expr.attr, "module_state")
                        elif r and r.startswith("cls:"):
                            info = self.class_by_id.get(r)
                            if info and expr.attr in info.assigned_attrs and expr.attr not in info.methods:
                                return self._field_node(info.cid, info.module, expr.attr, "class")
                        if base.id in m.global_types:
                            info = self.class_by_id.get(m.global_types[base.id])
                            return self._field_for_self(info, expr.attr) if info else None
                elif isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name) \
                        and base.value.id == "self" and ctx_cls is not None:
                    typ = self.attr_type(ctx_cls.cid, base.attr)
                    info = self.class_by_id.get(typ) if typ else None
                    return self._field_for_self(info, expr.attr) if info else None
            return None

        def store_ids(expr: ast.AST) -> Set[str]:
            out = {self.store_node(s) for s, _ in self.store_literals(expr)}
            out |= self._holder_refs(expr, m, ctx_cls, {})
            for n in walk_expr(expr):
                if isinstance(n, ast.Name) and n.id in handles:
                    out |= handles[n.id]
            return out

        memo: Dict[int, Set[str]] = {}

        def sources(expr: Optional[ast.AST]) -> Set[str]:
            if expr is None:
                return set()
            k = id(expr)
            if k in memo:
                return memo[k]
            memo[k] = set()
            out: Set[str] = set()
            line = getattr(expr, "lineno", 0)
            if isinstance(expr, ast.Name):
                if expr.id in taint:
                    out |= taint[expr.id]
                fid = field_of(expr)
                if fid and expr.id not in taint:
                    read(fid, line)
                    out.add(fid)
                if expr.id in organs_local:
                    sid = self._slot_id(organs_local[expr.id])
                    if sid and sid in g.nodes:
                        out.add(sid)
            elif isinstance(expr, ast.Attribute):
                fid = field_of(expr)
                if fid:
                    read(fid, line)
                    out.add(fid)
                else:
                    out |= sources(expr.value)
            elif isinstance(expr, ast.Subscript):
                key = self._organ_key(expr)
                if key is not None:
                    sid = self._slot_id(key)
                    if sid and sid in g.nodes:
                        out.add(sid)
                elif self._is_signal_receiver(expr.value, signal_locals) and isinstance(expr.slice, ast.Constant) \
                        and isinstance(expr.slice.value, str):
                    sid = signal(expr.slice.value)
                    read(sid, line)
                    out.add(sid)
                else:
                    out |= sources(expr.value) | sources(expr.slice)
            elif isinstance(expr, ast.Call):
                out |= call_sources(expr)
            elif isinstance(expr, ast.Await):
                out |= sources(expr.value)
            elif isinstance(expr, (ast.Lambda,)):
                pass
            elif isinstance(expr, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                for gen in expr.generators:
                    out |= sources(gen.iter)
                for part in ([expr.key, expr.value] if isinstance(expr, ast.DictComp) else [expr.elt]):
                    out |= sources(part)
            else:
                for child in ast.iter_child_nodes(expr):
                    if isinstance(child, ast.expr):
                        out |= sources(child)
            memo[k] = out
            return out

        def call_sources(n: ast.Call) -> Set[str]:
            line = n.lineno
            fn = n.func
            cname = call_name(n)
            key = self._organ_key(n)
            if key is not None:
                sid = self._slot_id(key)
                return {sid} if sid and sid in g.nodes else set()
            # signal receiver .get("k")
            if isinstance(fn, ast.Attribute) and fn.attr in ("get", "pop", "setdefault") and n.args \
                    and self._is_signal_receiver(fn.value, signal_locals) \
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                sid = signal(n.args[0].value)
                if fn.attr == "setdefault":
                    write(sid, line)
                    if len(n.args) > 1:
                        feed(sources(n.args[1]), sid, "assign", line)
                else:
                    read(sid, line)
                return {sid}
            arg_src: List[Tuple[ast.AST, Set[str]]] = []
            callbacks: List[ast.AST] = []
            for a in list(n.args) + [kw.value for kw in n.keywords]:
                a0 = a.value if isinstance(a, ast.Starred) else a
                arg_src.append((a0, sources(a0)))
                if isinstance(a0, (ast.Name, ast.Attribute)):
                    callbacks.append(a0)
            all_args: Set[str] = set()
            for _, s in arg_src:
                all_args |= s
            target, conf = self.resolve_call(m, fn, ctx_cls, scopes, types)
            recv_src = sources(fn.value) if isinstance(fn, ast.Attribute) else set()
            # spawns and callbacks
            self._spawn_and_callbacks(owner, m, n, cname, callbacks, ctx_cls, scopes, types, target)
            # stores
            if cname in WRITE_HINTS:
                sids = store_ids(n)
                if sids:
                    data = set(all_args) | (recv_src if cname in ("write", "write_text", "write_bytes", "writelines") else set())
                    for sid in sids:
                        if sid in g.nodes:
                            feed({x for x in data if x != sid}, sid, "store_write", line)
            if cname in READ_HINTS or cname == "open":
                sids = {s for s in store_ids(n) if s in g.nodes}
                if sids:
                    return sids
            # http client
            if cname in self.http_calls:
                ep = self._http_endpoint(n)
                if ep:
                    g.add_edge(owner, "INVOKES", ep, evidence=(m.rel, line), confidence=0.7)
                    feed(all_args, ep, "payload", line)
                    return {ep}
            if target and target.startswith("fn:"):
                for _, s in arg_src:
                    feed(s, target, "argument", line)
                if recv_src:
                    feed(recv_src, target, "receiver", line)
                return {target}
            if target and target.startswith("cls:"):
                init = self.find_method(target, "__init__")
                if init:
                    for _, s in arg_src:
                        feed(s, init, "argument", line)
                return set()
            # mutators on a channel
            if isinstance(fn, ast.Attribute) and fn.attr in MUTATORS:
                sink = sink_of(fn.value)
                if sink:
                    write(sink, line)
                    feed(all_args, sink, "assign", line)
                    if fn.attr in ("pop", "popitem", "popleft", "setdefault"):
                        read(sink, line)
                        return {sink}
                    return set()
            # unresolved or external: the value carries what went in
            return all_args | recv_src

        def sink_of(t: ast.AST) -> Optional[str]:
            """The channel a store target writes: a field, a signal key, a bus or organ slot."""
            if isinstance(t, (ast.Name, ast.Attribute)):
                fid = field_of(t)
                if fid:
                    return fid
                if isinstance(t, ast.Name) and t.id in organs_local:
                    return self._slot_id(organs_local[t.id])
                return None
            if isinstance(t, ast.Subscript):
                key = self._organ_key(t)
                if key is not None:
                    sid = self._slot_id(key)
                    if sid:
                        g.add_node(sid, "BusChannel" if key.startswith("_") else "Organ", name=key)
                    return sid
                if self._is_signal_receiver(t.value, signal_locals) and isinstance(t.slice, ast.Constant) \
                        and isinstance(t.slice.value, str):
                    return signal(t.slice.value)
                return sink_of(t.value)
            return None

        def assign(t: ast.AST, src: Set[str], line: int, value: Optional[ast.AST]) -> None:
            if isinstance(t, (ast.Tuple, ast.List)):
                for e in t.elts:
                    assign(e, src, line, None)
                return
            if isinstance(t, ast.Starred):
                assign(t.value, src, line, None)
                return
            if isinstance(t, ast.Name):
                if value is not None:
                    key = self._organ_key(value)
                    if key is not None:
                        organs_local[t.id] = key
                    if self._is_signal_receiver(value, signal_locals) or (
                            isinstance(value, ast.Call) and dotted(value.func) in self.ont.get("signal_seed_functions", {})):
                        signal_locals.add(t.id)
                    ctype = self.call_class(m, value, types)
                    if ctype:
                        types[t.id] = ctype
                fid = field_of(t)
                if fid and (t.id not in local_names or (f and t.id in self._globals_of(f))):
                    write(fid, line)
                    feed(src, fid, "assign", line)
                else:
                    taint[t.id] = set(src)
                return
            sink = sink_of(t)
            if sink:
                if sink.startswith("organ:") or sink.startswith("bus:"):
                    pass  # REGISTERS / WRITES already added by pass_bodies
                else:
                    write(sink, line)
                feed(src, sink, "assign", line)
                if isinstance(t, ast.Attribute) and value is not None and ctx_cls is not None \
                        and isinstance(t.value, ast.Name) and t.value.id == "self":
                    pass

        for stmt in iter_stmts(body):
            line = stmt.lineno
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                continue
            if isinstance(stmt, ast.Assign):
                src = sources(stmt.value)
                for t in stmt.targets:
                    assign(t, src, line, stmt.value)
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                assign(stmt.target, sources(stmt.value), line, stmt.value)
            elif isinstance(stmt, ast.AugAssign):
                src = sources(stmt.value) | sources(stmt.target) if not isinstance(stmt.target, ast.Name) \
                    else sources(stmt.value) | taint.get(stmt.target.id, set())
                assign(stmt.target, src, line, None)
            elif isinstance(stmt, (ast.For, ast.AsyncFor)):
                assign(stmt.target, sources(stmt.iter), line, None)
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                for it in stmt.items:
                    src = sources(it.context_expr)
                    if it.optional_vars is not None:
                        if isinstance(it.optional_vars, ast.Name):
                            sids = {s for s in store_ids(it.context_expr) if s in g.nodes}
                            if sids:
                                handles[it.optional_vars.id] = sids
                        assign(it.optional_vars, src, line, None)
            elif isinstance(stmt, ast.Return) and stmt.value is not None and f is not None:
                feed(sources(stmt.value), f.fid, "return", line)
            elif isinstance(stmt, ast.Delete):
                for t in stmt.targets:
                    sink = sink_of(t)
                    if sink and not sink.startswith(("organ:", "bus:")):
                        write(sink, line)
            else:
                for e in own_exprs(stmt):
                    sources(e)

    def _globals_of(self, f: FuncInfo) -> Set[str]:
        cached = getattr(f, "_globals", None)
        if cached is None:
            cached = set()
            for stmt in iter_stmts(f.node.body):
                if isinstance(stmt, ast.Global):
                    cached.update(stmt.names)
            f._globals = cached  # type: ignore[attr-defined]
        return cached

    def _spawn_and_callbacks(self, owner: str, m: ModuleInfo, n: ast.Call, cname: str, callbacks: List[ast.AST],
                             ctx_cls: Optional[ClassInfo], scopes: List[Dict[str, str]], types: Dict[str, str],
                             target: Optional[str]) -> None:
        g = self.g
        line = n.lineno
        mech = self.spawn_calls.get(cname)
        if mech:
            recv_ok = self.spawn_receivers.get(cname)
            if recv_ok is not None:
                chain = dotted(n.func) or ""
                head = chain.split(".")[0] if "." in chain else ""
                if recv_ok and head not in recv_ok:
                    mech = None
                elif not recv_ok and not head:
                    mech = None
        refs: List[Tuple[ast.AST, str]] = []
        for kw in n.keywords:
            if kw.arg in ("target", "function", "callback", "fn", "func", "on_done", "handler"):
                refs.append((kw.value, kw.arg))
        for a in n.args:
            refs.append((a, "arg"))
        # asyncio.create_task(coro()) and friends take a coroutine call, not a reference
        if mech in ("task",) and n.args and isinstance(n.args[0], ast.Call):
            t, _ = self.resolve_call(m, n.args[0].func, ctx_cls, scopes, types)
            if t and t.startswith("fn:"):
                g.add_edge(owner, "SPAWNS", t, evidence=(m.rel, line), mechanisms=[mech], confidence=0.9)
                self.flow_stats["spawns"] += 1
            return
        for ref, how in refs:
            if not isinstance(ref, (ast.Name, ast.Attribute)):
                continue
            t, conf = self.resolve_call(m, ref, ctx_cls, scopes, types)
            if not t or not t.startswith(("fn:", "cls:")):
                continue
            if mech:
                g.add_edge(owner, "SPAWNS", t, evidence=(m.rel, line), mechanisms=[mech], confidence=min(conf, 0.9))
                self.flow_stats["spawns"] += 1
            elif t.startswith("fn:"):
                g.add_edge(owner, "PASSES_CALLBACK", t, evidence=(m.rel, line), to=[cname or "?"],
                           confidence=min(conf, 0.9))
                self.flow_stats["callbacks"] += 1

    def _http_endpoint(self, n: ast.Call) -> Optional[str]:
        """A literal URL path among the call's first arguments, e.g. _request("POST", "/act", ...)."""
        for a in list(n.args[:3]):
            path = None
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                path = a.value
            elif isinstance(a, ast.JoinedStr):
                path = joined_template(a)
            if path and re.match(r"^(https?://[^/\s]+)?/[\w\-/{}.<>]*$", path):
                path = re.sub(r"^https?://[^/]+", "", path) or "/"
                eid = "endpoint:http:" + path
                self.g.add_node(eid, "Endpoint", name=path, protocol="http")
                return eid
        return None

    def _http_handlers(self, m: ModuleInfo) -> None:
        """BaseHTTPRequestHandler subclasses: do_GET/do_POST handle the paths they compare against."""
        for c in m.classes.values():
            bases = set(c.external_bases) | {b.split(":")[-1].split(".")[-1] for b in c.base_ids}
            if not any("RequestHandler" in b for b in bases):
                continue
            for meth, fid in c.methods.items():
                if not meth.startswith("do_"):
                    continue
                fi = self.func_by_id.get(fid)
                if fi is None:
                    continue
                for n in ast.walk(fi.node):
                    if isinstance(n, ast.Compare):
                        for side in [n.left] + list(n.comparators):
                            if isinstance(side, ast.Constant) and isinstance(side.value, str) \
                                    and re.match(r"^/[\w\-/{}.]*$", side.value):
                                eid = "endpoint:http:" + side.value
                                self.g.add_node(eid, "Endpoint", name=side.value, protocol="http")
                                self.g.add_edge(fid, "HANDLES", eid, evidence=(m.rel, n.lineno), confidence=0.8)
                                self.g.add_edge(eid, "ROUTES_TO", fid, evidence=(m.rel, n.lineno), confidence=0.8)

    # -------------------------------------------------- env vars and systems
    def _env_node(self, name: str) -> str:
        return self.g.add_node("env:" + name, "EnvVar", name=name)

    def _env_call(self, owner: str, m: ModuleInfo, n: ast.Call) -> None:
        chain = dotted(n.func) or ""
        if not n.args or not isinstance(n.args[0], ast.Constant) or not isinstance(n.args[0].value, str):
            return
        key = n.args[0].value
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            return
        tail = chain.split(".")
        if chain in ("os.getenv", "getenv") or (len(tail) >= 2 and tail[-2] == "environ" and tail[-1] == "get"):
            self.g.add_edge(owner, "READS", self._env_node(key), evidence=(m.rel, n.lineno))
        elif len(tail) >= 2 and tail[-2] == "environ" and tail[-1] in ("setdefault", "pop"):
            self.g.add_edge(owner, "WRITES", self._env_node(key), evidence=(m.rel, n.lineno))

    def _env_subscript(self, owner: str, m: ModuleInfo, n: ast.Subscript) -> None:
        chain = dotted(n.value) or ""
        if chain.split(".")[-1] != "environ":
            return
        key = n.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            etype = "READS" if isinstance(n.ctx, ast.Load) else "WRITES"
            self.g.add_edge(owner, etype, self._env_node(key.value), evidence=(m.rel, n.lineno))

    def _membership(self, owner: str, m: ModuleInfo, n: ast.Compare) -> None:
        if not (isinstance(n.left, ast.Constant) and isinstance(n.left.value, str)):
            return
        if not any(isinstance(op, (ast.In, ast.NotIn)) for op in n.ops):
            return
        key = n.left.value
        for comp in n.comparators:
            chain = dotted(comp) or ""
            if chain.split(".")[-1] == "environ" and re.match(r"^[A-Za-z_]\w*$", key):
                self.g.add_edge(owner, "READS", self._env_node(key), evidence=(m.rel, n.lineno))
            elif self._is_systems(comp):
                self._slot(owner, m, key, "read", n.lineno)

    def _slot(self, owner: str, m: ModuleInfo, key: str, mode: str, line: int) -> Optional[str]:
        if not re.match(r"^_?[A-Za-z][\w]*$", key):
            return None
        ev = (m.rel, line)
        if key.startswith("_"):
            bid = self.g.add_node("bus:" + key, "BusChannel", name=key)
            self.g.add_edge(owner, "WRITES" if mode == "write" else "READS", bid, evidence=ev)
            return bid
        oid = self.g.add_node("organ:" + key, "Organ", name=key)
        self.g.add_edge(owner, "REGISTERS" if mode == "write" else "USES_ORGAN", oid, evidence=ev)
        return oid

    def _systems_subscript(self, owner: str, m: ModuleInfo, n: ast.Subscript) -> None:
        if not self._is_systems(n.value):
            return
        key = n.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            mode = "read" if isinstance(n.ctx, ast.Load) else "write"
            self._slot(owner, m, key.value, mode, n.lineno)

    def _systems_call(self, owner: str, m: ModuleInfo, n: ast.Call, local: Dict[str, str]) -> None:
        f = n.func
        if not isinstance(f, ast.Attribute) or not self._is_systems(f.value):
            return
        if f.attr in SYSTEMS_READ_METHODS | SYSTEMS_WRITE_METHODS and n.args:
            k = n.args[0]
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                mode = "write" if f.attr in SYSTEMS_WRITE_METHODS else "read"
                sid = self._slot(owner, m, k.value, mode, n.lineno)
                if mode == "write" and sid and sid.startswith("organ:") and len(n.args) > 1:
                    self._implemented_by(sid, m, n.args[1], local)
        elif f.attr == "update":
            for a in n.args:
                if isinstance(a, ast.Dict):
                    self._register_dict(owner, m, a, local)
            for kw in n.keywords:
                if kw.arg:
                    sid = self._slot(owner, m, kw.arg, "write", n.lineno)
                    if sid and sid.startswith("organ:"):
                        self._implemented_by(sid, m, kw.value, local)

    def _register_dict(self, owner: str, m: ModuleInfo, d: ast.Dict, local: Dict[str, str]) -> None:
        for k, v in zip(d.keys, d.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                sid = self._slot(owner, m, k.value, "write", k.lineno)
                if sid and sid.startswith("organ:"):
                    self._implemented_by(sid, m, v, local)

    def _implemented_by(self, organ: str, m: ModuleInfo, value: ast.AST, local: Dict[str, str]) -> None:
        cls = self.call_class(m, value, local)
        if cls:
            self.g.add_edge(organ, "IMPLEMENTED_BY", cls, evidence=(m.rel, value.lineno), confidence=0.9)

    def _organ_registration(self, owner: str, m: ModuleInfo, stmt: ast.stmt, local: Dict[str, str]) -> None:
        tgts = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        value = stmt.value
        if value is None:
            return
        for t in tgts:
            if isinstance(t, ast.Subscript) and self._is_systems(t.value):
                k = t.slice
                if isinstance(k, ast.Constant) and isinstance(k.value, str) and not k.value.startswith("_"):
                    if re.match(r"^[A-Za-z][\w]*$", k.value):
                        self._implemented_by("organ:" + k.value, m, value, local)
            elif isinstance(t, ast.Name) and t.id in self.receivers and isinstance(value, ast.Dict):
                self._register_dict(owner, m, value, local)

    # ---------------------------------------------------- concept literals
    def _concepts_from_literals(self, owner: str, m: ModuleInfo, literals: Dict[str, int],
                                nc_dims: Dict[str, int]) -> None:
        g = self.g
        axes_present = [s for s in self.axis_symbols if s in literals]
        if len(axes_present) >= int(self.ont.get("axis_literal_min_distinct", 4)):
            for s in axes_present:
                g.add_edge(owner, "EXPRESSES", "axis:" + s, evidence=(m.rel, literals[s]), confidence=0.8)
        for pair in self.ont["istate_pairs"]:
            pos, neg = pair.split("/")
            hit = None
            if pos in literals and neg in literals:
                hit = literals[pos]
            else:
                for lit, line in literals.items():
                    if re.sub(r"\s+", "", lit) == pair:
                        hit = line
                        break
            if hit is not None:
                g.add_edge(owner, "EXPRESSES", "istate:" + pair, evidence=(m.rel, hit), confidence=0.9)
        for lit, line in literals.items():
            for mt in self.nc_re.finditer(lit):
                g.add_edge(owner, "EXPRESSES", f"nc:{mt.group(1)}_{mt.group(2)}", evidence=(m.rel, line),
                           confidence=0.9)
        for dim, line in nc_dims.items():
            if dim in self.ont["noncomp_dimensions"]:
                g.add_edge(owner, "EXPRESSES", "ncdim:" + dim, evidence=(m.rel, line))
        for seq in self.ont["sequences"]:
            present = [s for s in seq["stages"] if s in literals]
            if len(present) >= int(seq.get("min_distinct", 3)):
                for s in present:
                    g.add_edge(owner, "EXPRESSES", f"concept:{seq['id']}/{s}", evidence=(m.rel, literals[s]),
                               confidence=0.8)

    # ------------------------------------------------------------ citations
    def _citations(self, m: ModuleInfo) -> None:
        spans = sorted(m.spans, key=lambda s: (s[0], -s[1]))
        for lineno, text in enumerate(m.source.splitlines(), 1):
            if "FIX-" not in text:
                continue
            for rule in _FIX_RE.findall(text):
                owner = m.nid
                best = None
                for start, end, nid in spans:
                    if start <= lineno <= end and (best is None or (end - start) < best):
                        best = end - start
                        owner = nid
                rid = self.g.add_node("rule:" + rule, "DoctrineRule", rule_id=rule)
                self.g.add_edge(owner, "CITES", rid, evidence=(m.rel, lineno), provenance="regex")

    # ================================================================ PASS 5
    def pass_ontology(self) -> None:
        g, ont = self.g, self.ont
        for a in ont["constraint_axes"]:
            g.add_node("axis:" + a["symbol"], "ConstraintAxis", name=a["name"], symbol=a["symbol"],
                       adjective=a["adjective"], poles=a["poles"], istate=a["istate"])
            g.add_node("istate:" + a["istate"], "IStatePair", name=a["istate"])
            g.add_edge("istate:" + a["istate"], "MAPS_TO", "axis:" + a["symbol"], provenance="ontology")
        for pair in ont["istate_pairs"]:
            g.add_node("istate:" + pair, "IStatePair", name=pair, order=ont["istate_pairs"].index(pair))
        for i, d in enumerate(ont["noncomp_dimensions"]):
            g.add_node("ncdim:" + d, "NonCompDimension", name=d, index=i)
        count = 0
        for ai, a in enumerate(ont["constraint_axes"]):
            for di, d in enumerate(ont["noncomp_dimensions"]):
                nid = f"nc:{a['adjective']}_{d.title()}"
                g.add_node(nid, "NonComp", name=f"{a['adjective']} {d.title()}", axis=a["symbol"],
                           dimension=d, index=ai * len(ont["noncomp_dimensions"]) + di)
                g.add_edge(nid, "COMPOSED_OF", "axis:" + a["symbol"], provenance="ontology")
                g.add_edge(nid, "COMPOSED_OF", "ncdim:" + d, provenance="ontology")
                count += 1
        if count != int(ont.get("noncomp_channels", 25)):
            self.warnings.append(f"ontology yields {count} Non-Comps, expected {ont.get('noncomp_channels')}")
        prev = None
        for layer in ont["layers"]:
            lid = "layer:" + layer["id"]
            g.add_node(lid, "Layer", name=layer["name"], layer_id=layer["id"])
            if prev and layer["id"].startswith("L"):
                g.add_edge(prev, "PRECEDES", lid, provenance="ontology")
            if layer["id"].startswith("L"):
                prev = lid
            for mod_file in layer.get("modules", []):
                for mid in self._modules_for_file(mod_file):
                    g.add_edge(mid, "OWNED_BY", lid, provenance="ontology")
        for seq in ont["sequences"]:
            sid = "concept:" + seq["id"]
            g.add_node(sid, "Concept", name=seq["name"], kind="sequence", stages=seq["stages"])
            prev_stage = None
            for i, s in enumerate(seq["stages"]):
                st = f"concept:{seq['id']}/{s}"
                g.add_node(st, "Concept", name=s, kind="stage", order=i)
                g.add_edge(st, "PART_OF", sid, provenance="ontology")
                if prev_stage:
                    g.add_edge(prev_stage, "PRECEDES", st, provenance="ontology")
                prev_stage = st
        for sub in ont["subsystems"]:
            g.add_node("concept:" + sub["id"], "Concept", name=sub["name"], kind="subsystem")
        self._name_concepts()
        self._manifold_directory()
        self.log("pass 5a: ontology, layers, manifold directory")

    def _modules_for_file(self, token: str) -> List[str]:
        token = token.strip().lstrip("./")
        if token in self.mod_by_rel:
            return [self.mod_by_rel[token].nid]
        base = token.rsplit("/", 1)[-1]
        cands = self.mods_by_basename.get(base, [])
        if len(cands) == 1:
            return [cands[0].nid]
        roots = [c for c in cands if "/" not in c.rel]
        return [roots[0].nid] if len(roots) == 1 else []

    @staticmethod
    def _snake(name: str) -> str:
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
        s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
        return s.lower()

    def _name_concepts(self) -> None:
        compiled = [(sub["id"], [re.compile(p) for p in sub["patterns"]]) for sub in self.ont["subsystems"]]
        axis_tokens = {t: a["symbol"] for a in self.ont["constraint_axes"] for t in a["name_tokens"]}
        for nid, node in list(self.g.nodes.items()):
            if node["type"] not in ("Module", "Class"):
                continue
            raw = node["name"].split(".")[-1]
            snake = self._snake(raw)
            for cid, pats in compiled:
                if any(p.search(snake) for p in pats):
                    self.g.add_edge(nid, "EXPRESSES", "concept:" + cid, provenance="name", confidence=0.6)
            tokens = set(snake.split("_"))
            for tok, sym in axis_tokens.items():
                if tok in tokens:
                    self.g.add_edge(nid, "EXPRESSES", "axis:" + sym, provenance="name", confidence=0.6)

    def _manifold_directory(self) -> None:
        base = self.root / self.ont.get("manifold_directory", "aurora_manifold_directory")
        if not base.is_dir():
            return
        adjectives = {a["adjective"] for a in self.ont["constraint_axes"]}
        dims = {d.title() for d in self.ont["noncomp_dimensions"]}
        for axis in self.axis_symbols:
            d = base / axis
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.json")):
                mt = re.match(r"^(\w+?)_(\w+?)_of_(\w+)$", p.stem)
                if not mt or mt.group(1) not in adjectives or mt.group(2) not in dims:
                    continue
                mid = f"manifold:{axis}/{p.stem}"
                self.g.add_node(mid, "ManifoldEntry", name=p.stem, path=self.rel(p), base_axis=axis)
                self.g.add_edge(mid, "COMPOSED_OF", f"nc:{mt.group(1)}_{mt.group(2)}", provenance="filesystem")
                self.g.add_edge(mid, "COMPOSED_OF", "axis:" + axis, provenance="filesystem")

    # ------------------------------------------------------- doc resolution
    def resolve_doc_token(self, token: str) -> List[str]:
        raw = token.strip()
        sysm = re.search(r"""systems\[\s*["'](\w+)["']\s*\]""", raw)
        if sysm:
            key = sysm.group(1)
            nid = ("bus:" if key.startswith("_") else "organ:") + key
            return [nid] if nid in self.g.nodes else []
        t = raw.strip("()[]{}.,;'\" ")
        t = re.sub(r"\(.*\)$", "", t)
        t = re.sub(r":\d+(?:-\d+)?$", "", t)
        if ":" in t and t.split(":", 1)[0].endswith(".py"):
            path, chain = t.split(":", 1)
            mods = self._modules_for_file(path)
            if mods and _IDENT_CHAIN.match(chain):
                mm = self.mod_by_id[mods[0]]
                hit = self.suffix_index.get(f"{mm.name}.{chain}")
                return sorted(hit) if hit and len(hit) == 1 else mods
            return mods
        if t.endswith(".py"):
            return self._modules_for_file(t)
        s = normalize_store(t)
        if s and ("store:" + s) in self.g.nodes:
            return ["store:" + s]
        if t.startswith("_") and ("bus:" + t) in self.g.nodes:
            return ["bus:" + t]
        if len(t) >= 4 and _IDENT_CHAIN.match(t):
            hit = self.suffix_index.get(t)
            if hit and len(hit) == 1:
                return sorted(hit)
        return []

    def _doc_tokens(self, text: str) -> List[str]:
        toks = _BACKTICK.findall(text)
        toks.extend(_PYFILE.findall(text))
        return toks

    def pass_documents(self, md_files: List[Path]) -> None:
        g = self.g
        registry_globs = self.ont.get("registry_files", [])
        inventory = self.ont.get("persistence_inventory", "")
        layer_doc = self.ont.get("layer_ownership_doc", "")
        allowed_doc_targets = set(EDGE_TYPES["DOCUMENTS"]["target"])
        for p in md_files:
            rel = self.rel(p)
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), p.stem)
            did = g.add_node("doc:" + rel, "Document", name=p.name, path=rel, title=title[:160], loc=len(lines))
            g.add_edge("repo:aurora", "CONTAINS", did, provenance="filesystem")
            for i, line in enumerate(lines, 1):
                for tok in self._doc_tokens(line):
                    for target in self.resolve_doc_token(tok):
                        if g.nodes[target]["type"] in allowed_doc_targets:
                            g.add_edge(did, "DOCUMENTS", target, evidence=(rel, i), provenance="doc", confidence=0.9)
                            if rel == inventory:
                                if target.startswith("store:"):
                                    g.nodes[target]["declared_in_inventory"] = True
                                elif target.startswith("cls:"):
                                    g.nodes[target]["inventory_listed"] = True
            if any(fnmatch.fnmatch(rel, pat) for pat in registry_globs):
                self._registry(rel, lines)
            if rel == layer_doc:
                self._layer_doc(rel, lines)
        self.log("pass 5b: documents, registry, layer ownership")

    def _registry(self, rel: str, lines: List[str]) -> None:
        g = self.g
        entries: List[Tuple[str, int, str, List[str]]] = []
        cur: Optional[List[Any]] = None
        for i, line in enumerate(lines, 1):
            mt = _REGISTRY_HEADING.match(line)
            if mt:
                if cur:
                    entries.append(tuple(cur))  # type: ignore[arg-type]
                cur = [mt.group(2), i, mt.group(3).strip(), []]
                continue
            if cur is not None and re.match(r"^#{1,2}\s", line):
                entries.append(tuple(cur))  # type: ignore[arg-type]
                cur = None
                continue
            if cur is not None:
                cur[3].append((i, line))
        if cur:
            entries.append(tuple(cur))  # type: ignore[arg-type]
        for rule, line, rest, body in entries:
            rid = "rule:" + rule
            cat = re.match(r"^\(([^)]+)\)", rest)
            title = re.sub(r"^\([^)]*\)\s*[—–\-:]*\s*", "", rest).strip(" —-:")
            node = g.nodes.get(rid)
            if node and node.get("defined"):
                node.setdefault("also_defined_in", [])
                if rel not in node["also_defined_in"]:
                    node["also_defined_in"].append(rel)
                continue
            g.add_node(rid, "DoctrineRule", rule_id=rule)
            g.nodes[rid].update({"title": title[:200], "category": cat.group(1).strip() if cat else "",
                                 "source": rel, "line": line, "defined": True})
            for ln, text in body:
                for tok in self._doc_tokens(text):
                    for target in self.resolve_doc_token(tok):
                        if g.nodes[target]["type"] in EDGE_TYPES["GOVERNS"]["target"]:
                            g.add_edge(rid, "GOVERNS", target, evidence=(rel, ln), provenance="doc", confidence=0.9)

    def _layer_doc(self, rel: str, lines: List[str]) -> None:
        current = None
        for i, line in enumerate(lines, 1):
            mt = re.match(r"^#{2,3}\s+(L\d|Orchestrator)\b", line)
            if mt:
                current = "layer:" + ("ORCH" if mt.group(1) == "Orchestrator" else mt.group(1))
                continue
            if current and re.match(r"^#{1,3}\s", line):
                current = None
                continue
            if current and line.lstrip().startswith(("-", "|")):
                for tok in _BACKTICK.findall(line):
                    if not tok.endswith(".py"):
                        continue
                    mods = self._modules_for_file(tok)
                    if mods:
                        for mid in mods:
                            self.g.add_edge(mid, "OWNED_BY", current, evidence=(rel, i), provenance="doc")
                    else:
                        node = self.g.nodes.get(current)
                        if node is not None:
                            node.setdefault("declared_missing", [])
                            if tok not in node["declared_missing"]:
                                node["declared_missing"].append(tok)

    # ------------------------------------------------------ other languages
    def pass_other_sources(self, files: List[Path]) -> None:
        g = self.g
        by_rel: Dict[str, str] = {}
        for p in files:
            rel = self.rel(p)
            lang = self._other_language(rel) or "unknown"
            text = p.read_text(encoding="utf-8", errors="replace")
            sid = g.add_node("src:" + rel, "SourceFile", name=p.name, path=rel, language=lang,
                             loc=text.count("\n") + 1,
                             has_authorship_header=bool(_AUTH_RE.search("\n".join(text.splitlines()[:40]))))
            g.add_edge("repo:aurora", "CONTAINS", sid, provenance="filesystem")
            by_rel[rel] = sid
        for p in files:
            rel = self.rel(p)
            lang = g.nodes["src:" + rel]["language"]
            text = p.read_text(encoding="utf-8", errors="replace")
            if lang == "rust":
                self._rust_edges(p, rel, text, by_rel)
            elif lang == "dart":
                self._dart_edges(p, rel, text, by_rel)
            if lang == "systemd":
                # ExecStart and friends name the script or interpreter the unit runs; the repo root is a placeholder
                for i, line in enumerate(text.splitlines(), 1):
                    mx = _SYSTEMD_EXEC.match(line)
                    if not mx:
                        continue
                    for tok in mx.group(2).split():
                        tok = re.sub(r"^[-@:+!]+", "", tok)
                        tok = re.sub(r"^(?:__AURORA_ROOT__|%h/[^/]+|\$\{?\w+\}?)/", "", tok).lstrip("./")
                        if ("src:" + tok) in g.nodes:
                            g.add_edge("src:" + rel, "RUNS", "src:" + tok, evidence=(rel, i), provenance="regex")
                        elif tok in self.mod_by_rel:
                            g.add_edge("src:" + rel, "RUNS", self.mod_by_rel[tok].nid, evidence=(rel, i),
                                       provenance="regex")
            if lang in ("shell", "batch", "powershell", "github-workflow", "systemd"):
                for i, line in enumerate(text.splitlines(), 1):
                    for mod_name, path in _PY_LAUNCH.findall(line):
                        targets: List[str] = []
                        if mod_name and mod_name in self.mods:
                            targets = [self.mods[mod_name].nid]
                        elif path:
                            path = path.replace("\\", "/").lstrip("./")
                            near = (p.parent / path)
                            try:
                                near_rel = near.resolve().relative_to(self.root).as_posix()
                            except ValueError:
                                near_rel = ""
                            if near_rel in self.mod_by_rel:
                                targets = [self.mod_by_rel[near_rel].nid]
                            else:
                                targets = self._modules_for_file(path)
                        for t in targets:
                            g.add_edge("src:" + rel, "RUNS", t, evidence=(rel, i), provenance="regex")
        self.log(f"pass 5c: {len(files)} non-Python source files")

    def _rust_edges(self, p: Path, rel: str, text: str, by_rel: Dict[str, str]) -> None:
        here = p.parent
        mod_dir = here if p.name in ("mod.rs", "lib.rs", "main.rs") else here / p.stem
        for name in _RUST_MOD.findall(text):
            for cand in (mod_dir / f"{name}.rs", mod_dir / name / "mod.rs"):
                r = cand.relative_to(self.root).as_posix() if cand.exists() else None
                if r and r in by_rel:
                    self.g.add_edge("src:" + rel, "IMPORTS", by_rel[r], provenance="regex")
                    break
        crate = next((d for d in [here] + list(here.parents) if (d / "Cargo.toml").exists()), None)
        if crate is None:
            return
        for path in _RUST_USE.findall(text):
            parts = [x for x in path.split("::") if x and x != "{"]
            for i in range(len(parts), 0, -1):
                stem = crate / "src" / "/".join(parts[:i])
                hit = None
                for cand in (stem.with_suffix(".rs"), stem / "mod.rs"):
                    if cand.exists():
                        hit = cand.relative_to(self.root).as_posix()
                        break
                if hit and hit in by_rel:
                    self.g.add_edge("src:" + rel, "IMPORTS", by_rel[hit], provenance="regex")
                    break

    def _dart_edges(self, p: Path, rel: str, text: str, by_rel: Dict[str, str]) -> None:
        for spec in _DART_IMPORT.findall(text):
            target = None
            if spec.startswith("package:"):
                pkg, _, sub = spec[len("package:"):].partition("/")
                for d in [p.parent] + list(p.parent.parents):
                    pub = d / "pubspec.yaml"
                    if pub.exists():
                        mt = re.search(r"^name:\s*(\S+)", pub.read_text(encoding="utf-8", errors="replace"), re.M)
                        if mt and mt.group(1) == pkg:
                            target = d / "lib" / sub
                        break
            elif not spec.startswith("dart:"):
                target = (p.parent / spec).resolve()
            if target is not None and target.exists():
                r = target.resolve().relative_to(self.root).as_posix()
                if r in by_rel:
                    self.g.add_edge("src:" + rel, "IMPORTS", by_rel[r], provenance="regex")

    # ================================================================ pass 5d: other languages
    # Rust, Dart, Kotlin and Java are read with patterns and brace matching, not a full parser, so
    # their edges carry provenance regex and calls inside them are matched by name (confidence 0.6-0.7).
    # The cross-language hand-offs are the point: MethodChannel, EventChannel, Chaquopy, frames, intents.

    _POLY_KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "when", "match", "loop", "else", "try",
                      "super", "this", "new", "throw", "assert", "await", "print", "println", "Some", "Ok", "Err",
                      "setState", "sizeof", "typeof", "fun", "fn", "class", "in", "is", "as"}

    @staticmethod
    def _mask_text(text: str, lang: str) -> str:
        """Blank out comments and string contents (keeping offsets) so brace matching is not fooled."""
        out = list(text)
        i, n = 0, len(text)
        while i < n:
            c = text[i]
            if text.startswith("//", i):
                j = text.find("\n", i)
                j = n if j < 0 else j
                for k in range(i, j):
                    out[k] = " "
                i = j
            elif text.startswith("/*", i):
                j = text.find("*/", i + 2)
                j = n if j < 0 else j + 2
                for k in range(i, j):
                    if out[k] != "\n":
                        out[k] = " "
                i = j
            elif c in "\"'" and not (lang == "rust" and c == "'" and i + 2 < n and text[i + 2] != "'"
                                     and text[i + 1] != "\\"):
                q3 = text[i:i + 3]
                if q3 in ('"""', "'''"):
                    j = text.find(q3, i + 3)
                    j = n if j < 0 else j + 3
                    lo, hi = i + 3, j - 3
                else:
                    j = i + 1
                    while j < n and text[j] != c and text[j] != "\n":
                        j += 2 if text[j] == "\\" else 1
                    j = min(j + 1, n)
                    lo, hi = i + 1, j - 1
                for k in range(lo, max(lo, hi)):
                    if out[k] not in "\n":
                        out[k] = "_"
                i = j
            else:
                i += 1
        return "".join(out)

    @staticmethod
    def _match_brace(masked: str, open_idx: int) -> int:
        depth = 0
        for k in range(open_idx, len(masked)):
            ch = masked[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return k
        return len(masked) - 1

    _POLY_CLASS = {
        "rust": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(struct|enum|trait|union)\s+(\w+)", re.M),
        "dart": re.compile(r"^\s*(?:abstract\s+|sealed\s+|base\s+|final\s+)*(class|mixin|enum|extension)\s+(\w+)", re.M),
        "kotlin": re.compile(r"^\s*(?:(?:private|public|internal|open|abstract|data|sealed|inner|enum|companion)\s+)*"
                             r"(class|object|interface)\s+(\w+)", re.M),
        "java": re.compile(r"^\s*(?:(?:public|private|protected|abstract|final|static)\s+)*(class|interface|enum)\s+(\w+)", re.M),
    }
    _RUST_IMPL = re.compile(r"^\s*impl(?:<[^>{]*>)?\s+(?:([\w:]+)(?:<[^>{]*>)?\s+for\s+)?([\w:]+)", re.M)
    _POLY_FN = {
        "rust": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:const\s+|async\s+|unsafe\s+|extern\s+\"C\"\s+)*fn\s+(\w+)", re.M),
        "kotlin": re.compile(r"^\s*(?:(?:private|public|internal|protected|override|open|suspend|inline|operator|abstract)\s+)*"
                             r"fun\s+(?:<[^>]*>\s*)?(?:[\w.]+\.)?(\w+)\s*\(", re.M),
        "dart": re.compile(r"^\s*(?:@\w+\s*)*(?:(?:static|final|external|factory|const|late|abstract|Future|void|"
                           r"[A-Z]\w*(?:<[^;{}()=]*>)?\??|int|double|bool|String|dynamic|num)\s+)*(?:get\s+|set\s+|factory\s+\w+\.|[A-Z]\w*\.)?"
                           r"([a-zA-Z_]\w*)\s*(?:<[^>]*>)?\s*\([^;]*?\)\s*(?:async\*?|sync\*)?\s*(?:\{|=>)", re.M | re.S),
        "java": re.compile(r"^\s*(?:(?:public|private|protected|static|final|synchronized|abstract|native)\s+)+"
                           r"[\w<>\[\],.? ]+\s+(\w+)\s*\([^;{]*\)\s*(?:throws\s+[\w., ]+)?\s*\{", re.M),
    }
    _CALL_TOKEN = re.compile(r"(?<![\w.])(?:([A-Za-z_]\w*)\.)?([A-Za-z_]\w*)\s*(?:<[^<>()]*>)?\s*\(")

    def _poly_id(self, rel: str) -> str:
        stem = rel.rsplit(".", 1)[0]
        return stem.replace("/", ".").replace("-", "_")

    def pass_polyglot(self, files: List[Path]) -> None:
        g = self.g
        langs = ("rust", "dart", "kotlin", "java")
        units: List[Dict[str, Any]] = []      # one per function: id, lang, rel, cls, body span, text
        self.poly_by_name: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        for p in files:
            rel = self.rel(p)
            lang = self._other_language(rel)
            if lang not in langs:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            masked = self._mask_text(text, lang)
            sid = "src:" + rel
            base = self._poly_id(rel)
            line_of = lambda idx, _t=text: _t.count("\n", 0, idx) + 1
            # classes and their spans
            spans: List[Tuple[int, int, str]] = []
            for mt in self._POLY_CLASS[lang].finditer(masked):
                kind, name = mt.group(1), mt.group(2)
                brace = masked.find("{", mt.end())
                semi = masked.find(";", mt.end())
                end = self._match_brace(masked, brace) if brace >= 0 and (semi < 0 or brace < semi or lang != "rust") else mt.end()
                cid = f"cls:{base}.{name}"
                g.add_node(cid, "Class", name=name, qualname=name, path=rel, line=line_of(mt.start()),
                           language=lang, kind=kind)
                g.add_edge(sid, "CONTAINS", cid, provenance="regex")
                spans.append((mt.start(), end, cid))
            if lang == "rust":
                for mt in self._RUST_IMPL.finditer(masked):
                    trait, typ = mt.group(1), mt.group(2).split("::")[-1]
                    brace = masked.find("{", mt.end())
                    if brace < 0:
                        continue
                    end = self._match_brace(masked, brace)
                    cid = f"cls:{base}.{typ}"
                    if cid not in g.nodes:
                        g.add_node(cid, "Class", name=typ, qualname=typ, path=rel, line=line_of(mt.start()),
                                   language=lang, kind="impl")
                        g.add_edge(sid, "CONTAINS", cid, provenance="regex")
                    if trait:
                        tname = trait.split("::")[-1]
                        tgt = next((c for c in self.poly_by_name.get(("cls", tname), [])), None)
                        if tgt:
                            g.add_edge(cid, "INHERITS", tgt, evidence=(rel, line_of(mt.start())), provenance="regex",
                                       confidence=0.7)
                    spans.append((mt.start(), end, cid))
            for _, _, cid in spans:
                self.poly_by_name[("cls", g.nodes[cid]["name"])].append(cid)
            # functions
            for mt in self._POLY_FN[lang].finditer(masked):
                name = mt.group(1)
                if name in self._POLY_KEYWORDS:
                    continue
                start = mt.start(1)
                owner_cls = None
                for a, bnd, cid in spans:
                    if a < start < bnd and (owner_cls is None or a > owner_cls[0]):
                        owner_cls = (a, cid)
                brace = masked.find("{", mt.end(1))
                arrow = masked.find("=>", mt.end(1))
                semi = masked.find(";", mt.end(1))
                if brace < 0 or (semi >= 0 and semi < brace and (arrow < 0 or arrow > semi)):
                    end = semi if semi >= 0 else mt.end()
                    if lang == "dart" and arrow >= 0 and (brace < 0 or arrow < brace):
                        end = semi if semi >= 0 else mt.end()
                    elif lang in ("rust", "java", "kotlin") and lang != "kotlin":
                        continue   # declaration only (trait or interface method)
                elif lang == "dart" and arrow >= 0 and arrow < brace:
                    end = semi if semi >= 0 else mt.end()
                else:
                    end = self._match_brace(masked, brace)
                parent = owner_cls[1] if owner_cls else sid
                qual = (g.nodes[parent]["name"] + "." + name) if owner_cls else name
                fid = f"fn:{base}.{qual}"
                if fid in g.nodes:
                    fid = f"{fid}@{line_of(start)}"
                g.add_node(fid, "Function", name=name, qualname=qual, path=rel, line=line_of(start),
                           end_line=line_of(end), language=lang, kind="method" if owner_cls else "function")
                g.add_edge(parent, "CONTAINS", fid, provenance="regex")
                self.poly_by_name[(lang, name)].append(fid)
                units.append({"id": fid, "lang": lang, "rel": rel, "cls": owner_cls[1] if owner_cls else None,
                              "lo": start, "hi": end, "text": text, "masked": masked, "line0": line_of(start)})
        # innermost function owns each offset
        by_file: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for u in units:
            by_file[u["rel"]].append(u)
        self._poly_units = by_file
        # name-matched calls
        for u in units:
            body = u["masked"][u["lo"]:u["hi"]]
            seen: Set[str] = set()
            for mt in self._CALL_TOKEN.finditer(body):
                recv, name = mt.group(1), mt.group(2)
                if name in self._POLY_KEYWORDS or name == g.nodes[u["id"]]["name"] and mt.start() < 40:
                    continue
                if self._innermost(u["rel"], u["lo"] + mt.start())["id"] != u["id"]:
                    continue
                cands = self.poly_by_name.get((u["lang"], name), [])
                if not cands:
                    continue
                same_cls = [c for c in cands if u["cls"] and c.startswith(u["cls"].replace("cls:", "fn:", 1) + ".")]
                same_file = [c for c in cands if g.nodes[c]["path"] == u["rel"]]
                if recv and recv[0].isupper():
                    typed = [c for c in cands if g.nodes[c]["qualname"].startswith(recv + ".")]
                    pick, conf = (typed, 0.7) if len(typed) == 1 else ([], 0)
                elif len(same_cls) == 1:
                    pick, conf = same_cls, 0.7
                elif len(same_file) == 1:
                    pick, conf = same_file, 0.7
                elif len(cands) == 1:
                    pick, conf = cands, 0.6
                else:
                    pick, conf = [], 0
                for t in pick:
                    if t in seen:
                        continue
                    seen.add(t)
                    line = u["text"].count("\n", 0, u["lo"] + mt.start()) + 1
                    g.add_edge(u["id"], "CALLS", t, evidence=(u["rel"], line), provenance="regex", confidence=conf)
        self._polyglot_endpoints(units)
        self.log(f"pass 5d: {len(units)} functions in Rust, Dart, Kotlin and Java; "
                 f"{sum(1 for n in g.nodes.values() if n['type'] == 'Endpoint')} endpoints")

    def _innermost(self, rel: str, idx: int) -> Optional[Dict[str, Any]]:
        best = None
        for u in self._poly_units.get(rel, []):
            if u["lo"] <= idx <= u["hi"] and (best is None or u["lo"] >= best["lo"]):
                best = u
        return best

    def _endpoint(self, protocol: str, name: str, **attrs: Any) -> str:
        eid = f"endpoint:{protocol}:{name}"
        self.g.add_node(eid, "Endpoint", name=name, protocol=protocol, **attrs)
        return eid

    def _owner_at(self, rel: str, text: str, idx: int) -> str:
        u = self._innermost(rel, idx)
        return u["id"] if u else "src:" + rel

    def _polyglot_endpoints(self, units: List[Dict[str, Any]]) -> None:
        g = self.g
        files: Dict[str, Tuple[str, str]] = {}
        for u in units:
            files[u["rel"]] = (u["text"], u["lang"])
        for p_rel in list(self.repo_files):
            lang = self._other_language(p_rel)
            if lang in ("kotlin", "dart", "java", "rust") and p_rel not in files and ("src:" + p_rel) in g.nodes:
                try:
                    files[p_rel] = ((self.root / p_rel).read_text(encoding="utf-8", errors="replace"), lang)
                except OSError:
                    pass
        line_of = lambda t, i: t.count("\n", 0, i) + 1
        consts: Dict[str, str] = {}
        for rel, (text, lang) in files.items():
            for mt in re.finditer(r"(?:const\s+val|val|static\s+const|const|static\s+final\s+String)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*\"([^\"]+)\"", text):
                consts[mt.group(1)] = mt.group(2)
        chaq_roots = self.ont.get("chaquopy_python_roots", [])

        def py_target(module: str, fn: str) -> Optional[str]:
            for root in chaq_roots:
                mm = self.mod_by_rel.get(f"{root}/{module.replace('.', '/')}.py")
                if mm:
                    t = mm.defs.get(fn)
                    return t if t and t.startswith("fn:") else None
            mm = self.mods.get(module)
            if mm:
                t = mm.defs.get(fn)
                return t if t and t.startswith("fn:") else None
            return None

        def chaquopy_ep(module: str, fn: str) -> str:
            eid = self._endpoint("chaquopy", f"{module}#{fn}")
            t = py_target(module, fn)
            if t:
                g.add_edge(eid, "ROUTES_TO", t, provenance="regex", confidence=0.9)
            return eid

        # Kotlin dispatchers: functions whose String parameter is passed straight to callAttr
        dispatchers: Dict[str, Tuple[str, str]] = {}   # fun name -> (module, param)
        for rel, (text, lang) in files.items():
            if lang != "kotlin":
                continue
            for mt in re.finditer(r"fun\s+(\w+)\s*\(\s*(\w+)\s*:\s*String", text):
                u = self._innermost(rel, mt.start(1))
                if not u:
                    continue
                body = text[u["lo"]:u["hi"]]
                mod = re.search(r"getModule\(\"([\w.]+)\"\)", body)
                if mod and re.search(r"callAttr\(\s*" + re.escape(mt.group(2)) + r"\b", body):
                    dispatchers[mt.group(1)] = (mod.group(1), mt.group(2))
        for rel, (text, lang) in files.items():
            if lang == "dart":
                chans = {mt.group(1): (mt.group(2), mt.group(3)) for mt in re.finditer(
                    r"(\w+)\s*=\s*(MethodChannel|EventChannel)\(\s*'([^']+)'", text)}
                for var, (kind, cname) in chans.items():
                    proto = "methodchannel" if kind == "MethodChannel" else "eventchannel"
                    if proto == "eventchannel":
                        for mt in re.finditer(re.escape(var) + r"\s*\.\s*receiveBroadcastStream", text):
                            eid = self._endpoint(proto, cname)
                            g.add_edge(self._owner_at(rel, text, mt.start()), "SUBSCRIBES", eid,
                                       evidence=(rel, line_of(text, mt.start())), provenance="regex", confidence=0.9)
                        continue
                    for mt in re.finditer(re.escape(var) + r"\s*\.\s*invokeMethod\s*(?:<[^>]*>)?\s*\(\s*'(\w+)'", text):
                        eid = self._endpoint(proto, f"{cname}#{mt.group(1)}", channel=cname)
                        g.add_edge(self._owner_at(rel, text, mt.start()), "INVOKES", eid,
                                   evidence=(rel, line_of(text, mt.start())), provenance="regex", confidence=0.9)
            elif lang in ("kotlin", "java"):
                for mt in re.finditer(r"MethodChannel\([^,]+,\s*(\w+|\"[^\"]+\")\s*\)\s*\.\s*setMethodCallHandler", text):
                    tok = mt.group(1).strip('"')
                    cname = consts.get(tok, tok)
                    handler = self._owner_at(rel, text, mt.start())
                    brace = text.find("{", mt.end())
                    masked = self._mask_text(text, lang)
                    end = self._match_brace(masked, brace)
                    block = text[brace:end]
                    # when (call.method) { "name" -> ... }
                    arms = list(re.finditer(r"^\s*((?:\"\w+\"\s*,?\s*)+)->", block, re.M))
                    for i, arm in enumerate(arms):
                        arm_end = arms[i + 1].start() if i + 1 < len(arms) else len(block)
                        arm_text = block[arm.end():arm_end]
                        for name in re.findall(r"\"(\w+)\"", arm.group(1)):
                            eid = self._endpoint("methodchannel", f"{cname}#{name}", channel=cname)
                            ev = (rel, line_of(text, brace + arm.start()))
                            g.add_edge(handler, "HANDLES", eid, evidence=ev, provenance="regex", confidence=0.9)
                            g.add_edge(eid, "ROUTES_TO", handler, evidence=ev, provenance="regex", confidence=0.9)
                            for dm in re.finditer(r"(\w+)\s*\(\s*\"(\w+)\"", arm_text):
                                if dm.group(1) in dispatchers:
                                    module = dispatchers[dm.group(1)][0]
                                    ce = chaquopy_ep(module, dm.group(2))
                                    g.add_edge(eid, "FEEDS", ce, evidence=ev, provenance="regex", roles=["payload"],
                                               via=[handler], confidence=0.9)
                                    g.add_edge(handler, "INVOKES", ce, evidence=ev, provenance="regex", confidence=0.9)
                            for dm in re.finditer(r"\.\s*(\w+)\s*\(", arm_text):
                                tgt = [c for c in self.poly_by_name.get((lang, dm.group(1)), [])]
                                if len(tgt) == 1:
                                    g.add_edge(eid, "ROUTES_TO", tgt[0], evidence=ev, provenance="regex", confidence=0.7)
                for mt in re.finditer(r"EventChannel\([^,]+,\s*(\w+|\"[^\"]+\")\s*\)\s*\.\s*setStreamHandler", text):
                    tok = mt.group(1).strip('"')
                    eid = self._endpoint("eventchannel", consts.get(tok, tok))
                    g.add_edge(self._owner_at(rel, text, mt.start()), "HANDLES", eid,
                               evidence=(rel, line_of(text, mt.start())), provenance="regex", confidence=0.9)
                # who pushes events: eventSink?.success(...)
                ev_names = [n for n in g.nodes if n.startswith("endpoint:eventchannel:")]
                for mt in re.finditer(r"eventSink\??\s*\.\s*success\s*\(", text):
                    for eid in ev_names:
                        g.add_edge(self._owner_at(rel, text, mt.start()), "EMITS", eid,
                                   evidence=(rel, line_of(text, mt.start())), provenance="regex", confidence=0.7)
                # direct Chaquopy calls and dispatcher calls
                for mt in re.finditer(r"getModule\(\"([\w.]+)\"\)\s*\.\s*callAttr\(\s*\"(\w+)\"", text, re.S):
                    ce = chaquopy_ep(mt.group(1), mt.group(2))
                    g.add_edge(self._owner_at(rel, text, mt.start()), "INVOKES", ce,
                               evidence=(rel, line_of(text, mt.start())), provenance="regex", confidence=0.95)
                for mt in re.finditer(r"(\w+)\.callAttr\(\s*\"(\w+)\"", text):
                    var = mt.group(1)
                    mod = re.search(r"\b" + re.escape(var) + r"\s*=\s*[\w.()]*getModule\(\"([\w.]+)\"\)", text)
                    if mod:
                        ce = chaquopy_ep(mod.group(1), mt.group(2))
                        g.add_edge(self._owner_at(rel, text, mt.start()), "INVOKES", ce,
                                   evidence=(rel, line_of(text, mt.start())), provenance="regex", confidence=0.95)
                for fname, (module, _) in dispatchers.items():
                    for mt in re.finditer(r"\b" + re.escape(fname) + r"\s*\(\s*\"(\w+)\"", text):
                        ce = chaquopy_ep(module, mt.group(1))
                        g.add_edge(self._owner_at(rel, text, mt.start()), "INVOKES", ce,
                                   evidence=(rel, line_of(text, mt.start())), provenance="regex", confidence=0.9)
                # Android services started with an Intent
                for mt in re.finditer(r"Intent\([^)]*?(\w+)::class\.java\)", text):
                    tail = text[mt.end():mt.end() + 400]
                    if re.search(r"start(?:Foreground)?Service\(", tail) or re.search(
                            r"start(?:Foreground)?Service\(", text[max(0, mt.start() - 200):mt.start()]):
                        for cid in self.poly_by_name.get(("cls", mt.group(1)), []):
                            g.add_edge(self._owner_at(rel, text, mt.start()), "SPAWNS", cid,
                                       evidence=(rel, line_of(text, mt.start())), provenance="regex",
                                       mechanisms=["android_service"], confidence=0.8)
            # error swallowing and fallback defaults, for "where does a wrong answer come from" questions
            self._fallbacks(rel, text, lang)
        self._frame_endpoints()

    def _fallbacks(self, rel: str, text: str, lang: str) -> None:
        g = self.g
        pats = []
        if lang == "dart":
            pats.append(("null_default", re.compile(
                r"\[\s*'(\w+)'\s*\]\s*(?:as\s+[\w<>?]+\??)?\s*\)?\s*\?\?\s*('[^']*'|\"[^\"]*\"|-?\d[\d.]*|true|false|\[\]|\{\})")))
        if lang in ("kotlin", "java"):
            pats.append(("catch_default", re.compile(r"catch\s*\(\s*\w+\s*:\s*\w+\s*\)\s*\{\s*(\"[^\"]*\"|null|false|-?\d+)\s*\}")))
            pats.append(("catch_default", re.compile(r"catch\s*\(\s*\w+\s+\w+\s*\)\s*\{\s*return\s+(\"[^\"]*\"|null|false|-?\d+)\s*;")))
        for kind, rx in pats:
            for mt in rx.finditer(text):
                owner = self._owner_at(rel, text, mt.start())
                if owner not in g.nodes:
                    continue
                rec = {"kind": kind, "line": text.count("\n", 0, mt.start()) + 1,
                       "key": mt.group(1) if kind == "null_default" else "",
                       "default": (mt.group(2) if kind == "null_default" else mt.group(1)).strip("'\"")}
                g.nodes[owner].setdefault("fallbacks", []).append(rec)

    def _frame_endpoints(self) -> None:
        """Byte-frame protocols: a MAGIC0/MAGIC1 pair names the frame.  Code that compares against the
        magic subscribes to the frame; code that builds bytes with it emits it."""
        g = self.g
        rx = re.compile(r"\b(\w*MAGIC)0\b\s*(?::\s*u8)?\s*=\s*0x([0-9A-Fa-f]{2})\s*;?\s*(?:const\s+)?(\w*MAGIC)1\b\s*"
                        r"(?::\s*u8)?\s*=\s*0x([0-9A-Fa-f]{2})", re.S)
        sources: List[Tuple[str, str, str]] = []
        for m in self.mods.values():
            sources.append((m.rel, m.source, "python"))
        for rel, units in self._poly_units.items():
            if units and units[0]["lang"] == "rust":
                sources.append((rel, units[0]["text"], "rust"))
        for rel, text, lang in sources:
            if "MAGIC" not in text:
                continue
            for mt in rx.finditer(text):
                if mt.group(1) != mt.group(3):
                    continue
                prefix = mt.group(1)
                code = (mt.group(2) + mt.group(4)).upper()
                eid = self._endpoint("frame", code, magic=f"0x{mt.group(2).upper()} 0x{mt.group(4).upper()}")
                for um in re.finditer(r"\b" + re.escape(prefix) + r"[01]\b", text):
                    if um.start() >= mt.start() and um.start() <= mt.end():
                        continue
                    line_start = text.rfind("\n", 0, um.start()) + 1
                    line_end = text.find("\n", um.start())
                    ln = text[line_start:line_end if line_end > 0 else len(text)]
                    lno = text.count("\n", 0, um.start()) + 1
                    if lang == "python":
                        mm = self.mod_by_rel.get(rel)
                        owner = self._py_owner_at(mm, lno) if mm else "src:" + rel
                    else:
                        owner = self._owner_at(rel, text, um.start())
                    et = "SUBSCRIBES" if re.search(r"==|!=|\bmatch\b|=>", ln) else "EMITS"
                    g.add_edge(owner, et, eid, evidence=(rel, lno), provenance="regex", confidence=0.8)

    def _py_owner_at(self, m: ModuleInfo, line: int) -> str:
        best, best_lo = m.nid, -1
        for f in m.funcs:
            lo, hi = f.node.lineno, getattr(f.node, "end_lineno", f.node.lineno)
            if lo <= line <= hi and lo > best_lo:
                best, best_lo = f.fid, lo
        return best

    # ================================================================ pass 7: runtime evidence
    def load_observations(self, paths: List[Path]) -> None:
        for p in paths:
            files = sorted(p.glob("observations-*.json")) if p.is_dir() else [p]
            for f in files:
                try:
                    doc = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    self.warnings.append(f"runtime file {f} unreadable: {exc}")
                    continue
                if doc.get("schema") != "aurora.kg_observations/1":
                    self.warnings.append(f"runtime file {f} has schema {doc.get('schema')!r}; skipped")
                    continue
                doc["_file"] = f.name
                self.observations.append(doc)

    def _code_index(self) -> Dict[Tuple[str, str], str]:
        idx: Dict[Tuple[str, str], str] = {}
        for nid, n in self.g.nodes.items():
            if n["type"] in ("Function", "Class") and n.get("module") and n.get("qualname"):
                m = self.mods.get(n["module"])
                if m:
                    idx.setdefault((m.rel, n["qualname"]), nid)
        for m in self.mods.values():
            idx[(m.rel, "<module>")] = m.nid
        return idx

    def _code_id(self, loc: Optional[List[Any]], idx: Dict[Tuple[str, str], str]) -> Optional[str]:
        if not loc:
            return None
        rel, qual, line = loc[0], loc[1], loc[2]
        # a module imported through a relative sys.path entry reports paths such as a/b/../../c.py
        rel = os.path.normpath(str(rel)).replace("\\", "/")
        q = qual.replace(".<locals>", "")
        nid = idx.get((rel, q))
        if nid:
            return nid
        m = self.mod_by_rel.get(rel)
        if m is None:
            return None
        best, best_lo = None, -1
        for lo, hi, fid in m.spans:
            if lo - 3 <= line <= hi and lo > best_lo:
                best, best_lo = fid, lo
        return best

    def pass_runtime(self) -> None:
        """Observed edges: a static edge the run took gains provenance runtime and observed counts;
        an observed call with no static edge is added with provenance runtime alone."""
        g = self.g
        if not self.observations:
            return
        idx = self._code_index()
        self.observed_nodes: Dict[str, Set[str]] = defaultdict(set)   # node -> scenarios
        self.runtime_unmapped: Counter = Counter()
        for doc in self.observations:
            sc = doc.get("scenario", doc["_file"])
            for row in doc.get("calls", []):
                callee = self._code_id(row.get("callee"), idx)
                caller = self._code_id(row.get("caller"), idx)
                if callee is None:
                    self.runtime_unmapped["callee"] += 1
                    continue
                self.observed_nodes[callee].add(sc)
                if caller is None:
                    continue
                self.observed_nodes[caller].add(sc)
                if caller == callee and not row.get("indirect"):
                    pass
                cnt = int(row.get("count", 1))
                tgt_type = g.nodes.get(callee, {}).get("type")
                if tgt_type != "Function":
                    continue
                key = (caller, "CALLS", callee)
                static = key in g.edges
                if not static and row.get("indirect"):
                    # through a library frame: a callback or a thread target, not a direct call
                    k2 = (caller, "SPAWNS", callee) if (caller, "SPAWNS", callee) in g.edges else \
                        ((caller, "PASSES_CALLBACK", callee) if (caller, "PASSES_CALLBACK", callee) in g.edges else None)
                    if k2:
                        g.add_edge(*k2, provenance="runtime", observed={sc: cnt})
                        continue
                g.add_edge(caller, "CALLS", callee, provenance="runtime", observed={sc: cnt},
                           indirect=bool(row.get("indirect")) or None)
            for row in doc.get("file_io", []):
                owner = self._code_id(row.get("code"), idx)
                if owner is None:
                    continue
                path = str(row.get("path", "")).replace("\\", "/")
                # tempfile names differ on every run; one store stands for all of them
                path = re.sub(r"(^|/)tmp[a-z0-9_]{6,12}(\.tmp)?$", r"\1<tempfile>", path)
                s = normalize_store(path) or path
                sid = "store:" + s
                if sid not in g.nodes:
                    # match a static store by basename when the run used a concrete name for a template
                    base = s.rsplit("/", 1)[-1]
                    cands = [n for n in g.nodes if n.startswith("store:") and n.rsplit("/", 1)[-1] == base]
                    sid = cands[0] if len(cands) == 1 else self.g.add_node(sid, "StateStore", name=s,
                                                                         observed_only=True)
                et = "WRITES" if row.get("mode") == "write" else "READS"
                g.add_edge(owner, et, sid, provenance="runtime", observed={sc: int(row.get("count", 1))})
                self.observed_nodes[sid].add(sc)
                self.observed_nodes[owner].add(sc)
            for row in doc.get("threads", []):
                starter = self._code_id(row.get("starter"), idx)
                target = self._code_id(row.get("target"), idx)
                if starter and target and g.nodes.get(target, {}).get("type") in ("Function", "Class"):
                    g.add_edge(starter, "SPAWNS", target, provenance="runtime", observed={sc: int(row.get("count", 1))},
                               mechanisms=["thread"], thread_names=[row.get("name", "")] if row.get("name") else None)
                    self.observed_nodes[target].add(sc)
            for key, cls in (doc.get("organs") or {}).items():
                oid = self._slot_id(key)
                if not oid:
                    continue
                if oid not in g.nodes:
                    g.add_node(oid, "BusChannel" if key.startswith("_") else "Organ", name=key, observed_only=True)
                g.nodes[oid].setdefault("observed_class", {})[sc] = cls
                self.observed_nodes[oid].add(sc)
                mod, _, qual = cls.partition(":")
                cid = "cls:" + mod + "." + qual if mod in self.mods else None
                if cid and cid in g.nodes and not oid.startswith("bus:"):
                    g.add_edge(oid, "IMPLEMENTED_BY", cid, provenance="runtime", observed={sc: 1})
            sig = doc.get("signals") or {}
            for kind, et in (("writes", "WRITES"), ("reads", "READS"), ("missing_reads", "READS")):
                for key, who in (sig.get(kind) or {}).items():
                    sid = "signal:" + key
                    if sid not in g.nodes:
                        g.add_node(sid, "Signal", name=key, observed_only=True)
                    self.observed_nodes[sid].add(sc)
                    if kind == "missing_reads":
                        g.nodes[sid].setdefault("observed_missing_reads", {})[sc] = sum(int(v) for v in who.values())
                    for w in who:
                        mod, _, fn = w.rpartition(".")
                        cands = [n for n in self.suffix_index.get(fn, set()) if n.startswith("fn:")
                                 and g.nodes[n].get("module", "").split(".")[-1] == mod]
                        if len(cands) == 1:
                            g.add_edge(cands[0], et, sid, provenance="runtime", observed={sc: 1})
        for nid, scs in self.observed_nodes.items():
            if nid in g.nodes:
                g.nodes[nid]["observed_in"] = sorted(scs)
        self.log(f"pass 7: runtime evidence from {len(self.observations)} recording(s); "
                 f"{len(self.observed_nodes)} nodes observed, {sum(self.runtime_unmapped.values())} rows unmapped")

    # ================================================================ pass 8: intent and claims
    def pass_intent(self, ownership_file: Optional[Path]) -> None:
        g = self.g
        self.ownership_meta: Dict[str, Any] = {}
        self.claim_disagreements: List[Dict[str, Any]] = []
        self.claims_missing: List[str] = []
        path = ownership_file
        if path is None:
            cand = self.root / self.ont.get("ownership_mapping", "docs/module_ownership.json")
            path = cand if cand.exists() else None
        anchor_owned = {(e["source"], e["target"]) for e in g.edges.values()
                        if e["type"] == "OWNED_BY" and "ontology" in e["provenance"]}
        if path is not None and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.ownership_meta = {"path": str(path.relative_to(self.root)) if str(path).startswith(str(self.root))
                                   else path.name, "schema": data.get("schema"),
                                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
                                   "scope": data.get("scope", {}).get("statement", ""),
                                   "covers": data.get("scope", {}).get("covers", []),
                                   "not_covered": data.get("scope", {}).get("not_covered", [])}
            # the mapping is the one source of declared ownership: drop edges read from the markdown
            for key in [k for k, e in g.edges.items() if e["type"] == "OWNED_BY"]:
                del g.edges[key]
                g.evidence.pop(key, None)
            # schema 1 keyed "modules" by path with a "category"; schema 2 keys "files" by path with a
            # "subsystem" inside a declared "domain", and adds import-derived composites.  Both are claims here.
            v2 = "files" in data
            self.ownership_meta["version"] = 2 if v2 else 1
            records = (data.get("files") if v2 else data.get("modules")) or {}
            for c in (data.get("subsystems") if v2 else data.get("categories")) or []:
                g.add_node(f"subsys:category:{c['id']}", "Subsystem", name=c.get("name", c["id"]), kind="category",
                           holds=c.get("holds", ""), declared=True, declared_domain=c.get("domain"))
            self.declared_domains: List[Dict[str, Any]] = list(data.get("domains") or []) if v2 else []
            self.declared_composites: Dict[str, Dict[str, Any]] = dict(data.get("composites") or {}) if v2 else {}
            # candidates the record holds back (import-only so far) are checked the same way but never promoted
            self.declared_candidates: Dict[str, Dict[str, Any]] = dict(data.get("composite_candidates") or {}) \
                if v2 else {}
            self.ownership_meta["declared_files"] = len(records)
            mapped_layer: Dict[str, str] = {}
            for rel, rec in sorted(records.items()):
                m = self.mod_by_rel.get(rel)
                nid = m.nid if m is not None else ("src:" + rel if ("src:" + rel) in g.nodes else None)
                if nid is None:
                    self.claims_missing.append(rel)
                    continue
                node = g.nodes[nid]
                cat = rec.get("subsystem") if v2 else rec.get("category")
                node["claim"] = {"category": cat, **{k: rec.get(k) for k in (
                    "also", "layer", "layer_role", "basis", "duties", "domain", "composite", "exercises")
                    if k in rec}}
                ev = (self.ownership_meta["path"], 0)
                if cat:
                    g.add_edge(nid, "MEMBER_OF", f"subsys:category:{cat}", evidence=ev,
                               provenance="claim", method=["declared_category"], claim_basis=rec.get("basis"))
                for extra in rec.get("also") or []:
                    if f"subsys:category:{extra}" in g.nodes:
                        g.add_edge(nid, "MEMBER_OF", f"subsys:category:{extra}", evidence=ev,
                                   provenance="claim", method=["declared_also"], claim_basis=rec.get("basis"))
                if m is None:
                    continue
                if rec.get("layer"):
                    lid = "layer:" + ("ORCH" if rec["layer"] == "orchestrator" else rec["layer"])
                    if lid in g.nodes:
                        g.add_edge(m.nid, "OWNED_BY", lid, evidence=ev, provenance="claim",
                                   layer_role=rec.get("layer_role"))
                        mapped_layer[m.nid] = lid
            # layer names come from the record too; the markdown is rendered from it and is not parsed here
            for lay in (data.get("layers") or []) if v2 else []:
                lid = "layer:" + ("ORCH" if lay.get("id") == "orchestrator" else lay.get("id", ""))
                if lid in g.nodes:
                    g.nodes[lid]["declared_name"] = lay.get("name", "")
                    g.nodes[lid].pop("declared_missing", None)
                elif lay.get("id"):
                    g.add_node(lid, "Layer", name=lay.get("name", lay["id"]), layer_id=lay["id"],
                               declared_name=lay.get("name", ""))
            for rec in data.get("layer_records_without_file") or []:
                lid = "layer:" + ("ORCH" if rec.get("layer") == "orchestrator" else rec.get("layer", ""))
                if lid in g.nodes:
                    g.nodes[lid].setdefault("declared_missing", [])
                    if rec["path"] not in g.nodes[lid]["declared_missing"]:
                        g.nodes[lid]["declared_missing"].append(rec["path"])
            # the record must agree with the ontology's own layer anchors (one file per layer); a module the
            # record puts in a layer the ontology does not anchor is normal and not a disagreement
            for src, lid in sorted(anchor_owned):
                if mapped_layer.get(src) != lid:
                    self.claim_disagreements.append({"module": src, "anchor_layer": lid,
                                                     "mapping_layer": mapped_layer.get(src)})
        else:
            self.ownership_meta = {"path": None, "note": "no canonical mapping found; layer ownership read from "
                                                         "docs/LAYER_MODULE_OWNERSHIP.md"}
        # layers are subsystems too
        for lid, n in list(g.nodes.items()):
            if n["type"] == "Layer":
                sid = "subsys:" + lid
                g.add_node(sid, "Subsystem", name=n.get("name", lid), kind="layer", declared=True)
                g.add_edge(sid, "PART_OF", lid, provenance="ontology")
        for e in [e for e in g.edges.values() if e["type"] == "OWNED_BY"]:
            g.add_edge(e["source"], "MEMBER_OF", "subsys:" + e["target"], provenance=e["provenance"][0],
                       method=["declared_layer"])
        # implemented responsibilities: the module behind each organ
        for e in [e for e in g.edges.values() if e["type"] == "IMPLEMENTED_BY"]:
            cls = e["target"]
            mod = self.parent_of.get(cls)
            while mod and not mod.startswith("mod:"):
                mod = self.parent_of.get(mod)
            if mod:
                organ = e["source"].split(":", 1)[1]
                sid = f"subsys:organ:{organ}"
                g.add_node(sid, "Subsystem", name=f"organ {organ}", kind="organ", declared=False)
                g.add_edge(mod, "MEMBER_OF", sid, provenance=e["provenance"][0], method=["organ"])
        # areas outside the mapping's scope, grouped by where they live
        areas = self.ont.get("areas", [])
        for nid, n in list(g.nodes.items()):
            if n["type"] not in ("Module", "SourceFile"):
                continue
            rel = n.get("path", "")
            for a in areas:
                if rel.startswith(a["prefix"]):
                    sid = f"subsys:area:{a['id']}"
                    g.add_node(sid, "Subsystem", name=a["name"], kind="area", declared=False)
                    g.add_edge(nid, "MEMBER_OF", sid, provenance="path", method=["path"])
                    break
        self.verify_claims()

    def reachable(self, starts: List[str], etypes: Set[str]) -> Set[str]:
        out_idx: Dict[str, List[str]] = defaultdict(list)
        for (s, et, d) in self.g.edges:
            if et in etypes:
                out_idx[s].append(d)
        impl: Dict[str, List[str]] = defaultdict(list)
        for (s, et, d) in self.g.edges:
            if et == "IMPLEMENTED_BY":
                impl[s].append(d)
        seen = set(x for x in starts if x in self.g.nodes)
        stack = list(seen)
        while stack:
            cur = stack.pop()
            nxt = list(out_idx.get(cur, ()))
            if cur.startswith("organ:"):
                nxt += impl.get(cur, [])
            if cur.startswith("cls:"):
                info = self.class_by_id.get(cur)
                if info:
                    nxt += list(info.methods.values())
            if cur.startswith("mod:"):
                mm = self.mod_by_id.get(cur)
                if mm:
                    nxt += [f.fid for f in mm.funcs if f.parent is None and f.owner_cls is None and
                            any(d.startswith(("atexit", "register")) for d in self._decorators(f.node))]
            for d in nxt:
                if d not in seen:
                    seen.add(d)
                    stack.append(d)
        return seen

    def module_of(self, nid: str) -> Optional[str]:
        cur = nid
        hops = 0
        while cur and not cur.startswith(("mod:", "src:")) and hops < 20:
            cur = self.parent_of.get(cur) or self.g.nodes.get(cur, {}).get("holder")
            hops += 1
        if cur and cur.startswith("mod:"):
            return cur
        n = self.g.nodes.get(nid, {})
        if n.get("path") and ("src:" + n["path"]) in self.g.nodes:
            return "src:" + n["path"]
        return cur

    def verify_claims(self) -> None:
        """Hold each declared category against what the code shows.  A claim is never changed here;
        the check says whether the implementation and the run agree with it."""
        g = self.g
        runtime_starts = []
        for rt in self.ont.get("runtimes", []):
            runtime_starts += rt.get("entrypoints", [])
        flow = {"CALLS", "INSTANTIATES", "SPAWNS", "PASSES_CALLBACK", "ROUTES_TO", "USES_ORGAN", "INVOKES"}
        self.runtime_reach: Dict[str, Set[str]] = {}
        for rt in self.ont.get("runtimes", []):
            self.runtime_reach[rt["id"]] = self.reachable(rt.get("entrypoints", []), flow)
        writes: Counter = Counter()
        own_writes: Dict[str, Set[str]] = defaultdict(set)
        state_readers: Dict[str, Set[str]] = defaultdict(set)
        inbound_prod: Dict[str, Set[str]] = defaultdict(set)
        organ_mods: Dict[str, Set[str]] = defaultdict(set)
        for (s, et, d), e in g.edges.items():
            ms, md = self.module_of(s), self.module_of(d)
            if et == "WRITES" and d.startswith("store:") and ms:
                writes[ms] += 1
            if et == "WRITES" and d.startswith(("store:", "bus:")) and ms:
                own_writes[ms].add(d)
            if et == "READS" and d.startswith(("store:", "bus:")) and ms:
                state_readers[d].add(ms)
            if et in ("CALLS", "INSTANTIATES", "IMPORTS") and ms and md and ms != md:
                mm = self.mod_by_id.get(ms)
                if mm and mm.role not in ("test", "script", "tool"):
                    inbound_prod[md].add(ms)
            if et == "IMPLEMENTED_BY":
                mc = self.module_of(d)
                if mc:
                    organ_mods[mc].add(s.split(":", 1)[1])
        reach_mods: Dict[str, Set[str]] = defaultdict(set)
        for rid, nodes in self.runtime_reach.items():
            for nid in nodes:
                if nid in g.nodes and g.nodes[nid]["type"] in ("Function", "Class"):
                    g.nodes[nid].setdefault("reachable_from", []).append(rid)
                mm = self.module_of(nid)
                if mm:
                    reach_mods[mm].add(rid)
        observed_mods: Dict[str, Set[str]] = defaultdict(set)
        for nid, scs in getattr(self, "observed_nodes", {}).items():
            mm = self.module_of(nid)
            if mm:
                observed_mods[mm] |= scs
        self.claim_checks: Dict[str, Dict[str, Any]] = {}
        for nid, n in g.nodes.items():
            if n["type"] != "Module":
                continue
            ev = {"reachable_from": sorted(reach_mods.get(nid, ())), "observed_in": sorted(observed_mods.get(nid, ())),
                  "organs": sorted(organ_mods.get(nid, ())), "store_writes": writes.get(nid, 0),
                  "production_importers": len(inbound_prod.get(nid, ()))}
            n["evidence_profile"] = ev
            claim = n.get("claim")
            if not claim:
                continue
            notes: List[str] = []
            cats = [claim.get("category")] + list(claim.get("also") or [])
            operational = bool(ev["organs"]) or bool(ev["observed_in"]) or bool(ev["reachable_from"])
            observations: List[str] = []
            if claim.get("category") == "investigative" and "investigative" == cats[0] and len(cats) == 1:
                # an investigative file may run live and keep its own records (the QuasiArch observer, the
                # learning probe); it conflicts with its claim only when state it writes is read by production
                # code outside investigative work, which makes it an input to her, not an observer of her
                fed: List[str] = []
                setup: List[str] = []
                for t in sorted(own_writes.get(nid, ())):
                    # an entry point that builds her systems dict for its own run is setting the run up; a bus slot
                    # it fills there lives only in that process
                    if t.startswith("bus:") and n.get("is_entrypoint"):
                        setup.append(t)
                        continue
                    for r in state_readers.get(t, ()):
                        if r == nid:
                            continue
                        rm = self.mod_by_id.get(r)
                        rcat = (g.nodes.get(r, {}).get("claim") or {}).get("category")
                        if rm is not None and rm.role not in ("test", "script", "tool") \
                                and rcat not in ("investigative", "tests"):
                            fed.append(f"{t} (read by {r.split(':', 1)[1]})")
                            break
                if fed:
                    notes.append("writes state that production code outside investigative work reads: "
                                 + ", ".join(fed[:4]))
                if ev["organs"]:
                    observations.append(f"live organ(s) {', '.join(ev['organs'][:4])}")
                if ev["store_writes"] and not fed:
                    observations.append(f"keeps its own records ({ev['store_writes']} store reference(s))")
                if ev["observed_in"]:
                    observations.append(f"ran in {', '.join(ev['observed_in'])}")
                if setup:
                    observations.append("fills bus slot(s) for its own run: " + ", ".join(setup[:4]))
            if claim.get("category") == "runtime" and not ev["reachable_from"] and not ev["observed_in"] \
                    and not n.get("is_entrypoint"):
                notes.append("declared runtime but not reachable from any recorded entry point")
            gaps: List[str] = []
            if not operational and not ev["production_importers"] and claim.get("category") != "investigative":
                gaps.append("no static production importer, organ or recorded run reaches it (dynamic loading "
                            "would not show)")
            status = "conflict" if notes else ("consistent" if (operational or ev["production_importers"])
                                                else "unverified")
            notes += gaps
            self.claim_checks[nid] = {"status": status, "notes": notes, "observations": observations,
                                      "claim_basis": claim.get("basis")}
            n["claim_check"] = status

    # ================================================================ pass 9: crystal hierarchy
    # The repository is the king quasi; each domain (desktop, phone app, ACM, ...) is a quasi; the declared
    # categories inside a domain are its higher-order subsystems; every file is a base unit.  Composites
    # sit between higher-order and base and are never declared: a group of base units is promoted to a
    # composite only when the graph shows them bound together, and the binding edges are kept as evidence.

    def pass_hierarchy(self) -> None:
        g = self.g
        king = g.add_node("subsys:king:aurora", "Subsystem", name="Aurora repository", kind="king", level="king",
                          declared=True)
        # The mapping's own domains win when it declares them (schema 2); the ontology's path prefixes are the
        # fallback for files the mapping does not cover, translated onto the declared domain ids.
        declared = getattr(self, "declared_domains", []) or []
        prefix_domains = self.ont.get("domains", [])
        fallback = self.ont.get("domain_fallback", {}) if declared else {}
        domains = [{"id": d["id"], "name": d.get("name", d["id"]), "holds": d.get("holds", "")} for d in declared] \
            or prefix_domains
        dom_of: Dict[str, str] = {}
        dom_basis: Dict[str, str] = {}
        for d in domains:
            did = f"subsys:quasi:{d['id']}"
            g.add_node(did, "Subsystem", name=d["name"], kind="quasi", level="quasi", declared=True,
                       holds=d.get("holds", ""))
            g.add_edge(did, "PART_OF", king, provenance="claim" if declared else "ontology")
        dom_ids = {d["id"] for d in domains}
        for nid, n in g.nodes.items():
            if n["type"] not in ("Module", "SourceFile"):
                continue
            rel = n.get("path", "")
            claimed = (n.get("claim") or {}).get("domain")
            if claimed and claimed in dom_ids:
                dom_of[nid], dom_basis[nid] = claimed, "claim"
            else:
                for d in prefix_domains:
                    if any(rel.startswith(px) for px in d.get("prefixes", [])) or (
                            d.get("root_python") and "/" not in rel and rel.endswith(".py")):
                        did = fallback.get(d["id"], d["id"])
                        if did in dom_ids:
                            dom_of[nid], dom_basis[nid] = did, "path"
                        break
            n["level"] = "base"
            if nid in dom_of:
                n["domain"] = dom_of[nid]
                g.add_edge(nid, "MEMBER_OF", f"subsys:quasi:{dom_of[nid]}", provenance=dom_basis[nid],
                           method=["domain"])
        self.dom_of = dom_of
        # higher-order: declared categories, placed in the domain their members live in
        cat_dom: Dict[str, Counter] = defaultdict(Counter)
        cat_members: Dict[str, List[str]] = defaultdict(list)
        for e in list(g.edges.values()):
            if e["type"] == "MEMBER_OF" and e["target"].startswith("subsys:category:") \
                    and "declared_category" in (e.get("method") or []):
                cat_members[e["target"]].append(e["source"])
                cat_dom[e["target"]][dom_of.get(e["source"], "?")] += 1
        group_of: Dict[str, str] = {}
        for cid, cnt in cat_dom.items():
            g.nodes[cid]["level"] = "higher_order"
            for mid in cat_members[cid]:
                group_of[mid] = cid
            ddom = g.nodes[cid].get("declared_domain")
            if ddom and f"subsys:quasi:{ddom}" in g.nodes:
                g.add_edge(cid, "PART_OF", f"subsys:quasi:{ddom}", provenance="claim")
                strays = {d: c for d, c in cnt.items() if d not in (ddom, "?")}
                if strays:
                    g.nodes[cid]["members_in_other_domains"] = strays
                continue
            for dom, _ in cnt.most_common():
                if dom != "?":
                    g.add_edge(cid, "PART_OF", f"subsys:quasi:{dom}", provenance="claim")
            for mid in cat_members[cid]:
                group_of[mid] = cid
        # files outside the mapping: their area is the higher-order grouping (inferred)
        for e in list(g.edges.values()):
            if e["type"] == "MEMBER_OF" and e["target"].startswith("subsys:area:") and e["source"] not in group_of:
                group_of[e["source"]] = e["target"]
                g.nodes[e["target"]]["level"] = "higher_order"
                dom = dom_of.get(e["source"])
                if dom:
                    g.add_edge(e["target"], "PART_OF", f"subsys:quasi:{dom}", provenance="path")
        # binding strength between base units, from implemented and observed edges only
        bind: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
        bind_ev: Dict[Tuple[str, str], List[Tuple[str, str, str]]] = defaultdict(list)
        writers: Dict[str, Set[str]] = defaultdict(set)
        readers: Dict[str, Set[str]] = defaultdict(set)
        for (s, et, d), e in list(g.edges.items()):
            if not set(e.get("basis", [])) & {"implemented", "observed"}:
                continue
            ms, md = self.module_of(s), self.module_of(d) if not d.split(":")[0] in (
                "store", "bus", "organ", "signal", "env", "endpoint") else None
            if et in ("CALLS", "INSTANTIATES", "INHERITS", "SPAWNS", "PASSES_CALLBACK") and ms and md and ms != md:
                k = tuple(sorted((ms, md)))
                bind[k][et] += 1
                if len(bind_ev[k]) < 8:
                    bind_ev[k].append((s, et, d))
            if et == "FEEDS" and ms:
                md2 = self.module_of(d)
                if md2 and md2 != ms:
                    k = tuple(sorted((ms, md2)))
                    bind[k]["FEEDS"] += 1
                    if len(bind_ev[k]) < 8:
                        bind_ev[k].append((s, et, d))
            if et in ("WRITES", "REGISTERS") and ms and d.split(":")[0] in ("store", "bus", "organ", "signal", "field"):
                writers[d].add(ms)
            if et in ("READS", "USES_ORGAN") and ms and d.split(":")[0] in ("store", "bus", "organ", "signal", "field"):
                readers[d].add(ms)
        for ch in set(writers) | set(readers):
            for w in writers.get(ch, ()):
                for r in readers.get(ch, ()):
                    if w != r:
                        k = tuple(sorted((w, r)))
                        bind[k]["SHARED_STATE"] += 1
                        if len(bind_ev[k]) < 8:
                            bind_ev[k].append((w, "SHARES", ch))
        threshold = int(self.ont.get("composite_min_binding", 3))
        groups: Dict[str, List[str]] = defaultdict(list)
        for mid, grp in group_of.items():
            groups[grp].append(mid)
        self.composites: List[Dict[str, Any]] = []
        for grp, members in sorted(groups.items()):
            mem = set(members)
            adj: Dict[str, Set[str]] = defaultdict(set)
            for (a, b2), c in bind.items():
                if a in mem and b2 in mem and sum(c.values()) >= threshold and \
                        (len(c) >= 2 or c.get("CALLS", 0) + c.get("INSTANTIATES", 0) >= threshold):
                    adj[a].add(b2)
                    adj[b2].add(a)
            seen: Set[str] = set()
            for start in sorted(adj):
                if start in seen:
                    continue
                comp, stack = [], [start]
                seen.add(start)
                while stack:
                    cur = stack.pop()
                    comp.append(cur)
                    for nb in adj[cur]:
                        if nb not in seen:
                            seen.add(nb)
                            stack.append(nb)
                if len(comp) < 2:
                    continue
                comp.sort()
                cset = set(comp)
                internal = Counter()
                ev = []
                for (a, b2), c in bind.items():
                    if a in cset and b2 in cset:
                        internal.update(c)
                        ev.extend(bind_ev[(a, b2)][:3])
                external = sum(sum(c.values()) for (a, b2), c in bind.items() if (a in cset) != (b2 in cset))
                tot_int = sum(internal.values())
                cohesion = round(tot_int / (tot_int + external), 3) if tot_int + external else 0.0
                name = os.path.commonprefix([g.nodes[m].get("path", m).rsplit("/", 1)[-1] for m in comp]).strip("_.") \
                    or grp.split(":")[-1]
                cid = f"subsys:composite:{grp.split(':')[-1]}:{hashlib.sha256('|'.join(comp).encode()).hexdigest()[:8]}"
                g.add_node(cid, "Subsystem", name=f"{name} composite", kind="composite", level="composite",
                           declared=False, members=len(comp), cohesion=cohesion,
                           binding=dict(internal), external_binding=external)
                g.add_edge(cid, "PART_OF", grp, provenance="name") if grp.startswith("subsys:area:") else \
                    g.add_edge(cid, "PART_OF", grp, provenance="claim")
                for mid in comp:
                    g.add_edge(mid, "MEMBER_OF", cid, provenance="path", method=["evidence_composite"],
                               confidence=min(0.9, 0.5 + cohesion))
                self.composites.append({"id": cid, "higher_order": grp, "members": [g.nodes[m].get("path", m) for m in comp],
                                        "binding": dict(internal), "external_binding": external, "cohesion": cohesion,
                                        "evidence": [list(x) for x in ev[:24]],
                                        "rule": f"pairs bound by >= {threshold} implemented or observed edges of two "
                                                f"kinds (or >= {threshold} calls), connected within one higher-order group"})
        self._compare_declared_composites(bind, bind_ev, dom_of)
        self._cross_domain_links(dom_of)
        self.log(f"pass 9: hierarchy: {len(domains)} quasi domains, {len(groups)} higher-order groups, "
                 f"{len(self.composites)} composites promoted on evidence, "
                 f"{len(self.declared_composite_checks)} declared composites checked, "
                 f"{len(self.cross_domain)} cross-domain links")

    def _compare_declared_composites(self, bind: Dict[Tuple[str, str], Counter],
                                     bind_ev: Dict[Tuple[str, str], List[Tuple[str, str, str]]],
                                     dom_of: Dict[str, str]) -> None:
        """Hold each composite the mapping declares (derived there from import edges) against the binding the
        graph sees between the same files: calls, instantiation, inheritance, spawns, callbacks, value flow and
        shared state, from implemented code and recorded runs.  An import alone binds nothing here."""
        g = self.g
        self.declared_composite_checks: List[Dict[str, Any]] = []
        nid_of = {}
        for nid, n in g.nodes.items():
            if n["type"] in ("Module", "SourceFile") and n.get("path"):
                nid_of[n["path"]] = nid
        ev_members: Dict[str, Set[str]] = {c["id"]: set(c["members"]) for c in self.composites}
        todo = [(cid, rec, False) for cid, rec in sorted(getattr(self, "declared_composites", {}).items())]
        todo += [(cid, rec, True) for cid, rec in sorted(getattr(self, "declared_candidates", {}).items())]
        for cid, rec, candidate in todo:
            members = [m for m in rec.get("members", [])]
            found = [nid_of[m] for m in members if m in nid_of]
            fset = set(found)
            sid = None
            if not candidate:
                sid = f"subsys:declared:{cid}"
                g.add_node(sid, "Subsystem", name=f"{cid} (declared composite)", kind="declared_composite",
                           level="composite", declared=True, hub=rec.get("hub"), members=len(members))
                parent = f"subsys:category:{rec.get('subsystem')}"
                if parent in g.nodes:
                    g.add_edge(sid, "PART_OF", parent, provenance="claim")
                for nid in found:
                    g.add_edge(nid, "MEMBER_OF", sid, provenance="claim", method=["declared_composite"])
            links = []
            for a, b in rec.get("links") or []:
                na, nb = nid_of.get(a), nid_of.get(b)
                c = bind.get(tuple(sorted((na, nb)))) if na and nb else None
                links.append({"link": [a, b], "binding": dict(c) if c else {},
                              "evidence": [list(x) for x in bind_ev.get(tuple(sorted((na, nb))), [])[:3]]
                              if na and nb else []})
            bound_links = sum(1 for l in links if l["binding"])
            internal = Counter()
            for (a, b2), c in bind.items():
                if a in fset and b2 in fset:
                    internal.update(c)
            external = sum(sum(c.values()) for (a, b2), c in bind.items() if (a in fset) != (b2 in fset))
            tot = sum(internal.values())
            best, best_j = None, 0.0
            for eid, em in ev_members.items():
                inter = len(em & set(members))
                if inter:
                    j = inter / len(em | set(members))
                    if j > best_j:
                        best, best_j = eid, j
            status = ("supported" if links and bound_links == len(links)
                      else "partly_supported" if bound_links else "import_only")
            self.declared_composite_checks.append({
                "id": cid, "candidate": candidate, "subsystem": rec.get("subsystem"), "domain": rec.get("domain"),
                "hub": rec.get("hub"),
                "members": members, "missing_from_graph": [m for m in members if m not in nid_of],
                "declared_links": len(links), "links_with_binding": bound_links, "status": status,
                "internal_binding": dict(internal),
                "cohesion": round(tot / (tot + external), 3) if tot + external else 0.0,
                "best_evidence_composite": best, "jaccard": round(best_j, 3), "links": links})
            if sid:
                g.nodes[sid]["claim_check"] = status

    def _cross_domain_links(self, dom_of: Dict[str, str]) -> None:
        """Links between files in different domains, from implemented or observed edges: direct code edges, and
        every pair of files that meet at one endpoint (a method channel, Chaquopy call, HTTP route or frame)."""
        g = self.g
        pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}

        def note(a: Optional[str], b: Optional[str], kind: str, ev: Tuple[str, ...]) -> None:
            if not a or not b or a == b or dom_of.get(a) == dom_of.get(b) or a not in dom_of or b not in dom_of:
                return
            k = tuple(sorted((a, b)))
            rec = pairs.setdefault(k, {"kinds": Counter(), "evidence": []})
            rec["kinds"][kind] += 1
            if len(rec["evidence"]) < 6:
                rec["evidence"].append(list(ev))

        touch: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)
        for (s, et, d), e in list(g.edges.items()):
            if not set(e.get("basis", [])) & {"implemented", "observed"}:
                continue
            if d.startswith("endpoint:") and et in ("INVOKES", "HANDLES", "EMITS", "SUBSCRIBES", "FEEDS"):
                touch[d].add((self.module_of(s) or "", et))
            if s.startswith("endpoint:") and et in ("ROUTES_TO", "FEEDS", "HANDLES"):
                touch[s].add((self.module_of(d) or "", "ROUTES_TO" if et == "ROUTES_TO" else et))
            if et in ("CALLS", "INSTANTIATES", "INHERITS", "IMPORTS", "SPAWNS") and not d.startswith("endpoint:"):
                note(self.module_of(s), self.module_of(d), et, (s, et, d))
        # an endpoint FEEDS endpoint edge (MethodChannel -> Chaquopy) joins both endpoints' files
        joined: Dict[str, Set[str]] = defaultdict(set)
        for (s, et, d) in list(g.edges):
            if et == "FEEDS" and s.startswith("endpoint:") and d.startswith("endpoint:"):
                joined[s].add(d)
                joined[d].add(s)
        for ep, mods in list(touch.items()):
            allm = set(mods)
            for other in joined.get(ep, ()):
                allm |= touch.get(other, set())
            for a, ka in allm:
                for b, kb in allm:
                    if a < b:
                        note(a, b, f"endpoint:{ka}/{kb}", (a, ep, b))
        self.cross_domain: List[Dict[str, Any]] = []
        for (a, b), rec in sorted(pairs.items(), key=lambda kv: -sum(kv[1]["kinds"].values())):
            self.cross_domain.append({"files": [g.nodes[a].get("path", a), g.nodes[b].get("path", b)],
                                      "domains": [dom_of.get(a), dom_of.get(b)], "kinds": dict(rec["kinds"]),
                                      "evidence": rec["evidence"]})

    # ================================================================ coverage
    def build_coverage(self) -> Dict[str, Any]:
        g = self.g
        analysed = {}
        for rel in sorted(self.repo_files):
            if rel in self.mod_by_rel:
                m = self.mod_by_rel[rel]
                st = "parsed_ast" if m.tree is not None else "parse_failed"
            elif ("src:" + rel) in g.nodes:
                lang = g.nodes["src:" + rel].get("language")
                st = "parsed_regex" if lang in ("rust", "dart", "kotlin", "java") else "scanned_launches"
            elif ("doc:" + rel) in g.nodes:
                st = "scanned_references"
            else:
                st = "not_analysed"
            analysed[rel] = st
        self.file_inventory = analysed
        reasons = Counter(s[4] for s in self.unresolved_sites)
        static_reach = set().union(*self.runtime_reach.values()) if getattr(self, "runtime_reach", None) else set()
        observed = set(getattr(self, "observed_nodes", {}).keys())
        recorded = {doc.get("scenario") for doc in self.observations}
        unobserved_reachable = []
        if observed:
            desk = self.runtime_reach.get("desktop", set())
            unobserved_reachable = sorted(n for n in desk if n.startswith("fn:") and n not in observed)
        edge_basis = Counter()
        for e in g.edges.values():
            edge_basis["+".join(e.get("basis", []))] += 1
        return {"files": Counter(analysed.values()), "unresolved_reasons": reasons,
                "unresolved_internal": sum(v for k, v in reasons.items() if k not in ("external", "builtin_value")),
                "scenarios_recorded": sorted(x for x in recorded if x),
                "observed_nodes": len(observed), "statically_reachable": len(static_reach),
                "unobserved_reachable_desktop": unobserved_reachable, "edge_basis": edge_basis,
                "claims_missing": self.claims_missing if hasattr(self, "claims_missing") else [],
                "claim_disagreements": getattr(self, "claim_disagreements", []),
                "claim_checks": Counter(v["status"] for v in getattr(self, "claim_checks", {}).values()),
                "ownership": getattr(self, "ownership_meta", {})}

    # ================================================================ PASS 6
    def pass_derive(self) -> None:
        g = self.g
        # TESTS: a test module importing a module that is not itself a test
        for e in list(g.edges.values()):
            if e["type"] != "IMPORTS" or not e["target"].startswith("mod:"):
                continue
            src, dst = self.mod_by_id.get(e["source"]), self.mod_by_id.get(e["target"])
            if src and dst and src.role == "test" and dst.role != "test":
                ev = sorted(g.evidence.get((e["source"], e["type"], e["target"]), ()))
                g.add_edge(src.nid, "TESTS", dst.nid, evidence=ev[0] if ev else None)
        # OVERRIDES
        for c in self.class_by_id.values():
            for name, fid in c.methods.items():
                for base in c.base_ids:
                    target = self.find_method(base, name)
                    if target and target != fid:
                        g.add_edge(fid, "OVERRIDES", target)
                        break
        # PERSISTS_TO: the class that owns a method which writes a store
        for e in list(g.edges.values()):
            if e["type"] == "WRITES" and e["target"].startswith("store:"):
                owner = e["source"]
                cls = owner if owner.startswith("cls:") else None
                f = self.func_by_id.get(owner)
                if f is not None and f.owner_cls is not None:
                    cls = f.owner_cls.cid
                if cls:
                    g.add_edge(cls, "PERSISTS_TO", e["target"], provenance="ast")
                    g.nodes[cls]["persistent"] = True
        # fan-in / fan-out and per-node flags
        self._overriders = {e["source"] for e in g.edges.values() if e["type"] == "OVERRIDES"}
        fan_in: Counter = Counter()
        fan_out: Counter = Counter()
        imp_in: Counter = Counter()
        imp_out: Counter = Counter()
        has_in: Dict[str, Set[str]] = defaultdict(set)
        for e in g.edges.values():
            has_in[e["target"]].add(e["type"])
            if e["type"] == "CALLS":
                fan_in[e["target"]] += 1
                fan_out[e["source"]] += 1
            elif e["type"] == "IMPORTS" and e["target"].startswith("mod:") and e["source"].startswith("mod:"):
                imp_in[e["target"]] += 1
                imp_out[e["source"]] += 1
        for nid, node in g.nodes.items():
            t = node["type"]
            if t == "Function":
                node["fan_in"] = fan_in[nid]
                node["fan_out"] = fan_out[nid]
                node["unreferenced_candidate"] = self._unreferenced(nid, node, has_in[nid])
            elif t == "Module":
                node["imported_by"] = imp_in[nid]
                node["imports_internal"] = imp_out[nid]
                node["orphan_candidate"] = self._orphan(nid, node, has_in[nid])
        # store, bus and organ flow summaries; a slot only tests touch is marked test_only
        flows: Dict[str, Counter] = defaultdict(Counter)
        prod: Counter = Counter()
        for e in g.edges.values():
            if e["target"].split(":", 1)[0] in ("store", "bus", "organ", "env"):
                flows[e["target"]][e["type"]] += 1
                src_mod = self.mod_by_id.get(_lift(g, self, e["source"]))
                if src_mod is not None and src_mod.role != "test":
                    prod[e["target"]] += 1
        for nid, c in flows.items():
            node = g.nodes[nid]
            node["test_only"] = prod[nid] == 0
            if nid.startswith(("store:", "bus:", "env:")):
                node["writers"] = c["WRITES"]
                node["readers"] = c["READS"]
                if nid.startswith("store:"):
                    node["references"] = c["REFERENCES"]
            else:
                node["registered_by"] = c["REGISTERS"]
                node["used_by"] = c["USES_ORGAN"]
        for nid, node in g.nodes.items():
            if node["type"] == "DoctrineRule":
                node.setdefault("defined", False)
                node.setdefault("title", "")
        self.log("pass 6: derived edges and metrics")

    def _unreferenced(self, nid: str, node: Dict[str, Any], inbound: Set[str]) -> bool:
        name = node["name"]
        if name.startswith("__") or name.startswith("test") or name in ("main", "setUp", "tearDown"):
            return False
        if node.get("decorators") or "CALLS" in inbound or "OVERRIDES" in inbound:
            return False
        if self.mentioned_names.get(name, 0) or name in self.mentioned_strings:
            return False
        f = self.func_by_id.get(nid)
        if f is not None and f.owner_cls is not None and f.owner_cls.external_bases:
            return False
        if f is not None and f.module.role == "test":
            return False
        if nid in self._overriders:
            return False
        return True

    def _orphan(self, nid: str, node: Dict[str, Any], inbound: Set[str]) -> bool:
        if node["role"] in ("test", "package_init") or node.get("is_entrypoint") or node.get("runs_on_import"):
            return False
        if inbound & {"IMPORTS", "RUNS", "TESTS"}:
            return False
        m = self.mod_by_id[nid]
        stem = m.rel.rsplit("/", 1)[-1][:-3]
        if stem in self.mentioned_strings or m.name in self.mentioned_strings:
            return False
        return True

    # ============================================================ VALIDATE
    def validate(self) -> List[str]:
        problems: List[str] = []
        for (src, etype, dst), e in self.g.edges.items():
            spec = EDGE_TYPES.get(etype)
            if spec is None:
                problems.append(f"unknown edge type {etype}")
                continue
            s, d = self.g.nodes.get(src), self.g.nodes.get(dst)
            if s is None or d is None:
                problems.append(f"{etype} edge to a missing node: {src} -> {dst}")
                continue
            if s["type"] not in spec["source"] or d["type"] not in spec["target"]:
                problems.append(f"{etype} not allowed {s['type']} -> {d['type']} ({src} -> {dst})")
        for nid, n in self.g.nodes.items():
            if n["type"] not in NODE_TYPES:
                problems.append(f"unknown node type {n['type']} on {nid}")
            elif not nid.startswith(NODE_TYPES[n["type"]]["prefix"] + ":"):
                problems.append(f"{nid} does not carry the {n['type']} prefix")
        return problems

    # =============================================================== BUILD
    def build(self, ownership_file: Optional[Path] = None, runtime: Optional[List[Path]] = None) -> Graph:
        t0 = time.time()
        py, md, other = self.discover()
        self.log(f"discovered {len(py)} Python, {len(md)} Markdown, {len(other)} other source files")
        self.pass_define(py)
        self.pass_imports()
        self.pass_classes()
        self.pass_ontology()
        self.pass_module_aliases()
        self.pass_bodies()
        self.pass_dispatch_tables()
        self.pass_flow()
        self.pass_other_sources(other)
        self.pass_polyglot(other)
        self.pass_documents(md)
        self.pass_derive()
        if runtime:
            self.load_observations(runtime)
        self.pass_runtime()
        self.pass_intent(ownership_file)
        for n in self.g.nodes.values():
            if n["type"] in ("Function", "Class") and not n.get("language"):
                n["language"] = "python"
        self.g.finalize()
        self.pass_hierarchy()
        self.g.finalize()
        self.coverage = self.build_coverage()
        self.log(f"built {len(self.g.nodes)} nodes and {len(self.g.edges)} edges in {time.time() - t0:.1f}s")
        return self.g


# ===========================================================================
# SECTION 7 -- WRITERS
# ===========================================================================

def git_commit(root: Path) -> Dict[str, str]:
    out = {}
    for key, args in (("commit", ["rev-parse", "HEAD"]), ("branch", ["rev-parse", "--abbrev-ref", "HEAD"])):
        try:
            out[key] = subprocess.run(["git", "-C", str(root)] + args, capture_output=True, text=True,
                                      timeout=20).stdout.strip()
        except Exception:
            out[key] = ""
    return out


def build_meta(b: Builder, g: Graph) -> Dict[str, Any]:
    by_node = Counter(n["type"] for n in g.nodes.values())
    by_edge = Counter(e["type"] for e in g.edges.values())
    git = git_commit(b.root)
    return {
        "title": "Aurora codebase knowledge graph",
        "authors": AUTHORS,
        "schema_version": SCHEMA_VERSION,
        "generator": "scripts/aurora_knowledge_graph.py",
        "generator_version": GENERATOR_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_commit": git.get("commit", ""),
        "source_branch": git.get("branch", ""),
        "content_hash": g.content_hash(),
        "static_content_hash": g.content_hash(include_observed=False),
        "runtime_scenarios": sorted({d.get("scenario", "") for d in b.observations}),
        "ownership_mapping": getattr(b, "ownership_meta", {}),
        "coverage": {"files": dict(b.coverage["files"]), "unresolved_internal_calls": b.coverage["unresolved_internal"],
                     "unresolved_reasons": dict(b.coverage["unresolved_reasons"]),
                     "observed_nodes": b.coverage["observed_nodes"],
                     "edge_basis": dict(b.coverage["edge_basis"]),
                     "claim_checks": dict(b.coverage["claim_checks"])},
        "node_count": len(g.nodes),
        "edge_count": len(g.edges),
        "node_types": dict(sorted(by_node.items())),
        "edge_types": dict(sorted(by_edge.items())),
        "noncomp_channels": b.ont.get("noncomp_channels"),
        "noncomp_interaction_slots": b.ont.get("noncomp_interaction_slots"),
        "warnings": b.warnings[:200],
    }


def write_json(path: Path, meta: Dict[str, Any], g: Graph) -> None:
    """Node-link JSON, one record per line so git diffs stay readable.
    Load with networkx: nx.node_link_graph(data, edges="edges")."""
    context = {"@vocab": "urn:aurora:kg:", "id": "@id", "type": "@type"}
    with path.open("w", encoding="utf-8") as fh:
        fh.write("{\n")
        fh.write(f'"@context": {json.dumps(context, sort_keys=True)},\n')
        fh.write(f'"meta": {json.dumps(meta, sort_keys=True, ensure_ascii=False)},\n')
        fh.write('"directed": true,\n"multigraph": false,\n"graph": {"name": "aurora"},\n')
        fh.write('"nodes": [\n')
        nodes = g.sorted_nodes()
        for i, n in enumerate(nodes):
            fh.write(json.dumps(n, sort_keys=True, ensure_ascii=False) + (",\n" if i < len(nodes) - 1 else "\n"))
        fh.write('],\n"edges": [\n')
        edges = g.sorted_edges()
        for i, e in enumerate(edges):
            fh.write(json.dumps(e, sort_keys=True, ensure_ascii=False) + (",\n" if i < len(edges) - 1 else "\n"))
        fh.write("]\n}\n")


def _graphml_type(values: List[Any]) -> str:
    kinds = {type(v) for v in values if v is not None}
    if kinds <= {bool}:
        return "boolean"
    if kinds <= {int}:
        return "long"
    if kinds <= {int, float}:
        return "double"
    return "string"


def _graphml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return safe_xml(json.dumps(v, ensure_ascii=False, sort_keys=True))
    return safe_xml(v)


def write_graphml(path: Path, meta: Dict[str, Any], g: Graph) -> None:
    nodes, edges = g.sorted_nodes(), g.sorted_edges()
    nkeys: Dict[str, List[Any]] = defaultdict(list)
    ekeys: Dict[str, List[Any]] = defaultdict(list)
    for n in nodes:
        for k, v in n.items():
            if k != "id":
                nkeys[k].append(v)
    for e in edges:
        for k, v in e.items():
            if k not in ("source", "target"):
                ekeys[k].append(v)
    with path.open("w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        fh.write(f"<!-- {xml_escape(meta['title'])}. Authors: {xml_escape(AUTHORS)}. "
                 f"commit {xml_escape(meta['source_commit'])} -->\n")
        for k in sorted(nkeys):
            fh.write(f'  <key id="n_{k}" for="node" attr.name="{k}" attr.type="{_graphml_type(nkeys[k])}"/>\n')
        for k in sorted(ekeys):
            fh.write(f'  <key id="e_{k}" for="edge" attr.name="{k}" attr.type="{_graphml_type(ekeys[k])}"/>\n')
        fh.write('  <graph id="aurora" edgedefault="directed">\n')
        for n in nodes:
            fh.write(f"    <node id={xml_quoteattr(n['id'])}>")
            for k in sorted(n):
                if k != "id" and n[k] is not None:
                    fh.write(f'<data key="n_{k}">{xml_escape(_graphml_value(n[k]))}</data>')
            fh.write("</node>\n")
        for i, e in enumerate(edges):
            fh.write(f"    <edge id=\"e{i}\" source={xml_quoteattr(e['source'])} target={xml_quoteattr(e['target'])}>")
            for k in sorted(e):
                if k not in ("source", "target") and e[k] is not None:
                    fh.write(f'<data key="e_{k}">{xml_escape(_graphml_value(e[k]))}</data>')
            fh.write("</edge>\n")
        fh.write("  </graph>\n</graphml>\n")


def write_jsonld(path: Path, meta: Dict[str, Any], g: Graph) -> None:
    context: Dict[str, Any] = {"@vocab": "urn:aurora:kg:", "id": "@id", "type": "@type"}
    for et in EDGE_TYPES:
        context[et] = {"@id": f"urn:aurora:kg:{et}", "@type": "@id"}
    out_edges = g.out_edges()
    with path.open("w", encoding="utf-8") as fh:
        fh.write("{\n")
        fh.write(f'"@context": {json.dumps(context, sort_keys=True)},\n')
        fh.write(f'"meta": {json.dumps(meta, sort_keys=True, ensure_ascii=False)},\n')
        fh.write('"@graph": [\n')
        nodes = g.sorted_nodes()
        for i, n in enumerate(nodes):
            rec = dict(n)
            grouped: Dict[str, List[str]] = defaultdict(list)
            for e in sorted(out_edges.get(n["id"], []), key=lambda x: (x["type"], x["target"])):
                grouped[e["type"]].append(e["target"])
            rec.update(grouped)
            fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + (",\n" if i < len(nodes) - 1 else "\n"))
        fh.write("]\n}\n")


def schema_document() -> Dict[str, Any]:
    return {"title": "Aurora knowledge graph schema", "authors": AUTHORS, "schema_version": SCHEMA_VERSION,
            "id_format": "<prefix>:<qualified name>, e.g. mod:aurora_internal.aurora_leverage_scalar, "
                         "fn:aurora.boot_aurora, store:aurora_oets_web.json",
            "edge_record": {"source": "node id", "target": "node id", "type": "edge type",
                            "weight": "times this relation was seen", "confidence": "0-1",
                            "provenance": "ast | regex | doc | ontology | filesystem | name",
                            "evidence": "up to 3 [path, line] pairs"},
            "node_types": NODE_TYPES, "edge_types": EDGE_TYPES}


def write_schema(path: Path) -> None:
    path.write_text(json.dumps(schema_document(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ summary
def _lift(g: Graph, b: Builder, nid: str) -> str:
    """Climb CONTAINS to the owning module (code) or return the node itself."""
    cur = nid
    while cur.startswith(("fn:", "cls:", "const:")):
        cur = b.parent_of.get(cur, cur)
        if cur == nid:
            break
    return cur


def write_summary(path: Path, meta: Dict[str, Any], g: Graph, b: Builder) -> None:
    nodes = g.nodes
    lines: List[str] = []
    w = lines.append
    w("# Aurora Knowledge Graph Summary")
    w(f"# Authors: {AUTHORS}")
    w("")
    w(f"Generated by `scripts/aurora_knowledge_graph.py` from commit `{meta['source_commit'][:12]}` "
      f"(branch `{meta['source_branch']}`). Content hash `{meta['content_hash'][:16]}`.")
    w("Regenerate with `python scripts/aurora_knowledge_graph.py build`; `check` fails when this is stale.")
    w("")
    w(f"**{meta['node_count']:,} nodes, {meta['edge_count']:,} edges.**")
    w("")
    w("| Node type | Count |")
    w("|---|---:|")
    for k, v in meta["node_types"].items():
        w(f"| {k} | {v:,} |")
    w("")
    w("| Edge type | Count |")
    w("|---|---:|")
    for k, v in meta["edge_types"].items():
        w(f"| {k} | {v:,} |")
    w("")
    out_e, in_e = g.out_edges(), g.in_edges()

    w("## 1. Layers")
    w("")
    w("| Layer | Name | Owned modules | Declared but missing |")
    w("|---|---|---:|---|")
    for layer in b.ont["layers"]:
        lid = "layer:" + layer["id"]
        owned = [e["source"] for e in in_e.get(lid, []) if e["type"] == "OWNED_BY"]
        missing = ", ".join(f"`{x}`" for x in nodes[lid].get("declared_missing", [])) or "none"
        w(f"| {layer['id']} | {layer['name']} | {len(owned)} | {missing} |")
    w("")

    def top(ntype: str, key: str, n: int = 15, role_skip: Tuple[str, ...] = ("test",)) -> List[Dict[str, Any]]:
        rows = [x for x in nodes.values() if x["type"] == ntype and x.get("role") not in role_skip]
        rows.sort(key=lambda x: (-x.get(key, 0), x["id"]))
        return rows[:n]

    w("## 2. Hubs")
    w("")
    w("Modules most imported by other modules:")
    w("")
    for x in top("Module", "imported_by"):
        w(f"- `{x['path']}`: imported by {x.get('imported_by', 0)} modules, {x.get('loc', 0):,} lines")
    w("")
    w("Functions with the most distinct callers:")
    w("")
    for x in top("Function", "fan_in"):
        w(f"- `{x.get('module', x.get('path', ''))}.{x['qualname']}`: {x.get('fan_in', 0)} callers")
    w("")

    w("## 3. Organs and the systems bus")
    w("")
    w("Slots, stores and variables that only tests touch are left out of the lists below.")
    w("")
    organs = [x for x in nodes.values() if x["type"] == "Organ" and not x.get("test_only")]
    bus = [x for x in nodes.values() if x["type"] == "BusChannel" and not x.get("test_only")]
    w(f"- Organs (`systems[\"key\"]`): **{len(organs)}**; with a resolved class: "
      f"**{sum(1 for o in organs if any(e['type'] == 'IMPLEMENTED_BY' for e in out_e.get(o['id'], [])))}**")
    w(f"- Bus slots (`systems[\"_key\"]`): **{len(bus)}**")
    wn = sorted(x["name"] for x in bus if x.get("writers") and not x.get("readers"))
    rn = sorted(x["name"] for x in bus if x.get("readers") and not x.get("writers"))
    w(f"- Written and never read: {len(wn)}" + (": " + ", ".join(f"`{k}`" for k in wn[:40]) if wn else ""))
    w(f"- Read and never written: {len(rn)}" + (": " + ", ".join(f"`{k}`" for k in rn[:40]) if rn else ""))
    unused = sorted(o["name"] for o in organs if o.get("registered_by") and not o.get("used_by"))
    w(f"- Organs registered and never read back by key: {len(unused)}"
      + (": " + ", ".join(f"`{k}`" for k in unused[:40]) if unused else ""))
    w("")

    w("## 4. Persisted state")
    w("")
    stores = [x for x in nodes.values() if x["type"] == "StateStore" and not x.get("test_only")]
    w(f"- Stores named in production code: **{len(stores)}**; listed in the persistence inventory: "
      f"**{sum(1 for s in stores if s.get('declared_in_inventory'))}**")
    wo = sorted(s["name"] for s in stores if s.get("writers") and not s.get("readers"))
    ro = sorted(s["name"] for s in stores if s.get("readers") and not s.get("writers"))
    w(f"- Written with no reader found: {len(wo)}" + (": " + ", ".join(f"`{k}`" for k in wo[:30]) if wo else ""))
    w(f"- Read with no writer found: {len(ro)}" + (": " + ", ".join(f"`{k}`" for k in ro[:30]) if ro else ""))
    multi = sorted(((s.get("writers", 0), s["name"]) for s in stores), reverse=True)[:10]
    w("- Stores with the most writers: " + ", ".join(f"`{n}` ({c})" for c, n in multi if c))
    w("")

    w("## 5. Doctrine")
    w("")
    rules = [x for x in nodes.values() if x["type"] == "DoctrineRule"]
    defined = [r for r in rules if r.get("defined")]
    ghosts = sorted(r["rule_id"] for r in rules if not r.get("defined"))
    idle = sorted(r["rule_id"] for r in defined
                  if not any(e["type"] == "GOVERNS" for e in out_e.get(r["id"], []))
                  and not any(e["type"] == "CITES" for e in in_e.get(r["id"], [])))
    w(f"- Registry entries: **{len(defined)}**; cited in code: "
      f"**{sum(1 for r in defined if any(e['type'] == 'CITES' for e in in_e.get(r['id'], [])))}**")
    w(f"- Cited in code but not defined in a registry file: {len(ghosts)}"
      + (": " + ", ".join(f"`{k}`" for k in ghosts[:40]) if ghosts else ""))
    w(f"- Defined but neither cited nor naming any code: {len(idle)}"
      + (": " + ", ".join(f"`{k}`" for k in idle[:40]) if idle else ""))
    w("")

    w("## 6. Constraint vocabulary in code")
    w("")
    for prefix, label in (("axis:", "Constraint axes"), ("istate:", "I-State pairs"), ("ncdim:", "Non-Comp dimensions")):
        cells = []
        for nid in sorted(k for k in nodes if k.startswith(prefix)):
            n_code = len({_lift(g, b, e["source"]) for e in in_e.get(nid, []) if e["type"] == "EXPRESSES"})
            cells.append(f"{nodes[nid]['name']} {n_code}")
        w(f"- {label} (modules carrying each): " + ", ".join(cells))
    nc_hit = sum(1 for k in nodes if k.startswith("nc:") and any(e["type"] == "EXPRESSES" for e in in_e.get(k, [])))
    w(f"- Non-Comps named in code: {nc_hit} of {meta.get('noncomp_channels')}")
    w("")

    w("## 7. Standing-rule compliance")
    w("")
    mods = [x for x in nodes.values() if x["type"] == "Module"]
    no_header = sorted(x["path"] for x in mods if not x.get("has_authorship_header") and x["role"] != "package_init")
    w(f"- Python modules without the authorship header: **{len(no_header)}** of {len(mods)}")
    for pth in no_header[:30]:
        w(f"  - `{pth}`")
    if len(no_header) > 30:
        w(f"  - and {len(no_header) - 30} more (query: `role` + `has_authorship_header` in aurora_kg.json)")
    unpref = sorted(x["path"] for x in mods if x["role"] in ("core", "internal") and not x.get("aurora_prefix"))
    w(f"- Core or internal modules without the `aurora_` prefix: **{len(unpref)}**"
      + (": " + ", ".join(f"`{k}`" for k in unpref[:30]) if unpref else ""))
    perr = sorted(f"`{x['path']}` ({x['parse_error']})" for x in mods if x.get("parse_error"))
    w(f"- Files Python cannot parse: {len(perr)}" + (": " + "; ".join(perr[:20]) if perr else ""))
    w("")

    w("### Boundary checks")
    w("")
    for bd in b.ont.get("boundaries", []):
        mod = bd["module"]
        public = set(bd.get("public", []))
        prod, tests = set(), set()
        for e in g.edges.values():
            src_mod = _lift(g, b, e["source"])
            if src_mod == "mod:" + mod:
                continue
            crossing = []
            if e["type"] in ("CALLS", "INSTANTIATES", "INHERITS", "OVERRIDES"):
                for pre in ("fn:", "cls:"):
                    if e["target"].startswith(f"{pre}{mod}."):
                        top_sym = e["target"][len(pre) + len(mod) + 1:].split(".")[0]
                        if top_sym not in public:
                            crossing.append(top_sym)
            elif e["type"] == "IMPORTS" and e["target"] == "mod:" + mod:
                crossing = [nm for nm in e.get("names", []) if nm not in public and nm != "*"]
            if crossing:
                role = nodes.get(src_mod, {}).get("role")
                (tests if role == "test" else prod).update(f"{src_mod[4:]} -> {c}" for c in crossing)
        status = "holds" if not prod else f"**{len(prod)} crossing(s)**"
        w(f"- {bd['rule']}: {status} in production code; {len(tests)} in tests.")
        for item in sorted(prod)[:30]:
            w(f"  - `{item}`")
    for fb in b.ont.get("forbidden_imports", []):
        hits = sorted({e["source"][4:] for e in g.edges.values() if e["type"] == "IMPORTS"
                       and (e["target"] in ("mod:" + fb["module"], "ext:" + fb["module"])
                            or fb["module"] in e.get("names", []))})
        w(f"- {fb['rule']}: import `{fb['use_instead']}`, never `{fb['module']}`: "
          + ("holds." if not hits else f"**{len(hits)} module(s)**: " + ", ".join(f"`{h}`" for h in hits[:20])))
    w("")

    w("## 8. Trim cross-check")
    w("")
    w("Heuristic: nothing in the repo names these, by import, call, attribute, string or launcher. "
      "Dynamic dispatch can hide a use, so treat them as leads, not verdicts.")
    w("")
    orph = sorted(x["path"] for x in mods if x.get("orphan_candidate"))
    unref = [x for x in nodes.values() if x["type"] == "Function" and x.get("unreferenced_candidate")]
    w(f"- Modules nothing imports or launches: **{len(orph)}**")
    for pth in orph[:40]:
        w(f"  - `{pth}`")
    if len(orph) > 40:
        w(f"  - and {len(orph) - 40} more")
    w(f"- Functions whose name appears nowhere else: **{len(unref)}** "
      f"({sum(x.get('loc', 0) for x in unref):,} lines)")
    by_mod = Counter(x.get("module", x.get("path", "")) for x in unref)
    for mname, c in by_mod.most_common(15):
        w(f"  - `{mname}`: {c}")
    w("")
    if b.warnings:
        w("## 9. Build warnings")
        w("")
        for msg in b.warnings[:50]:
            w(f"- {msg}")
        w("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------- html viewer
VIEW_TYPES = ["Module", "Layer", "StateStore", "Organ", "BusChannel", "DoctrineRule", "ConstraintAxis",
              "IStatePair", "NonComp", "Concept", "ExternalDependency", "SourceFile", "Document", "EnvVar"]
VIEW_EDGES = ["IMPORTS", "CALLS", "INSTANTIATES", "INHERITS", "READS", "WRITES", "REGISTERS", "USES_ORGAN",
              "IMPLEMENTED_BY", "OWNED_BY", "CITES", "GOVERNS", "EXPRESSES", "TESTS", "RUNS", "DOCUMENTS",
              "MAPS_TO", "COMPOSED_OF", "PRECEDES", "PART_OF"]


def view_projection(g: Graph, b: Builder) -> Dict[str, Any]:
    """Module-level projection: code nodes are lifted to their module, edges re-aggregated."""
    keep: Dict[str, int] = {}
    nodes_out: List[List[Any]] = []
    layer_of: Dict[str, str] = {}
    for e in g.edges.values():
        if e["type"] == "OWNED_BY":
            layer_of.setdefault(e["source"], e["target"].split(":", 1)[1])
    for n in g.sorted_nodes():
        if n["type"] not in VIEW_TYPES:
            continue
        if n["type"] == "ExternalDependency" and n.get("ecosystem") != "third_party":
            continue
        group = n["type"]
        if n["type"] == "Module":
            group = "test" if n.get("role") == "test" else n.get("role", "core")
        detail = {k: n[k] for k in ("path", "role", "loc", "docstring", "title", "category", "rule_id",
                                     "has_authorship_header", "orphan_candidate", "imported_by", "writers",
                                     "readers", "registered_by", "used_by", "language", "ecosystem", "kind")
                  if k in n and n[k] not in (None, "", [])}
        label = n.get("name", n["id"])
        if n["type"] == "DoctrineRule":
            label = n.get("rule_id", label)
        if n["type"] == "Document":
            label = n.get("path", label)
        keep[n["id"]] = len(nodes_out)
        size = n.get("loc", 0) if n["type"] == "Module" else 0
        nodes_out.append([n["id"], n["type"], label, group, size, layer_of.get(n["id"], ""), detail])
    agg: Dict[Tuple[int, int, int], int] = defaultdict(int)
    for e in g.edges.values():
        if e["type"] not in VIEW_EDGES:
            continue
        s, t = _lift(g, b, e["source"]), _lift(g, b, e["target"])
        if s == t or s not in keep or t not in keep:
            continue
        agg[(keep[s], keep[t], VIEW_EDGES.index(e["type"]))] += e["weight"]
    edges_out = [[s, t, k, w] for (s, t, k), w in sorted(agg.items())]
    return {"nodes": nodes_out, "edges": edges_out, "edgeTypes": VIEW_EDGES, "nodeTypes": VIEW_TYPES}


def write_html(path: Path, meta: Dict[str, Any], g: Graph, b: Builder) -> None:
    data = view_projection(g, b)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    info = json.dumps({"commit": meta["source_commit"][:12], "hash": meta["content_hash"][:16],
                       "nodes": meta["node_count"], "edges": meta["edge_count"]})
    path.write_text(HTML_TEMPLATE.replace("__DATA__", payload).replace("__META__", info), encoding="utf-8")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aurora Knowledge Graph</title>
<meta name="author" content="Sunni (Sir) Morningstar &amp; Cael Devo">
<style>
:root{--bg:#f7f7f5;--panel:#ffffff;--ink:#1d1d1b;--muted:#6b6b66;--line:#d9d9d4;--edge:rgba(60,60,60,.10);--hi:#d9480f}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#141413;--panel:#1e1e1c;--ink:#ecebe6;--muted:#9a9a93;--line:#33332f;--edge:rgba(220,220,210,.08);--hi:#ff8a4c}}
:root[data-theme="dark"]{--bg:#141413;--panel:#1e1e1c;--ink:#ecebe6;--muted:#9a9a93;--line:#33332f;--edge:rgba(220,220,210,.08);--hi:#ff8a4c}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:13px/1.4 system-ui,-apple-system,Segoe UI,sans-serif}
#app{display:flex;height:100%}#side{width:340px;max-width:92vw;border-right:1px solid var(--line);background:var(--panel);overflow:auto;padding:12px 14px}
#stage{flex:1;position:relative;min-width:0}canvas{display:block;width:100%;height:100%;cursor:grab}
h1{font-size:15px;margin:0 0 2px}small,.muted{color:var(--muted)}h2{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:14px 0 6px}
input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:4px 10px}.chips label{white-space:nowrap;cursor:pointer}.sw{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px;vertical-align:middle}
#results div,#detail a{cursor:pointer}#results div{padding:3px 0;border-bottom:1px solid var(--line)}#results div:hover,#detail a:hover{color:var(--hi)}
#detail a{display:block;padding:1px 0;color:var(--ink);text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kv{display:grid;grid-template-columns:auto 1fr;gap:2px 8px;word-break:break-all}#status{position:absolute;left:10px;bottom:8px;color:var(--muted)}
button{border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:6px;padding:4px 8px;cursor:pointer}
@media (max-width:700px){#app{flex-direction:column}#side{width:100%;max-width:none;height:45%;border-right:0;border-bottom:1px solid var(--line);padding:10px 16px}}
</style>
</head>
<body>
<div id="app">
<div id="side">
<h1>Aurora Knowledge Graph</h1>
<small>Sunni (Sir) Morningstar &amp; Cael Devo &middot; <span id="meta"></span></small>
<h2>Find</h2><input id="q" type="search" placeholder="module, store, organ, FIX-A..."><div id="results"></div>
<h2>Nodes</h2><div id="ntypes" class="chips"></div>
<h2>Edges</h2><div id="etypes" class="chips"></div>
<p><button id="reset">Reset view</button> <button id="relayout">Re-layout</button></p>
<div id="detail"></div>
</div>
<div id="stage"><canvas id="cv"></canvas><div id="status"></div></div>
</div>
<script>
const D=__DATA__, META=__META__;
const COLORS={core:"#3b6fd8",internal:"#7a4fd0",script:"#2f9e8f",tool:"#5b8f2f",app:"#a0722a",package_init:"#888",test:"#b5b5ad",
Layer:"#d9480f",StateStore:"#c92a6a",Organ:"#e67700",BusChannel:"#f2b705",DoctrineRule:"#c0392b",ConstraintAxis:"#0b7285",
IStatePair:"#1098ad",NonComp:"#66a80f",Concept:"#9c36b5",ExternalDependency:"#868e96",SourceFile:"#495057",Document:"#adb5bd",EnvVar:"#5c940d"};
const ON_T=new Set(["Module","Layer","StateStore","Organ","BusChannel","DoctrineRule","ConstraintAxis","Concept"]);
const ON_E=new Set(["IMPORTS","READS","WRITES","REGISTERS","USES_ORGAN","IMPLEMENTED_BY","OWNED_BY","GOVERNS","CITES","EXPRESSES","PRECEDES"]);
let showTests=false;
const N=D.nodes.map((a,i)=>({i,id:a[0],type:a[1],label:a[2],group:a[3],size:a[4],layer:a[5],d:a[6],x:0,y:0,vx:0,vy:0}));
const E=D.edges.map(a=>({s:a[0],t:a[1],k:a[2],w:a[3]}));
const OUT=N.map(()=>[]),IN=N.map(()=>[]);E.forEach(e=>{OUT[e.s].push(e);IN[e.t].push(e)});
document.getElementById("meta").textContent=`commit ${META.commit} · ${META.nodes.toLocaleString()} nodes · ${META.edges.toLocaleString()} edges`;
const cv=document.getElementById("cv"),ctx=cv.getContext("2d");let W=0,H=0,dpr=1;
let view={x:0,y:0,k:.6},sel=null,alpha=1,ticks=0;
function color(n){return COLORS[n.group]||COLORS[n.type]||"#999"}
function radius(n){if(n.type==="Module")return 2.5+Math.min(9,Math.sqrt(n.size||1)/9);if(n.type==="Layer")return 10;if(n.type==="ConstraintAxis")return 8;return 3.5}
function visible(n){if(!ON_T.has(n.type))return false;if(n.group==="test"&&!showTests)return false;return true}
function visEdges(){return E.filter(e=>ON_E.has(D.edgeTypes[e.k])&&visible(N[e.s])&&visible(N[e.t]))}
let VE=[];
function seed(){const groups=[...new Set(N.map(n=>n.layer||n.group))];N.forEach((n,i)=>{const gi=groups.indexOf(n.layer||n.group),a=2*Math.PI*gi/groups.length,r=380+((i*7919)%200);n.x=Math.cos(a)*r+((i*31)%60)-30;n.y=Math.sin(a)*r+((i*17)%60)-30;n.vx=n.vy=0});alpha=1;ticks=0}
function tick(){const vs=N.filter(visible),cell=48,grid=new Map();
for(const n of vs){const key=((n.x/cell)|0)+","+((n.y/cell)|0);let b=grid.get(key);if(!b)grid.set(key,b=[]);b.push(n)}
for(const n of vs){const cx=(n.x/cell)|0,cy=(n.y/cell)|0;for(let dx=-2;dx<=2;dx++)for(let dy=-2;dy<=2;dy++){const b=grid.get((cx+dx)+","+(cy+dy));if(!b)continue;for(const m of b){if(m===n)continue;let x=n.x-m.x,y=n.y-m.y,d2=x*x+y*y+.01;if(d2>cell*cell*4)continue;const f=60*alpha/d2;n.vx+=x*f;n.vy+=y*f}}}
for(const e of VE){const a=N[e.s],b=N[e.t];let x=b.x-a.x,y=b.y-a.y,d=Math.sqrt(x*x+y*y)+.01;const tgt=D.edgeTypes[e.k]==="OWNED_BY"?60:110,f=(d-tgt)/d*.02*alpha*Math.min(3,1+Math.log(e.w));a.vx+=x*f;a.vy+=y*f;b.vx-=x*f;b.vy-=y*f}
for(const n of vs){n.vx-=n.x*.0009*alpha;n.vy-=n.y*.0009*alpha;n.vx*=.82;n.vy*=.82;n.x+=n.vx;n.y+=n.vy}
alpha=Math.max(.02,alpha*.992);ticks++}
function resize(){dpr=window.devicePixelRatio||1;W=cv.clientWidth;H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;draw()}
function toScreen(n){return[(n.x-view.x)*view.k+W/2,(n.y-view.y)*view.k+H/2]}
function draw(){ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);const css=getComputedStyle(document.documentElement);
const edgeCol=css.getPropertyValue("--edge"),hi=css.getPropertyValue("--hi"),ink=css.getPropertyValue("--ink");
const nb=new Set();if(sel!==null){nb.add(sel);OUT[sel].forEach(e=>nb.add(e.t));IN[sel].forEach(e=>nb.add(e.s))}
ctx.lineWidth=1;for(const e of VE){const a=N[e.s],b=N[e.t];const on=sel!==null&&(e.s===sel||e.t===sel);if(sel!==null&&!on)continue;
const[x1,y1]=toScreen(a),[x2,y2]=toScreen(b);ctx.strokeStyle=on?hi:edgeCol;ctx.globalAlpha=on?.7:1;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke()}
ctx.globalAlpha=1;if(sel===null){ctx.strokeStyle=edgeCol;for(const e of VE){}}
for(const n of N){if(!visible(n))continue;const[x,y]=toScreen(n);if(x<-20||y<-20||x>W+20||y>H+20)continue;const r=radius(n)*Math.max(.6,Math.sqrt(view.k));
ctx.globalAlpha=sel===null||nb.has(n.i)?1:.15;ctx.fillStyle=color(n);ctx.beginPath();ctx.arc(x,y,r,0,7);ctx.fill();
if(n.i===sel){ctx.strokeStyle=hi;ctx.lineWidth=2;ctx.stroke()}
if((sel!==null&&nb.has(n.i))||n.type==="Layer"||n.type==="ConstraintAxis"||view.k>1.6){ctx.fillStyle=ink;ctx.font="11px system-ui";ctx.fillText(n.label.length>40?n.label.slice(0,39)+"…":n.label,x+r+2,y+3)}}
ctx.globalAlpha=1;document.getElementById("status").textContent=alpha>.03?`settling… ${ticks}`:""}
function loop(){if(alpha>.03){for(let i=0;i<3;i++)tick();draw()}requestAnimationFrame(loop)}
function pick(mx,my){let best=null,bd=1e9;for(const n of N){if(!visible(n))continue;const[x,y]=toScreen(n),d=(x-mx)**2+(y-my)**2,r=radius(n)+5;if(d<r*r&&d<bd){bd=d;best=n.i}}return best}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function select(i,center){sel=i;if(i===null){document.getElementById("detail").innerHTML="";draw();return}const n=N[i];
if(center){view.x=n.x;view.y=n.y;view.k=Math.max(view.k,1.2)}
let h=`<h2>${esc(n.type)}</h2><div><b>${esc(n.label)}</b></div><div class="muted">${esc(n.id)}</div><div class="kv">`;
for(const[k,v]of Object.entries(n.d||{}))h+=`<span class="muted">${esc(k)}</span><span>${esc(v)}</span>`;h+="</div>";
const groups={};OUT[i].forEach(e=>{(groups["→ "+D.edgeTypes[e.k]]??=[]).push([e.t,e.w])});IN[i].forEach(e=>{(groups["← "+D.edgeTypes[e.k]]??=[]).push([e.s,e.w])});
for(const[g,list]of Object.entries(groups).sort()){list.sort((a,b)=>b[1]-a[1]);h+=`<h2>${esc(g)} (${list.length})</h2>`;
for(const[j,w]of list.slice(0,60))h+=`<a data-i="${j}">${esc(N[j].label)} <span class="muted">${w>1?"×"+w:""}</span></a>`;if(list.length>60)h+=`<div class="muted">and ${list.length-60} more</div>`}
const el=document.getElementById("detail");el.innerHTML=h;el.querySelectorAll("a").forEach(a=>a.onclick=()=>{const j=+a.dataset.i;const t=N[j];if(!visible(t)){ON_T.add(t.type);if(t.group==="test")showTests=true;buildFilters();VE=visEdges()}select(j,true)});draw()}
function buildFilters(){const nt=document.getElementById("ntypes");nt.innerHTML="";
for(const t of D.nodeTypes){const c=N.filter(n=>n.type===t).length;if(!c)continue;const l=document.createElement("label");l.innerHTML=`<input type="checkbox" ${ON_T.has(t)?"checked":""}><span class="sw" style="background:${COLORS[t]||COLORS.core}"></span>${t} <span class="muted">${c}</span>`;l.querySelector("input").onchange=ev=>{ev.target.checked?ON_T.add(t):ON_T.delete(t);VE=visEdges();alpha=Math.max(alpha,.3);draw()};nt.appendChild(l)}
const tl=document.createElement("label");tl.innerHTML=`<input type="checkbox" ${showTests?"checked":""}><span class="sw" style="background:${COLORS.test}"></span>Test modules`;tl.querySelector("input").onchange=ev=>{showTests=ev.target.checked;VE=visEdges();alpha=Math.max(alpha,.3);draw()};nt.appendChild(tl);
const et=document.getElementById("etypes");et.innerHTML="";const counts={};E.forEach(e=>counts[e.k]=(counts[e.k]||0)+1);
D.edgeTypes.forEach((t,k)=>{if(!counts[k])return;const l=document.createElement("label");l.innerHTML=`<input type="checkbox" ${ON_E.has(t)?"checked":""}>${t} <span class="muted">${counts[k]}</span>`;l.querySelector("input").onchange=ev=>{ev.target.checked?ON_E.add(t):ON_E.delete(t);VE=visEdges();alpha=Math.max(alpha,.3);draw()};et.appendChild(l)})}
document.getElementById("q").oninput=ev=>{const q=ev.target.value.trim().toLowerCase(),r=document.getElementById("results");r.innerHTML="";if(q.length<2)return;
const hits=N.filter(n=>n.label.toLowerCase().includes(q)||n.id.toLowerCase().includes(q)).slice(0,30);
for(const n of hits){const d=document.createElement("div");d.innerHTML=`<span class="sw" style="background:${color(n)}"></span>${esc(n.label)} <span class="muted">${esc(n.type)}</span>`;d.onclick=()=>{if(!visible(n)){ON_T.add(n.type);if(n.group==="test")showTests=true;buildFilters();VE=visEdges()}select(n.i,true)};r.appendChild(d)}};
let drag=null;cv.onmousedown=ev=>{drag={x:ev.clientX,y:ev.clientY,vx:view.x,vy:view.y,moved:false}};
window.onmousemove=ev=>{if(!drag)return;const dx=ev.clientX-drag.x,dy=ev.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>3)drag.moved=true;view.x=drag.vx-dx/view.k;view.y=drag.vy-dy/view.k;draw()};
window.onmouseup=ev=>{if(drag&&!drag.moved){const r=cv.getBoundingClientRect();select(pick(ev.clientX-r.left,ev.clientY-r.top),false)}drag=null};
cv.onwheel=ev=>{ev.preventDefault();const f=Math.exp(-ev.deltaY*.0015);view.k=Math.min(8,Math.max(.05,view.k*f));draw()};
let touch=null;cv.ontouchstart=ev=>{const t=ev.touches[0];touch={x:t.clientX,y:t.clientY,vx:view.x,vy:view.y,moved:false}};
cv.ontouchmove=ev=>{if(!touch)return;ev.preventDefault();const t=ev.touches[0],dx=t.clientX-touch.x,dy=t.clientY-touch.y;if(Math.abs(dx)+Math.abs(dy)>4)touch.moved=true;view.x=touch.vx-dx/view.k;view.y=touch.vy-dy/view.k;draw()};
cv.ontouchend=ev=>{if(touch&&!touch.moved){const r=cv.getBoundingClientRect();select(pick(touch.x-r.left,touch.y-r.top),false)}touch=null};
document.getElementById("reset").onclick=()=>{view={x:0,y:0,k:.6};select(null)};document.getElementById("relayout").onclick=()=>{seed();VE=visEdges()};
window.onresize=resize;buildFilters();VE=visEdges();seed();resize();loop();
</script>
</body>
</html>
"""


# ===========================================================================
# SECTION 8 -- QUERIES
# ===========================================================================

def run_query(args: argparse.Namespace) -> int:
    data = load_graph(Path(args.graph))
    nodes = {n["id"]: n for n in data["nodes"]}
    out_e: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    in_e: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in data["edges"]:
        out_e[e["source"]].append(e)
        in_e[e["target"]].append(e)
    if args.find:
        q = args.find.lower()
        hits = [n for n in data["nodes"] if q in n["id"].lower() or q in str(n.get("name", "")).lower()]
        for n in hits[:80]:
            print(f"{n['id']:<80} {n['type']}")
        print(f"{len(hits)} match(es)")
        return 0
    if args.node:
        n = nodes.get(args.node)
        if n is None:
            print(f"no node {args.node}; try --find", file=sys.stderr)
            return 1
        print(json.dumps(n, indent=2, ensure_ascii=False))
        for label, coll, key in (("out", out_e, "target"), ("in", in_e, "source")):
            grouped: Dict[str, List[str]] = defaultdict(list)
            for e in coll.get(args.node, []):
                grouped[e["type"]].append(f"{e[key]} (x{e['weight']})")
            for t in sorted(grouped):
                print(f"\n[{label}] {t} ({len(grouped[t])})")
                for item in sorted(grouped[t])[:200]:
                    print(f"  {item}")
        return 0
    if args.impact:
        start = args.impact
        if start not in nodes:
            print(f"no node {start}", file=sys.stderr)
            return 1
        reverse_types = {"IMPORTS", "CALLS", "INSTANTIATES", "INHERITS", "USES_ORGAN", "READS", "TESTS", "RUNS"}
        reverse_types |= {"FEEDS", "SUBSCRIBES", "HANDLES", "SPAWNS", "PASSES_CALLBACK", "INVOKES"}
        seen = {start}
        q = deque([(start, 0)])
        depth_of = {start: 0}
        conf_of = {start: 1.0}
        basis_of: Dict[str, Set[str]] = {start: set()}
        while q:
            cur, d = q.popleft()
            if d >= args.depth:
                continue
            targets = [cur]
            # a module's impact includes everything that uses anything it contains
            targets += [e["target"] for e in out_e.get(cur, []) if e["type"] == "CONTAINS"]
            for t in targets:
                for e in in_e.get(t, []):
                    if e["type"] in reverse_types and e["source"] not in seen:
                        seen.add(e["source"])
                        depth_of[e["source"]] = d + 1
                        conf_of[e["source"]] = min(conf_of[cur], float(e.get("confidence", 1.0)))
                        basis_of[e["source"]] = basis_of[cur] | set(e.get("basis", []))
                        q.append((e["source"], d + 1))
        mods = sorted({s.split(":", 1)[1].rsplit(".", 1)[0] if not s.startswith("mod:") else s[4:]
                       for s in seen if s != start and s.split(":", 1)[0] in ("mod", "fn", "cls")})
        print(f"{len(seen) - 1} potential dependents of {start} within depth {args.depth}.")
        print("A potential dependent has a static or observed path to the node; it is not a prediction that a "
              "change breaks it.")
        for s in sorted(seen - {start}, key=lambda x: (depth_of[x], -conf_of[x], x))[:400]:
            print(f"  d{depth_of[s]} c{conf_of[s]:.1f} [{'+'.join(sorted(basis_of[s]))}] {s}")
        print(f"\nmodules touched: {len(mods)}")
        return 0
    if args.path:
        a, z = args.path
        prev = {a: None}
        q = deque([a])
        while q:
            cur = q.popleft()
            if cur == z:
                break
            for e in out_e.get(cur, []):
                if e["target"] not in prev:
                    prev[e["target"]] = (cur, e["type"])
                    q.append(e["target"])
        if z not in prev:
            print("no directed path")
            return 1
        chain = []
        cur = z
        while prev[cur] is not None:
            p, t = prev[cur]
            chain.append(f"{p} -[{t}]-> {cur}")
            cur = p
        print("\n".join(reversed(chain)))
        return 0
    print("give one of --find, --node, --impact, --path", file=sys.stderr)
    return 2


# ===========================================================================
# SECTION 8b -- SHARDED OUTPUT, LOADING, TRACE, INVESTIGATE, DIFF
# ===========================================================================

def _jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
            n += 1
    return n


def write_sharded(out: Path, meta: Dict[str, Any], g: Graph, b: "Builder") -> List[str]:
    """graph/meta.json, graph/nodes.jsonl, graph/edges/<TYPE>.jsonl, evidence/<TYPE>.jsonl (every site of
    edges with more than EVIDENCE_CAP), coverage/*.  One record per line, sorted, so git diffs stay readable."""
    written: List[str] = []
    gd, ed, evd, cov = out / "graph", out / "graph" / "edges", out / "evidence", out / "coverage"
    for d in (gd, ed, evd, cov):
        d.mkdir(parents=True, exist_ok=True)
    for d in (ed, evd):
        for old in d.glob("*.jsonl"):      # generated files only: each build rewrites the whole set
            old.unlink()
    (gd / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append("graph/meta.json")
    _jsonl(gd / "nodes.jsonl", g.sorted_nodes())
    written.append("graph/nodes.jsonl")
    by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in g.sorted_edges():
        by_type[e["type"]].append(e)
    for et, rows in sorted(by_type.items()):
        _jsonl(ed / f"{et}.jsonl", rows)
        full = [{"source": e["source"], "target": e["target"],
                 "sites": g.full_evidence((e["source"], e["type"], e["target"]))}
                for e in rows if e.get("evidence_count", 0) > EVIDENCE_CAP]
        if full:
            _jsonl(evd / f"{et}.jsonl", full)
    written.append(f"graph/edges/ ({len(by_type)} files)")
    written.append("evidence/")
    _jsonl(cov / "files.jsonl", ({"path": p, "status": st} for p, st in sorted(b.file_inventory.items())))
    # every call site whose target is unknown inside Aurora's own code; library calls and calls on built-in
    # values are counted per owner instead (they are not gaps in Aurora's dispatch)
    _jsonl(cov / "unresolved_calls.jsonl",
           ({"owner": o, "path": p, "line": ln, "expr": ex, "reason": r, "organ": extra or None}
            for o, p, ln, ex, r, extra in sorted(b.unresolved_sites) if r not in ("external", "builtin_value")))
    outside: Dict[str, Counter] = defaultdict(Counter)
    for o, p, ln, ex, r, extra in b.unresolved_sites:
        if r in ("external", "builtin_value"):
            outside[o][r] += 1
            if DIAG_EXPR_RE.match(ex):
                outside[o]["logging"] += 1
    _jsonl(cov / "library_calls.jsonl", ({"owner": o, **dict(c)} for o, c in sorted(outside.items())))
    c = b.coverage
    claims = {"ownership": c["ownership"], "disagreements": c["claim_disagreements"],
              "claimed_paths_missing": c["claims_missing"],
              "checks": {k: v for k, v in sorted(getattr(b, "claim_checks", {}).items())}}
    (cov / "claims.json").write_text(json.dumps(claims, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (cov / "composites.json").write_text(json.dumps(
        {"note": "Composites are promoted from base units on graph evidence only; nothing here is declared. "
                 "binding counts implemented or observed edges between members; cohesion is internal / (internal + "
                 "external) binding.  declared_composites holds each composite the ownership mapping declares "
                 "(import-derived there) with the binding the graph sees on its links; import_only means no call, "
                 "flow, spawn or shared state joins its files.  cross_domain lists file pairs in different domains "
                 "joined by implemented or observed edges or by meeting at one endpoint.",
         "composites": getattr(b, "composites", []),
         "declared_composites": getattr(b, "declared_composite_checks", []),
         "cross_domain": getattr(b, "cross_domain", [])}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    (cov / "unobserved.json").write_text(json.dumps(
        {"scenarios_recorded": c["scenarios_recorded"],
         "note": "Functions reachable by static edges from the desktop entry points that no recorded run entered. "
                 "Unobserved means not seen in these scenarios, not dead.",
         "functions": c["unobserved_reachable_desktop"]}, indent=1) + "\n", encoding="utf-8")
    write_coverage_md(cov / "COVERAGE.md", meta, g, b)
    write_subsystems_md(out / "SUBSYSTEMS.md", meta, g, b)
    written += ["coverage/", "SUBSYSTEMS.md"]
    return written


def write_coverage_md(path: Path, meta: Dict[str, Any], g: Graph, b: "Builder") -> None:
    c = b.coverage
    L: List[str] = []
    L.append("# What the knowledge graph covers, and what it does not")
    L.append("")
    L.append(f"Authors: {AUTHORS}  ")
    L.append(f"Source commit `{meta.get('source_commit', '')[:12]}`, generator {GENERATOR_VERSION}.")
    L.append("")
    L.append("Nothing here is hidden by a summary: every unresolved call site is in `unresolved_calls.jsonl`, every "
             "file's status in `files.jsonl`, every claim check in `claims.json`, and every statically reachable "
             "function that no recorded run entered in `unobserved.json`.")
    L.append("")
    L.append("## Files")
    L.append("")
    L.append("| status | files | meaning |")
    L.append("|---|---:|---|")
    meaning = {"parsed_ast": "Python, parsed with ast: calls, state, flow", "parse_failed": "Python that did not parse",
               "parsed_regex": "Rust, Dart, Kotlin, Java: read with patterns, calls matched by name",
               "scanned_launches": "shell, workflows, service units, web: only the modules and scripts they launch",
               "scanned_references": "Markdown: the code, stores and organs it names",
               "not_analysed": "data, config, images and other files: listed, not read"}
    for st, n in sorted(c["files"].items(), key=lambda kv: -kv[1]):
        L.append(f"| {st} | {n} | {meaning.get(st, '')} |")
    L.append("")
    L.append("## Calls without a resolved target")
    L.append("")
    L.append(f"{c['unresolved_internal']} method calls inside Aurora's code have no static target. External library "
             f"calls and calls on built-in values are listed with their reason but not counted as gaps.")
    L.append("")
    L.append("| reason | sites | what would resolve it |")
    L.append("|---|---:|---|")
    fixes = {"untyped_local": "a type the code does not state (assignment from an untyped call)",
             "builtin_value": "nothing: str, dict, list and similar",
             "external": "nothing: a library outside the repo",
             "dynamic_receiver": "the result of a call or subscript; runtime evidence",
             "untyped_attribute": "self.x whose class is never stated; an annotation or runtime evidence",
             "untyped_module_state": "a module global whose type is not stated",
             "unknown_member": "a name the target class or module does not define (dynamic or inherited from outside)",
             "untyped_parameter": "a parameter without an annotation",
             "organ_receiver": "systems[key] where the organ has no single implementing class"}
    for r, n in c["unresolved_reasons"].most_common():
        L.append(f"| {r} | {n} | {fixes.get(r, '')} |")
    L.append("")
    L.append("## Edge basis")
    L.append("")
    L.append("Every edge says how it is known. implemented: read from code. declared: stated in a document, the "
             "ownership mapping or the ontology. inferred: a grouping or a name match. observed: a recorded run took it.")
    L.append("")
    L.append("| basis | edges |")
    L.append("|---|---:|")
    for k, n in c["edge_basis"].most_common():
        L.append(f"| {k or '(none)'} | {n} |")
    L.append("")
    L.append("## Runtime evidence")
    L.append("")
    if c["scenarios_recorded"]:
        L.append(f"Recorded scenarios: {', '.join(c['scenarios_recorded'])}. {c['observed_nodes']} nodes were observed. "
                 f"{len(c['unobserved_reachable_desktop'])} functions are statically reachable from the desktop entry "
                 f"points but were not entered in any recorded run.")
        for doc in b.observations:
            line = f"- `{doc.get('scenario')}`: entry `{doc.get('entry')}`, completed {doc.get('completed')}, " \
                   f"{len(doc.get('calls', []))} call pairs, {doc.get('duration_s')} s"
            if doc.get("boot_stages"):
                line += f", last boot stage `{doc['boot_stages'][-1][1]}`"
            L.append(line)
    else:
        L.append("No runtime recording was given to this build, so no edge is observed. Run "
                 "`scripts/aurora_kg_observe.py` and rebuild with `--runtime`.")
    L.append("")
    L.append("Paths no recording covers: the phone runtime past the boot stages listed, the ACM kernel (bare metal), "
             "Praxis's own server, and any code that only runs on a timer longer than the recording.")
    L.append("")
    L.append("## Declared ownership and its boundary")
    L.append("")
    own = c["ownership"]
    if own.get("path"):
        L.append(f"Layer and category come from `{own['path']}` ({own.get('schema')}, sha256 {own.get('sha256')}). "
                 f"They are claims, kept apart from what the code and the runs show.")
        L.append("")
        L.append(f"> {own.get('scope', '')}")
        L.append("")
        L.append("Not covered by the mapping:")
        for nc in own.get("not_covered", []):
            L.append(f"- `{nc.get('path')}`: {nc.get('what')}")
        L.append("")
        L.append(f"Claim checks: " + ", ".join(f"{k} {v}" for k, v in sorted(c["claim_checks"].items())) + ".")
        if c["claim_disagreements"]:
            L.append("")
            L.append(f"{len(c['claim_disagreements'])} layer anchor(s) of the ontology are placed differently "
                     f"by the mapping:")
            for d in c["claim_disagreements"][:40]:
                L.append(f"- `{d['module']}`: ontology {d['anchor_layer']}, mapping {d['mapping_layer']}")
        if c["claims_missing"]:
            L.append("")
            L.append(f"{len(c['claims_missing'])} mapped path(s) have no module in the tree: "
                     + ", ".join(f"`{x}`" for x in c["claims_missing"][:20]))
    else:
        L.append(own.get("note", "No ownership mapping."))
    L.append("")
    L.append("## Reading impact")
    L.append("")
    L.append("`query --impact` lists potential dependents: code with a static or observed path to the node. It is "
             "not a prediction that a change breaks them. Each dependent carries the lowest confidence and the basis "
             "on its path.")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def write_subsystems_md(path: Path, meta: Dict[str, Any], g: Graph, b: "Builder") -> None:
    """The crystal ladder as the graph holds it: king quasi, quasi domains, higher-order subsystems, composites and
    base files.  Declared parts (domains, subsystems, the mapping's composites) are claims; evidence composites and
    every check below come from implemented code and recorded runs."""
    members: Dict[str, List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)
    part_of: Dict[str, List[str]] = defaultdict(list)
    for e in g.edges.values():
        if e["type"] == "MEMBER_OF":
            members[e["target"]].append((e["source"], e))
        if e["type"] == "PART_OF" and e["source"].startswith("subsys:"):
            part_of[e["target"]].append(e["source"])
    checks = getattr(b, "claim_checks", {})
    L = ["# Aurora's crystal ladder: declared responsibility against implemented and observed behaviour", "",
         f"Authors: {AUTHORS}  ", f"Source commit `{meta.get('source_commit', '')[:12]}`.  "
         f"Ownership mapping: `{(meta.get('ownership_mapping') or {}).get('path')}` "
         f"(schema `{(meta.get('ownership_mapping') or {}).get('schema')}`).", "",
         "The repository is the king quasi. Each domain is a quasi, each declared subsystem a higher-order unit, and "
         "every file a base unit. Domains and subsystems are claims from the ownership mapping. A composite is "
         "promoted only when the graph shows its files bound by calls, instantiation, inheritance, spawns, callbacks, "
         "value flow or shared state; the mapping's own composites (built from imports) are listed beside them with "
         "how much of that binding their links carry. A conflict means the evidence points beyond the declared "
         "subsystem; it is a question to review, not a correction.", ""]
    king = "subsys:king:aurora"
    L.append(f"## {g.nodes.get(king, {}).get('name', 'Aurora repository')} (king quasi)")
    L.append("")
    ev_comp = {c["id"]: c for c in getattr(b, "composites", [])}
    decl = {c["id"]: c for c in getattr(b, "declared_composite_checks", [])}
    for q in sorted(part_of.get(king, [])):
        qn = g.nodes[q]
        L.append(f"### Quasi: {qn.get('name')} (`{q}`), {len(members.get(q, []))} base file(s)")
        if qn.get("holds"):
            L += ["", f"Declared: {qn['holds']}"]
        L.append("")
        for h in sorted(part_of.get(q, []), key=lambda x: (g.nodes[x].get("kind") != "category", x)):
            hn = g.nodes[h]
            mem = [(m, e) for m, e in members.get(h, []) if "declared_composite" not in (e.get("method") or [])]
            L.append(f"#### Higher order: {hn.get('name')} (`{h}`), {len(mem)} member(s)"
                     + (" (grouped by path, inferred)" if hn.get("kind") == "area" else ""))
            if hn.get("holds"):
                L += ["", f"Declared: {hn['holds']}"]
            if hn.get("members_in_other_domains"):
                L += ["", f"Members placed in other domains: {hn['members_in_other_domains']}"]
            L.append("")
            comps = sorted(part_of.get(h, []))
            for c in comps:
                if c in ev_comp:
                    ec = ev_comp[c]
                    L.append(f"- Evidence composite `{c}`: {len(ec['members'])} files, cohesion {ec['cohesion']}, "
                             f"binding {ec['binding']}. Files: " + ", ".join(f"`{m}`" for m in ec["members"][:12])
                             + (" ..." if len(ec["members"]) > 12 else ""))
            for c in comps:
                cid = c.split(":", 2)[-1]
                if c.startswith("subsys:declared:") and cid in decl:
                    dc = decl[cid]
                    L.append(f"- Declared composite `{cid}` (hub `{dc['hub']}`): {len(dc['members'])} files, "
                             f"{dc['links_with_binding']} of {dc['declared_links']} import links carry binding, "
                             f"status {dc['status']}, closest evidence composite "
                             f"{('`' + dc['best_evidence_composite'] + '` (overlap ' + str(dc['jaccard']) + ')') if dc['best_evidence_composite'] else 'none'}.")
            if comps:
                L.append("")
            if hn.get("kind") == "area":
                L.append(", ".join(f"`{g.nodes[m].get('path', m)}`" for m, _ in sorted(mem)[:60])
                         + (" ..." if len(mem) > 60 else ""))
                L.append("")
                continue
            if not mem:
                continue
            L.append("| base file | claim basis | reached from | ran in | organs | store writes | check |")
            L.append("|---|---|---|---|---|---:|---|")
            for mid, e in sorted(mem, key=lambda x: g.nodes.get(x[0], {}).get("path", x[0])):
                n = g.nodes.get(mid, {})
                ev = n.get("evidence_profile", {})
                chk = checks.get(mid, {})
                role = " (also)" if "declared_also" in (e.get("method") or []) else ""
                L.append(f"| `{n.get('path', mid)}`{role} | {e.get('claim_basis') or (n.get('claim') or {}).get('basis', '')} | "
                         f"{', '.join(ev.get('reachable_from', [])) or '-'} | {', '.join(ev.get('observed_in', [])) or '-'} | "
                         f"{', '.join(ev.get('organs', [])[:3]) or '-'} | {ev.get('store_writes', 0)} | "
                         f"{chk.get('status', '-')}{': ' + '; '.join(chk['notes']) if chk.get('notes') else ''} |")
            L.append("")
    cross = getattr(b, "cross_domain", [])
    cands = [c for c in getattr(b, "declared_composite_checks", []) if c.get("candidate")]
    if cands:
        L += ["## Composite candidates the record holds back", "",
              "The record lists these as candidates, not composites, and their files stay base files. Each is checked "
              "here like a declared composite, so a candidate whose links gain binding can be promoted.", ""]
        for dc in cands:
            L.append(f"- `{dc['id']}` ({dc['domain']}, {dc['subsystem']}): {len(dc['members'])} files, "
                     f"{dc['links_with_binding']} of {dc['declared_links']} import links carry binding, "
                     f"status {dc['status']}.")
        L.append("")
    L += ["## Links across domains", "",
          f"{len(cross)} file pairs in different domains are joined by implemented or observed edges, or meet at one "
          "endpoint (method channel, Chaquopy call, HTTP route, frame). The 40 strongest:", "",
          "| file | file | domains | joined by |", "|---|---|---|---|"]
    for x in cross[:40]:
        L.append(f"| `{x['files'][0]}` | `{x['files'][1]}` | {' / '.join(str(d) for d in x['domains'])} | "
                 f"{', '.join(f'{k} {v}' for k, v in sorted(x['kinds'].items()))} |")
    L.append("")
    L += ["## Layers and organs", "",
          "Layers are declared in the ownership mapping; organ groupings come from the code's own implementation "
          "registry. Both are listed in `graph/nodes.jsonl` with their members in `graph/edges/MEMBER_OF.jsonl`.", ""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


class GraphView:
    """A loaded graph with indexes, for query, trace, investigate and diff."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.meta = data.get("meta", {})
        self.nodes: Dict[str, Dict[str, Any]] = {n["id"]: n for n in data["nodes"]}
        self.edges: List[Dict[str, Any]] = data["edges"]
        self.out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.inn: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for e in self.edges:
            self.out[e["source"]].append(e)
            self.inn[e["target"]].append(e)
            self.key[(e["source"], e["type"], e["target"])] = e
        self.base = data.get("_dir")

    def parent(self, nid: str) -> Optional[str]:
        for e in self.inn.get(nid, ()):
            if e["type"] == "CONTAINS":
                return e["source"]
        return None

    def module_of(self, nid: str) -> Optional[str]:
        cur, hops = nid, 0
        while cur and not cur.startswith(("mod:", "src:")) and hops < 12:
            cur = self.parent(cur)
            hops += 1
        return cur

    def evidence(self, e: Dict[str, Any]) -> List[List[Any]]:
        if e.get("evidence_count", 0) <= len(e.get("evidence", [])) or not self.base:
            return e.get("evidence", [])
        f = Path(self.base) / "evidence" / f"{e['type']}.jsonl"
        if f.exists():
            with f.open(encoding="utf-8") as fh:
                for line in fh:
                    r = json.loads(line)
                    if r["source"] == e["source"] and r["target"] == e["target"]:
                        return r["sites"]
        return e.get("evidence", [])

    @staticmethod
    def label(e: Dict[str, Any]) -> str:
        obs = e.get("observed")
        tag = "+".join(e.get("basis", []))
        if obs:
            tag += " ran:" + ",".join(f"{k}x{v}" for k, v in sorted(obs.items()))
        return f"[{tag} c{e.get('confidence', 1):.1f}]"


def load_graph(path: Path) -> Dict[str, Any]:
    path = Path(path)
    if path.is_dir():
        gd = path / "graph" if (path / "graph" / "meta.json").exists() else path
        meta = json.loads((gd / "meta.json").read_text(encoding="utf-8"))
        nodes = [json.loads(x) for x in (gd / "nodes.jsonl").read_text(encoding="utf-8").splitlines() if x]
        edges: List[Dict[str, Any]] = []
        for f in sorted((gd / "edges").glob("*.jsonl")):
            edges += [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x]
        return {"meta": meta, "nodes": nodes, "edges": edges, "_dir": str(gd.parent)}
    return json.loads(path.read_text(encoding="utf-8"))


FLOW_FORWARD = {"FEEDS", "WRITES", "CALLS", "SPAWNS", "PASSES_CALLBACK", "INVOKES", "EMITS", "REGISTERS",
                "INSTANTIATES", "ROUTES_TO", "IMPLEMENTED_BY"}
FLOW_TO_READERS = {"READS", "USES_ORGAN", "SUBSCRIBES", "HANDLES"}


def flow_successors(v: GraphView, nid: str) -> List[Tuple[str, Dict[str, Any], str]]:
    """Where information at nid goes next: (next node, edge, how)."""
    out: List[Tuple[str, Dict[str, Any], str]] = []
    ntype = v.nodes.get(nid, {}).get("type")
    for e in v.out.get(nid, ()):
        if e["type"] in FLOW_FORWARD:
            if ntype in CHANNELS and e["type"] != "FEEDS":
                continue
            out.append((e["target"], e, e["type"]))
    if ntype in CHANNELS or ntype == "Endpoint":
        for e in v.inn.get(nid, ()):
            if e["type"] in FLOW_TO_READERS:
                out.append((e["source"], e, "read by" if e["type"] != "HANDLES" else "handled by"))
    return out


def run_trace(args: argparse.Namespace) -> int:
    v = GraphView(load_graph(Path(args.graph)))
    start = args.start
    if start not in v.nodes:
        print(f"no node {start}; try query --find", file=sys.stderr)
        return 1
    target = args.to
    prev: Dict[str, Optional[Tuple[str, Dict[str, Any], str]]] = {start: None}
    q = deque([(start, 0)])
    order = []
    while q:
        cur, d = q.popleft()
        order.append((cur, d))
        if target and cur == target:
            break
        if d >= args.depth:
            continue
        for nxt, e, how in flow_successors(v, cur):
            if args.min_confidence and e.get("confidence", 1) < args.min_confidence:
                continue
            if args.observed_only and not e.get("observed"):
                continue
            if nxt not in prev:
                prev[nxt] = (cur, e, how)
                q.append((nxt, d + 1))
    if target:
        if target not in prev:
            print(f"no information path from {start} to {target} within depth {args.depth}")
            return 1
        chain = []
        cur = target
        while prev[cur] is not None:
            p, e, how = prev[cur]
            ev = (v.evidence(e) or [["?", 0]])[0]
            chain.append(f"{p}\n   --{how} {GraphView.label(e)} at {ev[0]}:{ev[1]}--> {cur}")
            cur = p
        print("\n".join(reversed(chain)))
        return 0
    for nid, d in order[: args.limit]:
        if d == 0:
            print(nid)
            continue
        p, e, how = prev[nid]
        print(f"{'  ' * d}<- {how} {GraphView.label(e)} from {p}\n{'  ' * d}   {nid}")
    print(f"\n{len(prev) - 1} nodes reached within depth {args.depth}")
    return 0


def run_investigate(args: argparse.Namespace) -> int:
    """Gather everything the graph knows about one subsystem: its state holders, who writes and reads them,
    the cross-language path, fallbacks and guards that answer with a default, thread boundaries, runtime
    reachability and what the recorded runs saw.  Facts only; the reading is the reader's."""
    v = GraphView(load_graph(Path(args.graph)))
    kw = args.topic.lower()
    hit = [n for nid, n in v.nodes.items() if kw in nid.lower() and n["type"] in
           ("Function", "Class", "Field", "Organ", "BusChannel", "Signal", "StateStore", "Endpoint", "Module")]
    by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for n in hit:
        by_type[n["type"]].append(n)
    L = [f"# Investigation: {args.topic}", "", f"Authors: {AUTHORS}  ",
         f"Graph of commit `{v.meta.get('source_commit', '')[:12]}`; runtime scenarios "
         f"{', '.join(v.meta.get('runtime_scenarios', [])) or 'none'}.", ""]

    def site(e: Dict[str, Any]) -> str:
        ev = (v.evidence(e) or [["?", 0]])[0]
        return f"{ev[0]}:{ev[1]}"

    L.append("## State that holds it")
    L.append("")
    holders = by_type.get("Field", []) + by_type.get("Organ", []) + by_type.get("BusChannel", []) + \
        by_type.get("Signal", []) + by_type.get("StateStore", [])
    for n in sorted(holders, key=lambda x: x["id"]):
        w = [e for e in v.inn.get(n["id"], ()) if e["type"] in ("WRITES", "REGISTERS")]
        r = [e for e in v.inn.get(n["id"], ()) if e["type"] in ("READS", "USES_ORGAN")]
        feeds_in = [e for e in v.inn.get(n["id"], ()) if e["type"] == "FEEDS"]
        flag = []
        if w and not r:
            flag.append("written, never read")
        if r and not w:
            flag.append("read, never written in the repo")
        if n.get("observed_in"):
            flag.append("observed in " + ",".join(n["observed_in"]))
        L.append(f"- `{n['id']}` ({n['type']}{', ' + n.get('kind') if n.get('kind') else ''})"
                 f"{': ' + '; '.join(flag) if flag else ''}")
        for e in sorted(w, key=lambda x: x["source"])[:12]:
            L.append(f"  - written by `{e['source']}` {GraphView.label(e)} at {site(e)}")
        for e in sorted(r, key=lambda x: x["source"])[:12]:
            L.append(f"  - read by `{e['source']}` {GraphView.label(e)} at {site(e)}")
        for e in sorted(feeds_in, key=lambda x: x["source"])[:6]:
            L.append(f"  - value from `{e['source']}` ({','.join(e.get('roles', []))}) at {site(e)}")
    L.append("")
    # one function writing several holders of the same thing
    L.append("## Functions that write more than one holder of it")
    L.append("")
    writers: Dict[str, List[str]] = defaultdict(list)
    for n in holders:
        for e in v.inn.get(n["id"], ()):
            if e["type"] in ("WRITES", "REGISTERS"):
                writers[e["source"]].append(n["id"])
    multi = {k: vv for k, vv in writers.items() if len(set(vv)) > 1}
    for k, vv in sorted(multi.items()):
        L.append(f"- `{k}` writes {', '.join(f'`{x}`' for x in sorted(set(vv)))}")
    if not multi:
        L.append("- none")
    L.append("")
    L.append("## Cross-language and cross-runtime path")
    L.append("")
    for n in sorted(by_type.get("Endpoint", []), key=lambda x: x["id"]):
        ins = [e for e in v.inn.get(n["id"], ()) if e["type"] in ("INVOKES", "EMITS", "FEEDS")]
        outs = [e for e in v.out.get(n["id"], ()) if e["type"] in ("ROUTES_TO", "FEEDS")]
        handlers = [e for e in v.inn.get(n["id"], ()) if e["type"] in ("HANDLES", "SUBSCRIBES")]
        L.append(f"- `{n['id']}`")
        for e in ins:
            L.append(f"  - from `{e['source']}` ({e['type']}) at {site(e)}")
        for e in handlers:
            L.append(f"  - {e['type'].lower()} by `{e['source']}` at {site(e)}")
        for e in outs:
            L.append(f"  - to `{e['target']}` ({e['type']})")
    L.append("")
    L.append("## Places that answer with a default instead of the real state")
    L.append("")
    seen_fb = 0
    for nid, n in sorted(v.nodes.items()):
        rel = nid.lower()
        fb = n.get("fallbacks") or []
        er = n.get("early_returns") or []
        if kw not in rel and not any(kw in str(x).lower() for x in fb + er):
            continue
        for x in fb:
            L.append(f"- `{nid}` line {x['line']}: {x['kind']} {x.get('key') or ''} -> `{x['default']}`")
            seen_fb += 1
        for x in er:
            L.append(f"- `{nid}` line {x['line']}: if `{x['cond']}` return `{x['returns']}`")
            seen_fb += 1
    if not seen_fb:
        L.append("- none found")
    L.append("")
    L.append("## Background work and thread boundaries")
    L.append("")
    for n in sorted(by_type.get("Function", []) + by_type.get("Class", []), key=lambda x: x["id"]):
        for e in v.inn.get(n["id"], ()):
            if e["type"] in ("SPAWNS", "PASSES_CALLBACK"):
                L.append(f"- `{e['source']}` {e['type'].lower()} `{n['id']}` "
                         f"({', '.join(e.get('mechanisms', []) or e.get('to', []))}) {GraphView.label(e)} at {site(e)}")
    L.append("")
    L.append("## Which runtime reaches each function, and what ran")
    L.append("")
    L.append("| function | reachable from (static) | observed in | unresolved calls |")
    L.append("|---|---|---|---:|")
    for n in sorted(by_type.get("Function", []), key=lambda x: x["id"])[: args.limit]:
        L.append(f"| `{n['id']}` | {', '.join(n.get('reachable_from', [])) or '-'} | "
                 f"{', '.join(n.get('observed_in', [])) or '-'} | {n.get('unresolved_calls', 0)} |")
    L.append("")
    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[aurora-kg] wrote {args.out}")
    else:
        print(text)
    return 0


DEV_RECORD_RE = re.compile(r"(lineage|genealog|evolution|evolv|develop|dream|curricul|trace|history|journal|"
                           r"growth|epoch|chamber|ledger|provenance)", re.I)
FAULT_RE = re.compile(r"(fault|error|crash|incident|failure|diagnos)", re.I)
DIAG_EXPR_RE = re.compile(r"^(log|logger|_log|LOG|logging|self\.log|self\.logger|self\._log)\.(debug|info|warning|"
                          r"warn|error|exception|critical)$")


def run_diff(args: argparse.Namespace) -> int:
    """Compare two graphs (base, head) and write what changed architecturally: lineage identities, lost and
    consolidated edges, stored-state keys, fault references, developmental records, dependencies, diagnostic
    evidence, and named focus areas.  'Consolidated' means the source still reaches the old target within
    two hops of the same kind of edge in head; everything else removed is 'lost' and listed."""
    A = GraphView(load_graph(Path(args.base)))
    B = GraphView(load_graph(Path(args.head)))
    out_lines: List[str] = []
    W = out_lines.append
    W("# Architectural comparison")
    W("")
    W(f"Authors: {AUTHORS}  ")
    W(f"Base `{A.meta.get('source_commit', '')[:12]}` ({A.meta.get('source_branch', '')}), head "
      f"`{B.meta.get('source_commit', '')[:12]}` ({B.meta.get('source_branch', '')}). "
      f"Static content hashes {A.meta.get('static_content_hash', '')[:12]} and {B.meta.get('static_content_hash', '')[:12]}.")
    W("")
    # ---------------------------------------------------------------- lineage
    fa = {k: n for k, n in A.nodes.items() if n["type"] == "Function"}
    fb = {k: n for k, n in B.nodes.items() if n["type"] == "Function"}
    gone = sorted(set(fa) - set(fb))
    new = sorted(set(fb) - set(fa))
    by_hash_b: Dict[str, List[str]] = defaultdict(list)
    by_name_b: Dict[str, List[str]] = defaultdict(list)
    for k in new:
        if fb[k].get("body_hash"):
            by_hash_b[fb[k]["body_hash"]].append(k)
        by_name_b[fb[k].get("name", "")].append(k)
    moved: List[Tuple[str, str, str]] = []
    deleted: List[str] = []
    for k in gone:
        n = fa[k]
        same = by_hash_b.get(n.get("body_hash", ""), [])
        if len(same) == 1:
            moved.append((k, same[0], "identical body"))
            continue
        cand = [x for x in by_name_b.get(n.get("name", ""), []) if fb[x].get("signature") == n.get("signature")]
        if len(cand) == 1:
            moved.append((k, cand[0], "same name and signature"))
        else:
            deleted.append(k)
    changed_body = sorted(k for k in set(fa) & set(fb) if fa[k].get("body_hash") != fb[k].get("body_hash"))
    moved_targets = {b for _, b, _ in moved}
    extracted = [k for k in new if k not in moved_targets]
    W("## 1. Function lineage")
    W("")
    W(f"{len(fa)} functions in base, {len(fb)} in head. {len(changed_body)} kept their identity with a changed body; "
      f"{len(moved)} changed identity (moved or renamed); {len(deleted)} were removed; {len(extracted)} are new.")
    W("")
    W("A changed identity breaks any record keyed by the old id (lineage, provenance, fault and test references).")
    W("")
    for a, b2, why in moved[:80]:
        W(f"- moved: `{a}` -> `{b2}` ({why})")
    for k in deleted[:120]:
        callers = [e["source"] for e in A.inn.get(k, ()) if e["type"] == "CALLS" and e["source"] in B.nodes]
        obs = fa[k].get("observed_in")
        W(f"- removed: `{k}`" + (f"; still-present callers in base: {', '.join(f'`{c}`' for c in callers[:4])}" if callers else "")
          + (f"; ran in {','.join(obs)}" if obs else ""))
    for k in extracted[:80]:
        callers = [e["source"] for e in B.inn.get(k, ()) if e["type"] == "CALLS"]
        W(f"- new: `{k}`" + (f", called by {', '.join(f'`{c}`' for c in callers[:4])}" if callers else ", no static caller"))
    W("")
    # ---------------------------------------------------------------- edges
    rename = {a: b2 for a, b2, _ in moved}

    def mapped(x: str) -> str:
        return rename.get(x, x)

    ka = set(A.key)
    kb = set(B.key)
    ignore = {"CONTAINS", "DOCUMENTS", "EXPRESSES", "GOVERNS"}
    def comp(x: str) -> bool:      # evidence composites are named by their members, so compared separately
        return x.startswith("subsys:composite:")

    removed_edges = [k for k in ka if k[1] not in ignore and not comp(k[2]) and not comp(k[0])
                     and (mapped(k[0]), k[1], mapped(k[2])) not in kb]
    ka_mapped = {(mapped(a), t, mapped(c)) for a, t, c in ka}
    added_edges = [k for k in kb if k[1] not in ignore and not comp(k[2]) and not comp(k[0]) and k not in ka_mapped]

    def reaches_in_b(src: str, et: str, dst: str) -> bool:
        src, dst = mapped(src), mapped(dst)
        if src not in B.nodes:
            return False
        frontier = {src}
        for _ in range(2):
            nxt = set()
            for s0 in frontier:
                for e in B.out.get(s0, ()):
                    if e["type"] == et and e["target"] == dst:
                        return True
                    if e["type"] in ("CALLS", "INSTANTIATES"):
                        nxt.add(e["target"])
            frontier = nxt
        return False

    def short(x: str) -> str:
        return x.rsplit(".", 1)[-1].lstrip("_")

    def module_bound_reach(src: str, et: str, dst: str) -> Optional[str]:
        """The source's module binds a helper at import time (for example a recorder made by a factory) that still
        reaches the old target: the call now goes through that binding, which static resolution does not follow
        into the closure."""
        mod = B.module_of(mapped(src))
        if not mod:
            return None
        for e in B.out.get(mod, ()):
            if e["type"] in ("CALLS", "INSTANTIATES") and (e["target"] == mapped(dst) or reaches_in_b(e["target"], et, dst)
                                                          or any(x["target"] == mapped(dst) for x in B.out.get(e["target"], ())
                                                                 if x["type"] in ("CALLS", "INSTANTIATES"))):
                return e["target"]
            # a factory whose nested function calls the target
            for c in B.out.get(e["target"], ()):
                if c["type"] == "CONTAINS" and any(x["target"] == mapped(dst) for x in B.out.get(c["target"], ())
                                                   if x["type"] == "CALLS"):
                    return e["target"]
        return None

    def retarget(src: str, et: str, dst: str) -> Optional[str]:
        """The old target is gone and the same source now uses a target with the same short name."""
        if mapped(dst) in B.nodes:
            return None
        for e in B.out.get(mapped(src), ()):
            if e["type"] == et and short(e["target"]) == short(dst):
                return e["target"]
        return None

    consolidated, lost, with_code, delegated, retargeted = [], [], [], [], []
    absorbed, run_only = [], []
    via: Dict[Tuple[str, str, str], str] = {}
    for k in removed_edges:
        e0 = A.key[k]
        if k[0] not in B.nodes and mapped(k[0]) == k[0]:
            with_code.append(k)
        elif reaches_in_b(*k):
            consolidated.append(k)
        elif "implemented" not in (e0.get("basis") or []) and "observed" in (e0.get("basis") or []):
            run_only.append(k)
        elif mapped(k[0]) != k[0] or (mapped(k[2]) != k[2] and k[1] in ("READS", "FEEDS", "WRITES")):
            via[k] = mapped(k[0]) if mapped(k[0]) != k[0] else mapped(k[2])
            absorbed.append(k)
        elif k[1] in ("CALLS", "INSTANTIATES", "FEEDS") and retarget(*k):
            via[k] = retarget(*k) or ""
            retargeted.append(k)
        elif k[1] in ("CALLS", "INSTANTIATES") and module_bound_reach(*k):
            via[k] = module_bound_reach(*k) or ""
            delegated.append(k)
        else:
            lost.append(k)
    W("## 2. Relationships: consolidated against lost")
    W("")
    W(f"{len(removed_edges)} relationships of base are not in head (structure and documentation edges left out). "
      f"{len(consolidated)} are consolidated: the same source still reaches the same target through a helper "
      f"within two calls. {len(retargeted)} are retargeted: the old target is gone and the source now calls one "
      f"of the same name (a shared helper). {len(delegated)} are delegated: the source's module binds a helper at "
      f"import time that still reaches the old target, a path static resolution does not follow into the "
      f"closure. {len(absorbed)} belonged to a function that was folded into a shared one (the shared body no "
      f"longer names those fields or targets one by one). {len(run_only)} were seen only in the base run and not "
      f"in the head run, which is a difference between recordings, not code. {len(with_code)} went with code "
      f"that was removed. {len(lost)} are lost: the source still exists and no longer reaches the target by any "
      f"of those routes. {len(added_edges)} relationships are new.")
    W("")
    for title, rows in (("Retargeted", retargeted), ("Delegated through a module binding", delegated),
                        ("Folded into a shared function", absorbed), ("Seen only in the base run", run_only)):
        by_v = Counter((k[1], short(k[2]), via.get(k, "")) for k in rows)
        W(f"### {title}: {len(rows)}")
        W("")
        for (t, name, v), n in by_v.most_common(30):
            W(f"- {n} {t} to `{name}` now through `{v}`")
        W("")
    for title, rows in (("Lost (review each)", lost), ("Removed with deleted code", with_code),
                        ("Consolidated", consolidated)):
        by_t = Counter(k[1] for k in rows)
        W(f"### {title}: " + ", ".join(f"{t} {n}" for t, n in by_t.most_common()))
        W("")
        for k in sorted(rows, key=lambda x: (x[1], x[0], x[2]))[: (300 if title.startswith("Lost") else 80)]:
            e = A.key[k]
            ev = (A.evidence(e) or [["?", 0]])[0]
            obs = " (ran)" if e.get("observed") else ""
            W(f"- `{k[0]}` {k[1]} `{k[2]}`{obs} [base {ev[0]}:{ev[1]}]")
        W("")
    # ---------------------------------------------------------------- stores
    sa = {k for k, n in A.nodes.items() if n["type"] == "StateStore"}
    sb = {k for k, n in B.nodes.items() if n["type"] == "StateStore"}

    def rw(v: GraphView, sid: str) -> Tuple[Set[str], Set[str]]:
        w = {mapped(e["source"]) if v is A else e["source"] for e in v.inn.get(sid, ()) if e["type"] == "WRITES"}
        r = {mapped(e["source"]) if v is A else e["source"] for e in v.inn.get(sid, ()) if e["type"] == "READS"}
        return w, r

    # ---------------------------------------------------------------- composites
    def comps(v: GraphView) -> Dict[str, Set[str]]:
        out: Dict[str, Set[str]] = defaultdict(set)
        for e in v.edges:
            if e["type"] == "MEMBER_OF" and comp(e["target"]):
                out[e["target"]].add(v.nodes.get(e["source"], {}).get("path", e["source"]))
        return out

    ca, cb = comps(A), comps(B)
    W("## 2b. Composites promoted on evidence")
    W("")
    W(f"{len(ca)} in base, {len(cb)} in head. Each base composite is matched to the head composite sharing the most "
      "files; a composite that splits, loses files or disappears means the binding between those files changed.")
    W("")
    for cid, mem in sorted(ca.items()):
        best, bj = None, 0.0
        for hid, hm in cb.items():
            j = len(mem & hm) / len(mem | hm) if mem | hm else 0.0
            if j > bj:
                best, bj = hid, j
        if bj < 1.0:
            hm = cb.get(best, set()) if best else set()
            W(f"- `{cid}` ({len(mem)} files) -> " + (f"`{best}` (overlap {bj:.2f})" if best else "no match")
              + (f"; left: {', '.join(f'`{x}`' for x in sorted(mem - hm)[:6])}" if mem - hm else "")
              + (f"; joined: {', '.join(f'`{x}`' for x in sorted(hm - mem)[:6])}" if hm - mem else ""))
    W("")
    W("## 3. Stored state")
    W("")
    W(f"Stores named only in base: {', '.join(f'`{x[6:]}`' for x in sorted(sa - sb)) or 'none'}.  ")
    W(f"Stores named only in head: {', '.join(f'`{x[6:]}`' for x in sorted(sb - sa)) or 'none'}.")
    W("")
    rows = []
    for sid in sorted(sa & sb):
        wa, ra = rw(A, sid)
        wb, rb = rw(B, sid)
        if wa != wb or ra != rb:
            note = []
            if wa and not wb:
                note.append("LOST ALL WRITERS")
            if ra and not rb:
                note.append("LOST ALL READERS")
            rows.append(f"- `{sid[6:]}`: writers {len(wa)}->{len(wb)}, readers {len(ra)}->{len(rb)}"
                        + (f" **{'; '.join(note)}**" if note else "")
                        + (f"; writers gone: {', '.join(f'`{x}`' for x in sorted(wa - wb)[:4])}" if wa - wb else "")
                        + (f"; readers gone: {', '.join(f'`{x}`' for x in sorted(ra - rb)[:4])}" if ra - rb else ""))
    W("\n".join(rows) if rows else "No store changed writers or readers.")
    W("")
    W("Stored-state keys inside those files are not parsed from code, so a renamed JSON key inside an unchanged "
      "store needs the lost FEEDS and Field edges above, or a reading of the diff, to show.")
    W("")
    # ---------------------------------------------------------------- faults and developmental records
    def cites(v: GraphView) -> Set[Tuple[str, str]]:
        return {(mapped(e["source"]) if v is A else e["source"], e["target"]) for e in v.edges if e["type"] == "CITES"}

    ca, cb = cites(A), cites(B)
    W("## 4. Fault references")
    W("")
    W(f"FIX citations in code: {len(ca)} in base, {len(cb)} in head.")
    lost_c = sorted(ca - cb)
    for s0, t in lost_c[:80]:
        W(f"- citation gone: `{s0}` -> `{t}`" + ("" if s0 in B.nodes else " (citing code removed)"))
    fault_nodes_a = {k for k in A.nodes if FAULT_RE.search(k) and A.nodes[k]["type"] in ("Function", "Class", "StateStore", "Field")}
    fault_nodes_b = {k for k in B.nodes if FAULT_RE.search(k) and B.nodes[k]["type"] in ("Function", "Class", "StateStore", "Field")}
    W(f"Fault and error handling nodes: {len(fault_nodes_a)} in base, {len(fault_nodes_b)} in head; "
      f"gone: {', '.join(f'`{x}`' for x in sorted({mapped(x) for x in fault_nodes_a} - fault_nodes_b)[:30]) or 'none'}; "
      f"new: {', '.join(f'`{x}`' for x in sorted(fault_nodes_b - {mapped(x) for x in fault_nodes_a})[:30]) or 'none'}.")
    W("")
    W("## 5. Developmental records")
    W("")
    dev = sorted(x for x in sa | sb if DEV_RECORD_RE.search(x))
    drows = []
    for sid in dev:
        wa, ra = rw(A, sid) if sid in A.nodes else (set(), set())
        wb, rb = rw(B, sid) if sid in B.nodes else (set(), set())
        if (wa, ra) != (wb, rb) or sid not in A.nodes or sid not in B.nodes:
            drows.append(f"- `{sid[6:]}`: writers {len(wa)}->{len(wb)}, readers {len(ra)}->{len(rb)}"
                         + (" (only in base)" if sid not in B.nodes else "") + (" (only in head)" if sid not in A.nodes else ""))
    W(f"{len(dev)} stores look like lineage, evolution, development or history records by name.")
    W("\n".join(drows) if drows else "None changed writers or readers.")
    W("")
    # ---------------------------------------------------------------- dependencies
    W("## 6. Dependencies between modules")
    W("")
    ia = {(e["source"], e["target"]) for e in A.edges if e["type"] == "IMPORTS"}
    ib = {(e["source"], e["target"]) for e in B.edges if e["type"] == "IMPORTS"}
    for s0, t in sorted(ia - ib)[:80]:
        W(f"- import gone: `{s0}` -> `{t}`")
    for s0, t in sorted(ib - ia)[:80]:
        W(f"- import new: `{s0}` -> `{t}`")
    if ia == ib:
        W("- no import changed")
    W("")
    # ---------------------------------------------------------------- diagnostics
    W("## 7. Diagnostic evidence")
    W("")

    def diag(v: GraphView) -> Counter:
        c: Counter = Counter()
        if not v.base:
            return c
        f = Path(v.base) / "coverage" / "unresolved_calls.jsonl"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if DIAG_EXPR_RE.match(r["expr"]):
                    c[v.module_of(r["owner"]) or r["path"]] += 1
        f2 = Path(v.base) / "coverage" / "library_calls.jsonl"
        if f2.exists():
            for line in f2.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if r.get("logging"):
                    c[v.module_of(r["owner"]) or r["owner"]] += int(r["logging"])
        return c

    da, db = diag(A), diag(B)
    W(f"Logging calls: {sum(da.values())} in base, {sum(db.values())} in head.")
    for mod in sorted(set(da) | set(db)):
        if da[mod] != db[mod]:
            W(f"- `{mod}`: {da[mod]} -> {db[mod]}")
    W("")
    # ---------------------------------------------------------------- focus areas
    W("## 8. Focus areas")
    W("")
    focus = [("Interaction handling", ["fn:aurora.process_external_user_turn"]),
             ("Praxis", sorted(k for k in A.nodes if "praxis" in k.lower() and A.nodes[k]["type"] in ("Function", "Organ", "Field", "Endpoint"))),
             ("Surface and subsurface coordination", sorted(k for k in A.nodes if ("strata" in k.lower() or "subsurface" in k.lower()) and A.nodes[k]["type"] in ("Function", "Organ", "BusChannel", "Field"))),
             ("State hand-offs (bus slots and pipeline signals)", sorted(k for k in A.nodes if A.nodes[k]["type"] in ("BusChannel", "Signal")))]
    for title, seeds in focus:
        def reach(v: GraphView, ss: List[str], mapit: bool) -> Set[Tuple[str, str, str]]:
            seen_e: Set[Tuple[str, str, str]] = set()
            frontier = [mapped(s0) if mapit else s0 for s0 in ss]
            seen_n = set(frontier)
            depth = 0
            while frontier and depth < (4 if len(ss) < 5 else 1):
                nxt = []
                for s0 in frontier:
                    for e in list(v.out.get(s0, ())) + list(v.inn.get(s0, ())):
                        if e["type"] in ignore:
                            continue
                        k = (e["source"], e["type"], e["target"])
                        if mapit:
                            k = (mapped(k[0]), k[1], mapped(k[2]))
                        seen_e.add(k)
                        o = k[2] if k[0] == s0 else k[0]
                        if o not in seen_n and len(ss) < 5:
                            seen_n.add(o)
                            nxt.append(o)
                frontier = nxt
                depth += 1
            return seen_e
        ea, eb = reach(A, seeds, True), reach(B, [mapped(s) for s in seeds], False)
        lost_f = sorted(ea - eb)
        lost_set = {(mapped(a), t, mapped(c)) for a, t, c in lost}
        lost_real = [k for k in lost_f if k in lost_set]
        W(f"### {title}")
        W("")
        W(f"{len(seeds)} seed node(s); {len(ea)} relationships around them in base, {len(eb)} in head; "
          f"{len(lost_real)} lost (not consolidated), {len(set(eb) - set(ea))} new.")
        for k in lost_real[:40]:
            W(f"- lost: `{k[0]}` {k[1]} `{k[2]}`")
        W("")
    text = "\n".join(out_lines) + "\n"
    Path(args.out).write_text(text, encoding="utf-8")
    # the full record behind the summary: every classified relationship with its base evidence
    def rec(k: Tuple[str, str, str]) -> Dict[str, Any]:
        e = A.key[k]
        return {"source": k[0], "type": k[1], "target": k[2], "evidence": A.evidence(e)[:6],
                "observed": bool(e.get("observed")), "via": via.get(k)}
    full = {"base": A.meta.get("source_commit"), "head": B.meta.get("source_commit"),
            "lineage": {"moved": [list(x) for x in moved], "removed": deleted, "new": extracted,
                        "changed_body": changed_body},
            "relationships": {"lost": [rec(k) for k in sorted(lost)], "retargeted": [rec(k) for k in sorted(retargeted)],
                              "delegated": [rec(k) for k in sorted(delegated)],
                              "folded_into_shared": [rec(k) for k in sorted(absorbed)],
                              "seen_only_in_base_run": [rec(k) for k in sorted(run_only)],
                              "consolidated": [rec(k) for k in sorted(consolidated)],
                              "removed_with_code": [rec(k) for k in sorted(with_code)],
                              "added": [{"source": a, "type": t, "target": c} for a, t, c in sorted(added_edges)]}}
    jpath = Path(args.out).with_suffix(".json")
    jpath.write_text(json.dumps(full, indent=1, default=str) + "\n", encoding="utf-8")
    print(f"[aurora-kg] wrote {args.out} and {jpath.name}: {len(lost)} lost, {len(retargeted)} retargeted, "
          f"{len(delegated)} delegated, {len(consolidated)} consolidated, {len(with_code)} with removed code, "
          f"{len(moved)} identities changed")
    return 0

# ===========================================================================
# SECTION 9 -- COMMAND LINE
# ===========================================================================

def load_ontology(path: Optional[str]) -> Dict[str, Any]:
    ont = json.loads(json.dumps(DEFAULT_ONTOLOGY))
    if path:
        override = json.loads(Path(path).read_text(encoding="utf-8"))
        ont.update(override)
    return ont


def main(argv: Optional[List[str]] = None) -> int:
    default_root = Path(__file__).resolve().parents[1]
    default_graph = default_root / "knowledge_graph"
    ap = argparse.ArgumentParser(description="Build and read Aurora's codebase knowledge graph.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "check"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=str(default_root), help="repository root")
        p.add_argument("--out", default=None, help="output directory (default <root>/knowledge_graph)")
        p.add_argument("--ontology", default=None, help="JSON file overriding the canonical ontology")
        p.add_argument("--ownership", default=None,
                       help="module ownership mapping (default <root>/docs/module_ownership.json when present)")
        p.add_argument("--runtime", action="append", default=[],
                       help="runtime observations file or directory (repeatable); default <out>/runtime when present")
        p.add_argument("--no-tests", action="store_true", help="leave tests/ out of the graph")
        p.add_argument("--lenient", action="store_true", help="write even if schema validation finds problems")
        p.add_argument("--quiet", action="store_true")
        if name == "build":
            p.add_argument("--formats", default="graph,schema,ontology,summary,html",
                           help="comma list of graph, json, graphml, jsonld, schema, ontology, summary, html, or all")
    q = sub.add_parser("query")
    q.add_argument("--graph", default=str(default_graph))
    q.add_argument("--find")
    q.add_argument("--node")
    q.add_argument("--impact")
    q.add_argument("--depth", type=int, default=3)
    q.add_argument("--path", nargs=2, metavar=("FROM", "TO"))
    t = sub.add_parser("trace", help="follow information forward from a node: flow, writes, reads, calls, hand-offs")
    t.add_argument("start")
    t.add_argument("--to", default=None, help="stop at this node and print the one path")
    t.add_argument("--graph", default=str(default_graph))
    t.add_argument("--depth", type=int, default=6)
    t.add_argument("--limit", type=int, default=300)
    t.add_argument("--min-confidence", type=float, default=0.0)
    t.add_argument("--observed-only", action="store_true")
    inv = sub.add_parser("investigate", help="everything the graph knows about one subsystem, as Markdown")
    inv.add_argument("topic")
    inv.add_argument("--graph", default=str(default_graph))
    inv.add_argument("--out", default=None)
    inv.add_argument("--limit", type=int, default=120)
    d = sub.add_parser("diff", help="architectural comparison of two built graphs")
    d.add_argument("base")
    d.add_argument("head")
    d.add_argument("--out", required=True)
    sub.add_parser("schema")
    args = ap.parse_args(argv)

    if args.cmd == "schema":
        print(json.dumps(schema_document(), indent=2, sort_keys=True))
        return 0
    if args.cmd == "query":
        return run_query(args)
    if args.cmd == "trace":
        return run_trace(args)
    if args.cmd == "investigate":
        return run_investigate(args)
    if args.cmd == "diff":
        return run_diff(args)

    root = Path(args.root).resolve()
    out = Path(args.out).resolve() if args.out else root / "knowledge_graph"
    ont = load_ontology(args.ontology)
    runtime = [Path(x).resolve() for x in args.runtime]
    if not runtime and (out / "runtime").is_dir():
        runtime = [out / "runtime"]
    b = Builder(root, ont, include_tests=not args.no_tests, quiet=args.quiet)
    g = b.build(ownership_file=Path(args.ownership).resolve() if args.ownership else None, runtime=runtime)
    problems = b.validate()
    if problems:
        print(f"[aurora-kg] schema validation found {len(problems)} problem(s):", file=sys.stderr)
        for msg in problems[:40]:
            print(f"  {msg}", file=sys.stderr)
        if not args.lenient:
            return 2
    meta = build_meta(b, g)

    if args.cmd == "check":
        existing = out / "graph" / "meta.json"
        if not existing.exists():
            print(f"[aurora-kg] no committed graph at {existing}", file=sys.stderr)
            return 1
        committed = json.loads(existing.read_text(encoding="utf-8")).get("static_content_hash", "")
        if committed != meta["static_content_hash"]:
            print(f"[aurora-kg] STALE: committed {committed[:16]} vs source {meta['static_content_hash'][:16]}. "
                  f"Run: python scripts/aurora_knowledge_graph.py build", file=sys.stderr)
            return 1
        print(f"[aurora-kg] up to date ({meta['static_content_hash'][:16]}; runtime evidence is not part of the check)")
        return 0

    formats = {f.strip() for f in args.formats.split(",") if f.strip()}
    if "all" in formats:
        formats |= {"graph", "json", "graphml", "jsonld", "schema", "ontology", "summary", "html"}
    out.mkdir(parents=True, exist_ok=True)
    exports = out / "exports"
    written: List[str] = []
    if "graph" in formats:
        written += write_sharded(out, meta, g, b)
    if formats & {"json", "graphml", "jsonld"}:
        # large single-file views, regenerated on demand and kept out of git by knowledge_graph/.gitignore
        exports.mkdir(exist_ok=True)
        (out / ".gitignore").write_text("exports/\n", encoding="utf-8")
    if "json" in formats:
        write_json(exports / "aurora_kg.json", meta, g)
        written.append("exports/aurora_kg.json")
    if "graphml" in formats:
        write_graphml(exports / "aurora_kg.graphml", meta, g)
        written.append("exports/aurora_kg.graphml")
    if "jsonld" in formats:
        write_jsonld(exports / "aurora_kg.jsonld", meta, g)
        written.append("exports/aurora_kg.jsonld")
    if "schema" in formats:
        write_schema(out / "schema.json")
        written.append("schema.json")
    if "ontology" in formats:
        (out / "ontology.json").write_text(json.dumps(ont, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append("ontology.json")
    if "summary" in formats:
        write_summary(out / "SUMMARY.md", meta, g, b)
        written.append("SUMMARY.md")
    if "html" in formats:
        write_html(out / "index.html", meta, g, b)
        written.append("index.html")
    b.log(f"wrote {', '.join(written)} to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
