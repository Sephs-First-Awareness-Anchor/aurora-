# Aurora Codebase Knowledge Graph: Design and Generator

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Generator:** `scripts/aurora_knowledge_graph.py`, version 2.0.0, stdlib only, Python 3.9+
**Built from:** `claude/knowledge-graph` at `2b5de7e` (main `f5c7beb` plus the ownership record of PR #262), with the desktop boot and turn recordings in `knowledge_graph/runtime/`.

`// ⚙ Preemptive hardening applied — 6 known patterns enforced.` (authorship header, `aurora_` prefix, canonical X/T/N/B/A symbols, canonical I-State order, the exact re-entry sequence, 25 channels and 625 slots)

---

## 1. What it is

One generator reads the whole repository and writes a typed, directed graph of it: every Python module, class, function, constant and field; the Rust, Dart, Kotlin and Java sources; the channels and endpoints that join the desktop, the phone and the ACM; the persisted stores, organ slots and bus slots; and Aurora's own vocabulary (layers, axes, Non-Comps, I-State pairs, the re-entry loop, the fix registry, the docs).

The graph is never edited by hand. The same source and the same recordings give the same graph, and `check` fails when the committed graph no longer matches the code.

It holds four kinds of knowledge and never mixes them:

| basis | meaning | where it comes from |
|---|---|---|
| `implemented` | read from the code | Python AST, patterns for Rust, Dart, Kotlin and Java |
| `declared` | stated by a person | `docs/module_ownership.json`, the docs, the ontology, the fix registry |
| `observed` | a recorded run took it | `knowledge_graph/runtime/*.json` |
| `inferred` | a grouping or name match the generator made | composites, cross-language name matches |

An edge can carry more than one basis (for example `implemented+observed`). Every edge keeps its `provenance`, its `confidence`, its full `evidence_count`, the first three `[file, line]` sites inline, and every site in `evidence/<TYPE>.jsonl`.

## 2. Where it lives

```
scripts/aurora_knowledge_graph.py     the generator
scripts/aurora_kg_observe.py          the runtime recorder (desktop boot, desktop turns, phone boot)
knowledge_graph/
  graph/meta.json                     counts, hashes, coverage totals, the mapping it read
  graph/nodes.jsonl                   one node per line
  graph/edges/<TYPE>.jsonl            one edge type per file, one edge per line
  evidence/<TYPE>.jsonl               every evidence site for edges with more than three
  coverage/COVERAGE.md                what is covered, what is not, and why
  coverage/files.jsonl                every file in the repo and how it was read
  coverage/unresolved_calls.jsonl     every call site with no static target, with its reason
  coverage/library_calls.jsonl        calls into libraries and built-in values (not gaps)
  coverage/unobserved.json            statically reachable functions no recording entered
  coverage/claims.json                every declared claim checked against the code
  coverage/composites.json            evidence composites, declared composites, cross-domain links
  runtime/                            the recordings the build used
  investigations/                     written answers that read the graph with the code
  comparisons/                        architectural comparisons between two builds
  SUBSYSTEMS.md                       the ladder, King to base files
  SUMMARY.md                          counts, hubs, organs, stores, doctrine, standing rules
  index.html                          self-contained interactive view, works offline
  schema.json, ontology.json          the types the build enforces and the vocabulary it used
  exports/                            not committed: GraphML and JSON-LD on demand
```

The graph is sharded by type so a change to one kind of relationship shows as a change to one file in a diff.

## 3. Commands

```bash
python scripts/aurora_knowledge_graph.py build --runtime knowledge_graph/runtime
python scripts/aurora_knowledge_graph.py check --runtime knowledge_graph/runtime
python scripts/aurora_knowledge_graph.py query --find SediMemory
python scripts/aurora_knowledge_graph.py query --node mod:aurora_sedimemory
python scripts/aurora_knowledge_graph.py query --impact mod:aurora_internal.aurora_leverage_scalar --depth 2
python scripts/aurora_knowledge_graph.py query --path fn:aurora.boot_aurora store:aurora_oets_web.json
python scripts/aurora_knowledge_graph.py trace fn:aurora_bridge.initialize --depth 4
python scripts/aurora_knowledge_graph.py trace bus:_praxis_context --observed-only
python scripts/aurora_knowledge_graph.py investigate praxis --out praxis.md
python scripts/aurora_knowledge_graph.py diff <base graph dir> <head graph dir> --out COMPARISON.md
python scripts/aurora_knowledge_graph.py schema
python scripts/aurora_kg_observe.py desktop --state <copy of a state dir>
```

- `--impact` is potential dependency: everything that could be affected by a change, through calls, flows, imports, inheritance, organs, stores and tests. It is not a prediction that each of those breaks.
- `trace` follows information forward: what a node feeds, writes, hands to a thread or a callback, and who reads it next, across the language bridges.
- `investigate` gathers everything the graph knows about one subsystem: its files, entry points, state, readers and writers, endpoints, claims and runtime evidence.
- `diff` compares two builds and classifies every relationship that changed (section 9).

## 4. Identity

Every node id is `<prefix>:<qualified name>`, readable and stable across builds:

| Example id | Meaning |
|---|---|
| `mod:aurora_internal.aurora_leverage_scalar` | a Python module |
| `cls:aurora_internal.aurora_leverage_scalar.PhaseNudge` | a class |
| `fn:aurora.boot_aurora` | a function or method |
| `field:aurora_praxis_bridge.PraxisBridge.systems` | an attribute that carries state |
| `src:flutter_app/lib/services/praxis_bridge.dart` | a non-Python source file |
| `ep:methodchannel:aurora/bridge#getPraxisStatus` | a cross-language endpoint |
| `store:aurora_oets_web.json` | a persisted file, relative to the state dir |
| `bus:_praxis_context` | a `systems["_key"]` bus slot |
| `organ:sensory_crystal` | a `systems["key"]` organ slot |
| `subs:king:aurora`, `subsys:quasi:phone`, `subsys:category:<id>` | the ladder |
| `axis:X`, `istate:IS/ISNT`, `ncdim:COST`, `nc:Agentive_Cost` | vocabulary |
| `rule:FIX-A001`, `layer:L5`, `doc:docs/LAYER_MODULE_OWNERSHIP.md` | doctrine and docs |

`aurora_state/x.json` and `state_dir / "x.json"` resolve to the same `store:x.json`. A recorded path such as `a/b/../../c.py` is normalised before it is matched, and per-run temp files become `<tempfile>`, so two runs meet on the same nodes.

## 5. Node types (25)

Repository, Package, Module, Class, Function, Constant, Field, ExternalDependency, SourceFile, Endpoint, Signal, StateStore, BusChannel, Organ, EnvVar, Layer, Subsystem, ConstraintAxis, IStatePair, NonCompDimension, NonComp, ManifoldEntry, Concept, DoctrineRule, Document.

`schema.json` gives each one's required attributes. A build that would write a node the schema does not allow stops, unless `--lenient` is passed.

## 6. Edge types (33)

| group | types |
|---|---|
| structure | CONTAINS, MEMBER_OF, PART_OF, COMPOSED_OF, INHERITS, OVERRIDES |
| code | IMPORTS, CALLS, INSTANTIATES, REFERENCES, TESTS |
| information flow | FEEDS (with a role: argument, return, attribute, field, yield), READS, WRITES, PERSISTS_TO |
| background and callbacks | SPAWNS (threads, executors, timers, coroutines), PASSES_CALLBACK, RUNS (launchers) |
| organs and the bus | REGISTERS, USES_ORGAN, IMPLEMENTED_BY |
| across languages and processes | INVOKES, HANDLES, ROUTES_TO, EMITS, SUBSCRIBES |
| intent | GOVERNS, OWNED_BY, DOCUMENTS, CITES, EXPRESSES, MAPS_TO, PRECEDES |

## 7. Runtime evidence

`aurora_kg_observe.py` runs a scenario against a copy of a state directory and records:

- every caller and callee pair Python entered (`sys.monitoring`, PY_START), with counts;
- every file opened and every thread started (an audit hook on `open` and `_thread.start_joinable_thread`), with the function that did it;
- the organs and bus slots set at the end, and the scenario's own probes.

The build maps each row onto the static graph. A pair the code already shows becomes `implemented+observed`; a pair it does not becomes an `observed` edge. That is how a call through an untyped local, a delayed callback or a thread target gets a real target. Rows that map to no node are counted, never dropped.

Committed recordings: `desktop_boot` (entry `aurora.boot_aurora`, 2,833 pairs) and `desktop_turns` (entry `aurora.process_external_user_turn`, 4,598 pairs). `check` does not re-run them; a new recording is a deliberate step.

## 8. The ladder: King, quasi, higher order, composite, base

`SUBSYSTEMS.md` and the `Subsystem` nodes follow the ladder in `docs/module_ownership.json` (schema `aurora.module_ownership/2`):

1. **King quasi:** the repository, `subs:king:aurora`.
2. **Quasi:** the domains the record declares: desktop, phone, acm and repo. A file's domain comes from its claim; the ontology's `domain_fallback` covers files the record leaves without one.
3. **Higher order:** the record's subsystems (the category column), each `PART_OF` its declared domain. Members that sit in another domain are listed, not moved.
4. **Composite:** two kinds, kept apart.
   - *Evidence composites* are promoted only on evidence: files bound by calls, flows, spawns or shared state, not by imports alone.
   - *Declared composites* are the record's own. Each import link in one is checked for binding and the composite is marked `supported`, `partly_supported` or `import_only`, with the evidence composite it overlaps most.
5. **Base:** the files, each with its claim check.

Links across domains (a file in one domain joined by implemented or observed edges, or meeting at one endpoint, with a file in another) are listed in `coverage/composites.json` and at the end of `SUBSYSTEMS.md`.

## 9. Claims against the code

Every claim the record makes about a file (layer, subsystem, duties, what it exercises) is checked against what the graph shows the file doing. The result is `consistent`, `conflict` or `unverified`, with the evidence profile behind it. A name is never taken as a job description: a claim with nothing in the code either way stays `unverified`.

## 10. Comparing two builds

`diff` reads two built graphs and writes Markdown plus the full JSON record. Each relationship present in the base and absent in the head is classed:

| class | meaning |
|---|---|
| consolidated | the source still reaches the target through a helper within two calls |
| retargeted | the old target is gone and the source now calls one of the same name |
| delegated | the source's module binds a helper at import time that still reaches the old target |
| folded_into_shared | the function was merged into a shared one that no longer names each field |
| seen_only_in_base_run | a recording difference, not a code difference |
| removed_with_code | the source or target was deleted |
| lost | none of the above: the connection is gone |

It also reports function identity changes, stored state, fault references, developmental records, module dependency shifts, diagnostic (logging) calls, evidence composites by overlap, and focus areas. `comparisons/TRIM_COMPARISON.md` is the comparison of main against the trim branch.

## 11. Coverage on this build

| measure | value |
|---|---:|
| nodes / edges | 34,499 / 160,682 |
| Python modules parsed | 909 |
| Rust, Dart, Kotlin, Java files read by pattern | 47 |
| files listed but not read (data, config, images) | 3,380 |
| method calls in Aurora's code with no static target | 34,972 |
| of which untyped locals / dynamic receivers / untyped attributes | 20,768 / 5,322 / 3,686 |
| library calls and calls on built-in values (not gaps) | 12,457 / 19,679 |
| organs with an implementing class | 100 of 181 |
| nodes a recording entered | 7,289 |
| thread and timer starts confirmed by a recording | 14 of 115 |
| claim checks: consistent / conflict / unverified | 341 / 9 / 557 |

## 12. Limits, stated plainly

- Rust, Dart, Kotlin and Java are read with patterns, not parsers. Calls there are matched by name and carry lower confidence.
- No recording covers the phone runtime past boot, the ACM kernel, Praxis's own server, or work on a timer longer than the recording.
- A call through an untyped value stays unresolved until a recording takes it. The unresolved list is the work queue for annotations and new recordings.
- Impact is potential dependency. It overstates on purpose.
- The mapping is a claim. The graph checks it; it does not replace it.

## 13. Files

| file | purpose |
|---|---|
| `scripts/aurora_knowledge_graph.py` | build, check, query, trace, investigate, diff, schema |
| `scripts/aurora_kg_observe.py` | record a scenario for runtime evidence |
| `knowledge_graph/investigations/PRAXIS_INITIALIZATION.md` | why Aurora can miss that Praxis is initialised |
| `knowledge_graph/comparisons/TRIM_COMPARISON.md` and `.json` | main against the trim branch |
