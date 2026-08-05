# Aurora Build 591 Native System Introspection

This repair adds a native diagnostic bridge to Aurora's existing introspection,
understanding, runtime-fault, QuasiArch, attribution, evolutionary-trace, and
code-lineage systems. It does not replace her reasoning, language generation,
or autonomous improvement systems.

## Runtime files

Replace these files with the supplied versions:

- `aurora.py`
- `aurora_daemon.py`
- `aurora_expression_perception.py`
- `aurora_internal/aurora_proposition_frame.py`

Add this new file:

- `aurora_internal/aurora_system_introspection.py`

Optional regression test:

- `tests/test_system_introspection_bridge.py`

The corrected semantic probe battery already installed for the wh-object repair
should remain in place. It does not need to be replaced again for this update.

## What Aurora gains

At boot, Aurora derives a function map from the Python source she is actually
running. The map records module, class/function identity, signature, current
source location, calls, reads, writes, and branch count.

For each external response turn, Aurora now records a bounded diagnostic episode
covering important meaning-changing boundaries, including:

- utterance parsing,
- proposition-frame construction,
- interrogative normalization,
- SentenceComposer slot binding,
- composer emission or abstention,
- final response arbitration.

When a fault or recurring issue is detected, the bridge correlates this trail
with Aurora's existing runtime-fault ledger, understanding contract,
communication attribution, evolutionary traces, QuasiArch observations, and
manual code-lineage status. It returns likely functions, current source files
and lines, the relevant input and derived decision, confidence, and a backward
value trail.

Observed decision boundaries outrank guesses. When direct provenance is absent,
Aurora may return a clearly labeled, lower-confidence source-map hypothesis for
further inspection.

The daemon now gives Aurora's local diagnosis first inspection rights before it
asks Poedex for supplementary research guidance. The local diagnosis is also
published into the understanding contract and QuasiArch observer context.

## Generated instance-owned state

Each runtime state directory receives:

- `system_introspection_index.json`
- `system_introspection_episodes.jsonl`
- `last_introspection_episode.json`
- `last_system_diagnosis.json`

Mutable episodes and diagnoses remain isolated by `state_dir`. Only immutable,
source-derived anatomy may be reused in memory between same-repository runtime
instances.

## Runtime access

```python
bridge = systems["system_introspection"]

bridge.describe_function(
    "aurora_expression_perception.SentenceComposer._bind_slot_from_frame"
)
bridge.diagnose_latest()
bridge.trace_value("who")
bridge.render_diagnosis()
bridge.status()
```

## Verification performed

- 131 focused regression tests passed.
- All changed runtime modules compiled successfully.
- A real `runtime_profile="surface"` boot completed.
- Aurora delivered: `My creator is Sunni (Sir) Morningstar.`
- The turn recorded parser, proposition-frame, composer, and arbitration steps.
- During the same live run, Aurora's diagnostic bridge independently localized
  a nonfatal existing `AttributeError` to the current AST-resolved function
  `aurora.AxisProjector.project` in `aurora.py`, rather than trusting a stale
  hardcoded handler-line number.
