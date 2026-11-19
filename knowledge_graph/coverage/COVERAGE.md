# What the knowledge graph covers, and what it does not

Authors: Sunni (Sir) Morningstar & Cael Devo  
Source commit `0d0794ec21a4`, generator 2.0.0.

Nothing here is hidden by a summary: every unresolved call site is in `unresolved_calls.jsonl`, every file's status in `files.jsonl`, every claim check in `claims.json`, and every statically reachable function that no recorded run entered in `unobserved.json`.

## Files

| status | files | meaning |
|---|---:|---|
| not_analysed | 3397 | data, config, images and other files: listed, not read |
| parsed_ast | 955 | Python, parsed with ast: calls, state, flow |
| scanned_references | 111 | Markdown: the code, stores and organs it names |
| parsed_regex | 52 | Rust, Dart, Kotlin, Java: read with patterns, calls matched by name |
| scanned_launches | 35 | shell, workflows, service units, web: only the modules and scripts they launch |

## Calls without a resolved target

36632 method calls inside Aurora's code have no static target. External library calls and calls on built-in values are listed with their reason but not counted as gaps.

| reason | sites | what would resolve it |
|---|---:|---|
| untyped_local | 21713 | a type the code does not state (assignment from an untyped call) |
| builtin_value | 20152 | nothing: str, dict, list and similar |
| external | 12980 | nothing: a library outside the repo |
| dynamic_receiver | 5588 | the result of a call or subscript; runtime evidence |
| untyped_attribute | 3857 | self.x whose class is never stated; an annotation or runtime evidence |
| untyped_module_state | 2036 | a module global whose type is not stated |
| untyped_parameter | 1381 | a parameter without an annotation |
| unknown_member | 1330 | a name the target class or module does not define (dynamic or inherited from outside) |
| organ_receiver | 727 | systems[key] where the organ has no single implementing class |

## Edge basis

Every edge says how it is known. implemented: read from code. declared: stated in a document, the ownership mapping or the ontology. inferred: a grouping or a name match. observed: a recorded run took it.

| basis | edges |
|---|---:|
| implemented | 143387 |
| declared | 13046 |
| observed | 4856 |
| implemented+observed | 3720 |
| inferred | 1625 |
| implemented+inferred | 2 |

## Runtime evidence

Recorded scenarios: desktop_boot, desktop_turns. 7334 nodes were observed. 4572 functions are statically reachable from the desktop entry points but were not entered in any recorded run.
- `desktop_boot`: entry `aurora.boot_aurora`, completed True, 2833 call pairs, 350.4 s
- `desktop_turns`: entry `aurora.process_external_user_turn`, completed True, 4598 call pairs, 39.9 s

Paths no recording covers: the phone runtime past the boot stages listed, the ACM kernel (bare metal), Praxis's own server, and any code that only runs on a timer longer than the recording.

## Declared ownership and its boundary

Layer and category come from `docs/module_ownership.json` (aurora.module_ownership/2, sha256 0969b8b59565d491). They are claims, kept apart from what the code and the runs show.

> Covers every source file in the repository: desktop Aurora's Python (runtime, scripts and tests), the phone app's Dart, Kotlin, Java and Python, the ACM's Rust and Python, launchers, service units, prototypes and CI workflows. Data, state, documentation and build configuration are not source and are listed below.

Not covered by the mapping:
- `aurora_state/, aurora_state_test/, aurora_logs/, vector_data/, lessons/, aurora_genealogy/`: Runtime state, logs, lessons and genealogy data
- `docs/ and root .md files`: Documentation, install notes and build reports
- `root .json and .jsonl files`: Maps, audits, manifests and run history
- `Cargo.toml, pubspec.yaml, Gradle files, buildozer.spec, requirements and pytest.ini`: Build and dependency configuration
- `flutter_app/android/ resources and manifests`: Android resources and XML configuration

Claim checks: conflict 9, consistent 360, unverified 586.

1 mapped path(s) have no module in the tree: `knowledge_graph/index.html`

## Reading impact

`query --impact` lists potential dependents: code with a static or observed path to the node. It is not a prediction that a change breaks them. Each dependent carries the lowest confidence and the basis on its path.
