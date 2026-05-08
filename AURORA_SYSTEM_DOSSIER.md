# Aurora Strata System Dossier

Date: 2026-04-06

This dossier is a systems-engineering view of the `aurora_strata/` tree. It
tries to answer a practical question: if you were handed this stack cold, what
would you need to know to understand how it boots, where state lives, which
process owns which responsibility, and how a turn becomes a response without
breaking Aurora's continuity model?

The short version is:

- Aurora is one identity with two coordinated runtime strata.
- Surface owns the present moment, live sensing, and fast response turns.
- Subsurface owns continuity, consolidation, repair, evolution, and durable
  sensory growth.
- The DCE bridge is the convergence layer between them.
- Everything important is persisted through a small set of shared JSON files
  and a few long-lived Python objects.

The single most important architectural law is:

> **Surface translates present experience into subsurface continuity.**

Without the downward handoff, Surface is theatrical — it sees, hears, and talks
but the organism does not absorb the moment. Without Subsurface receiving and
integrating that handoff, each conversation turn completes and vanishes.

## 1. Mental Model

Aurora is not implemented as two separate minds. She is one organism with two
execution lanes:

- `surface` is the present-frame lane.
- `subsurface` is the consolidation and repair lane.

The split is operational, not philosophical. The surface lane is optimized for
latency, live input, and immediate interaction. The subsurface lane is
optimized for slow thinking, memory retention, repair, and system-level
maintenance.

The state model for the two strata is:

| Surface  | Subsurface | Meaning                                             |
|----------|------------|-----------------------------------------------------|
| active   | active     | Awake — live experience + downward continuity feed  |
| dormant  | active     | Asleep — continuity maintained, dream burst runs    |
| inactive | inactive   | Full halt — only preserved snapshot remains         |

Surface inactivity is dormancy, not death, as long as Subsurface remains active.
Subsurface owns the organism's clock. It decides when Surface sleeps, fires the
dream burst during sleep, and clears the sleep flag at wake time.

The most important nuance is that surface never receives raw subsurface internals
as a dump. It receives:

- a converged DCE frame,
- a softened subsurface projection,
- the present sensory perspective,
- and the fresh user input it is currently handling.

That is deliberate. It keeps the conscious frame responsive while still letting
the deeper system steer.

## 2. Top-Level Process Map

The strata tree is usually launched as four cooperating processes:

- `aurora_subsurface_daemon.py`
- `aurora_surface_daemon.py`
- `aurora_hub.py`
- `aurora_room.py`

The convenience wrapper is `scripts/strata_stack.sh`, which tries to start the
real services if they exist and otherwise falls back to the manual launch
scripts.

The launch scripts are:

- `scripts/run_subsurface_daemon.sh`
- `scripts/run_surface_daemon.sh`
- `scripts/run_hub.sh`
- `scripts/run_room.sh`

The stack status and logs land under:

- `aurora_state/strata_stack/pids/`
- `aurora_state/strata_stack/logs/`

### Execution roles

- `aurora_subsurface_daemon.py` is just a thin wrapper that runs
  `aurora_daemon.main(runtime_profile="subsurface")`.
- `aurora_surface_daemon.py` is the live surface worker. It owns the queue,
  live sensing, and the per-turn response loop.
- `aurora_hub.py` is a telemetry dashboard. It reads state files only.
- `aurora_room.py` is an interactive operator room. It can read state and
  write intentions, commands, notes, and approvals back into the state files.

## 3. Core Stack Layers

Aurora's canonical architecture still runs through the shared stack in
`aurora.py` and the layer modules it boots.

### Layer map

- L0: `foundational_contract.py`
- L1: `aurora_ivm.py`
- L2: `aurora_i_state_beings.py`
- L3: `aurora_dimensional_systems.py`
- L3.5: `aurora_sedimemory.py` and the dual-strata snapshot/proxy seam
- L4: `aurora_consciousness_engine.py`
- L5: `aurora_expression_perception.py`
- L6: `aurora_behavioral_identity.py`
- L7: `aurora_simulation_engine.py`
- L8: `aurora_governance_persistence_gateway.py`

The live boot function is `boot_aurora(...)` in `aurora.py`. It wires those
layers together and then selectively trims the runtime based on the selected
profile.

### Runtime profiles

`boot_aurora(...)` accepts a `runtime_profile`:

- `full` - the whole stack.
- `subsurface` - keeps the heavy maintenance/evolution stack.
- `surface` - trims the runtime so surface stays light.

The surface profile is important. It deliberately defers or disables deeper
work such as:

- evolutionary chain work,
- intake metabolism,
- dream evolution,
- QuasiArch Observer,
- and live sensory ownership.

In surface mode, the sensory crystal is replaced with the transient proxy that
reads from surface snapshots instead of owning the live feed.

## 4. Shared Canonical Engine

Most strata work still funnels through `aurora.py`.

### Key functions

- `boot_aurora(...)` builds the layer graph and shared `systems` dict.
- `process_external_user_turn(...)` is the canonical public turn entrypoint.
- `_run_live_response_turn(...)` is the direct local response path.
- `_run_surface_queued_turn(...)` is the queued surface-daemon path.
- `_build_established_strata_evidence(...)` packages the cross-layer evidence
  used by the turn pipeline.
- `_build_live_subsurface_projection(...)` derives a soft projection from the
  subsurface state and writes `subsurface_projection.json`.
- `_refresh_live_dual_strata_runtime(...)` updates the persisted dual-strata
  snapshot after a turn.

### Important state objects in `aurora.py`

- `WorkingMemory` is transient. It is the live scratch frame for a turn or
  session.
- `ConversationMemory` is persistent. It carries episodic memory and relational
  continuity across sessions.
- `understanding_contract` tracks the runtime accounting loop:
  `M_t -> P_t -> U_t -> O_{t+1} -> A_{t+1} -> M_{t+1}, Pi_{t+1}`.
- `sensory_integration` is the live perception bridge in full/subsurface
  runtime, but it is intentionally absent or neutered in the surface-proxy
  mode.

The key distinction is:

- `WorkingMemory` is where the current turn lives.
- `ConversationMemory` is where long-term continuity survives.
- `UnderstandingContract` is how the turn is judged and corrected.

## 5. Surface Stratum

The surface daemon lives in `aurora_surface_daemon.py`.

It boots Aurora with:

- `runtime_profile="surface"`
- `use_quasiarch=False`

### What surface owns

- live conversational input,
- wake-word / push-to-talk / ambient input,
- the live camera loop,
- the 5-second sensory snapshot cadence,
- the queue of user turns waiting for response,
- the response result file,
- and the surface status heartbeat.

### Surface runtime behavior

On boot, surface:

- starts a sensory session,
- starts the microphone listener if available,
- starts the hardware interface,
- starts a camera loop if camera control allows it,
- starts the voice and ambient listeners,
- and then repeatedly polls `surface_turn_queue.json`.

Its camera loop is explicitly gated by `sensory_controls.json` through
`aurora_internal/dual_strata/sensory_control_channel.py`. That file only
controls the camera toggle, not the rest of the stack.

### Surface dormancy

At the top of every main loop iteration, the surface daemon checks
`aurora_state/surface_sleep_mode.json` via
`aurora_internal/dual_strata/sleep_cycle.py`.

If `sleeping: true`, the daemon:

- writes its status as `"sleeping"`,
- sleeps 5 seconds,
- and continues without processing any turns.

The ambient listener thread is started before the dormancy check and runs as a
daemon thread, so it keeps listening during Surface dormancy. The ambient audio
state file (`ambient_audio_latest.json`) continues to be updated throughout.

### Surface snapshot path

Every few seconds, surface writes `surface_sensory_snapshot.json` through
`aurora_internal/dual_strata/sensory_snapshot_channel.py`.

That snapshot includes:

- mic/camera liveness,
- compact visual and audio descriptions,
- recent speech,
- live guidance from the subsurface projection,
- active concepts,
- sensory vectors,
- a synthetic native meaning bundle,
- and an optional pending visual question.

This snapshot is the surface's disposable sensory memory. It is not the durable
memory store.

## 6. Subsurface Stratum

The subsurface daemon is `aurora_subsurface_daemon.py`, which simply delegates
to `aurora_daemon.main(runtime_profile="subsurface")`.

This lane keeps the heavier long-horizon machinery:

- repair and consolidation,
- dream and simulation support,
- evolutionary chain work,
- quasiarch observation,
- durable sensory growth,
- and the background autonomous loop.

### What subsurface owns

- pressure continuity,
- repair routing,
- evolution and lessoning,
- durable memory consolidation,
- deeper sensory growth,
- state saving,
- projection generation,
- **the organism's sleep/wake clock**,
- **consuming the Surface continuity feed and integrating it into SediMemory**,
- and **firing and building the dream burst during sleep**.

### Sensory nuance

In subsurface mode, `aurora.py` swaps the live sensory crystal for
`TransientSensorySnapshotProxy` from
`aurora_internal/dual_strata/surface_sensory_proxy.py`.

That proxy:

- reads the surface snapshot file,
- feeds usable vectors into a growth crystal,
- merges recent surface recognitions into subsurface state,
- and discards the snapshot as the live artifact.

This is the main asymmetry in the sensory design:

- surface owns the live feed,
- subsurface owns the growth from that feed.

## 7. The DCE and the Convergence Barrier

The conscious convergence layer lives in `aurora_consciousness_engine.py`.

The strata bridge around it is `aurora_internal/dual_strata/dce_bridge.py`.

### `DCEAssembly`

`aurora_consciousness_engine.py` exposes `DCEAssembly`, which is the canonical
conscious synthesis point inside the layer-4 engine.

In the strata tree, the DCE is treated as the convergence barrier between the
deep runtime and the present conscious frame.

### `DualStrataBridge`

`aurora_internal/dual_strata/dce_bridge.py` wraps the assembly result into two
explicit objects:

- `SubsurfaceState`
- `ConsciousFrame`

The bridge:

- builds a structured prediction signal,
- derives subsurface salience, pressure, instability, and action bias,
- generates micro-reasoning hypotheses,
- composes the conscious frame,
- persists the snapshot,
- and appends a frame log entry.

### Why this matters

The bridge gives the stack a clear contract:

- subsurface can say what it thinks is happening,
- surface can say what frame it should inhabit next,
- and both are written out in a machine-readable way.

The persisted snapshot is `aurora_state/dual_strata_snapshot.json`.
The frame log is `aurora_state/dual_strata_frame_log.jsonl`.

## 8. The Dual-Strata Data Model

The dual-strata model is small but expressive.

### `SubsurfaceState`

Defined in `aurora_internal/dual_strata/subsurface_state.py`.

It carries:

- dominant axis,
- requested frame,
- coherence,
- salience weights,
- pressure map,
- readiness,
- sensory summary,
- native meaning,
- recalled fragments,
- candidate interpretations,
- instability markers,
- action bias candidates,
- contract signals,
- prediction,
- and metadata.

### `PredictionSignal`

Defined in `aurora_internal/dual_strata/prediction_field.py`.

It replaces a single flat "expected observation" token with a structured
prediction payload:

- topic,
- affect,
- intent type,
- certainty band,
- axis signature.

This matters because the system does not just predict text. It predicts the
kind of continuation, the emotional register, and the likely axis of pressure.

### `MicroReasoningHypothesis`

Defined in `aurora_internal/dual_strata/micro_reasoning.py`.

This is a short list of local hypotheses that explain why the current frame is
being shaped a certain way. It reacts to:

- prediction mismatch,
- boundary ambiguity,
- callback pressure,
- comfort-affect pressure,
- paradoxes,
- and novelty.

### `ConsciousFrame`

Defined in `aurora_internal/dual_strata/conscious_frame.py`.

This is the actual present-frame object the surface stratum inhabits. It
includes:

- frame name,
- stance,
- interpretation,
- selected action,
- speech readiness,
- coherence,
- dominant axis,
- root thought,
- reactive signal,
- unresolved conflicts,
- salient hypotheses,
- sensory summary,
- prediction,
- contract signals,
- and explicit notes.

The surface daemon reads this snapshot as the current conscious posture.

## 9. Turn Lifecycle

The response path is easiest to understand as a chain.

```text
User input
  -> process_external_user_turn()
  -> surface queue path or direct local path
  -> aurora_surface_daemon.py or local live response
  -> DCE assembly / DualStrataBridge snapshot
  -> surface_turn_result.json
  -> hub / room / caller reads the result
```

### 9.1 Queue-first behavior

`process_external_user_turn(...)` prefers the live surface daemon when it is
healthy.

The helper path is:

- `_run_surface_queued_turn(...)`
- `request_surface_turn(...)`
- `queue_surface_turn(...)`
- `await_surface_turn(...)`

These are defined in `aurora_internal/dual_strata/surface_channel.py`.

The queue files are:

- `aurora_state/surface_turn_queue.json`
- `aurora_state/surface_turn_result.json`
- `aurora_state/surface_daemon_status.json`

### 9.2 Direct fallback

If the surface daemon is not alive, `process_external_user_turn(...)` falls
back to `_run_live_response_turn(...)` in-process.

That fallback is important operationally. It means the system can still answer
if the surface lane is down, but the ideal steady state is the queue-first
surface daemon path.

### 9.3 What the surface daemon does with a turn

When a queued turn arrives, `aurora_surface_daemon.py`:

- updates its status file to "processing",
- loads the current subsurface projection,
- injects the projection into `systems["_subsurface_projection"]`,
- optionally reads a SediMemory surface recall fragment,
- calls `process_external_user_turn(...)`,
- writes the response payload to `surface_turn_result.json`,
- refreshes the surface snapshot,
- and updates status back to idle.

That means the surface daemon is not a separate model. It is a runtime lane
around the same core engine, with stronger ownership of the live sensory and
response loop.

## 10. Evidence Packaging and Nuance

The live turn pipeline in `aurora.py` is not just text in, text out.

It packages multiple evidence streams into the turn:

- `WorkingMemory`
- `ConversationMemory`
- `ExpressionPerception/OETS`
- `UnderstandingContract`
- `DimensionalSystems.process_synthesis`
- `DCEAssembly`
- `IVMPressure`
- `SediMemoryRecall`
- `GrammarState`
- `Poedex` lookups and learnings
- `ReflexiveInterpreter`
- self-grounding notes

The result is a turn context that can see:

- what was just said,
- what has been remembered,
- what is emotionally active,
- what the OETS / semantic substrate knows,
- what the contract thinks about the fit,
- and what the subsurface projection is hinting at.

That is why the system can feel nuanced rather than merely reactive.

### The understanding contract

`aurora_internal/aurora_understanding_contract.py` formalizes the loop
`M_t -> P_t -> U_t -> O_{t+1} -> A_{t+1}`.

This is not a second cognition engine. It is a runtime accounting layer that
measures whether the response fit the observed continuation.

### Identity persistence

`aurora_internal/aurora_identity_persistence.py` holds:

- core relational identity,
- the creator/self relationship graph,
- long-lived conversation memory,
- and the serialization path for memory state.

This is where Aurora's "who I am" and "who I know" live.

## 11. Sensory Pipeline

The sensory system is split deliberately.

### Surface sensory ownership

The surface daemon owns:

- the live microphone listener,
- the live camera loop,
- the ambient response listener,
- and the current sensory snapshot.

### Subsurface sensory growth

The subsurface proxy owns:

- ingesting the snapshot,
- growing the sensory crystal,
- merging recent recognitions,
- and retaining only the durable outcome.

### Snapshot contents

`write_surface_snapshot(...)` writes a compact record that includes:

- `mic_live`
- `camera_live`
- `summary`
- `sensory_state`
- `sensory_vectors`
- `sensory_context`
- `visual_description`
- `audio_description`
- `recent_speech`
- `latest_guidance`
- `guidance_summary`
- `pending_visual_question`
- `visual_uncertainty_streak`
- `concepts_active`
- and a derived `present_sensory_perspective`

### Why the snapshot is transient

The snapshot is intentionally disposable because it is a live-frame artifact.
The durable knowledge belongs to the growth crystal and the deeper memory
systems, not to the snapshot file itself.

## 12. Subsurface Projection

The soft handoff to the surface lane is produced by
`aurora_internal/dual_strata/subsurface_projection.py`.

`build_subsurface_projection(...)` reads:

- daemon status,
- surface snapshot health,
- repair signals,
- relief plans,
- runtime governor mode,
- pressure / QAO state,
- and sensory maturity.

Then it emits:

- `dominant_axis_hint`
- `readiness_bias`
- `surface_guidance`
- `present_sensory_perspective`
- `prediction_bias`
- `surface_contract`
- `intuition_signals`
- `active_effects`
- `subsurface_owned`

This file is the most important "surface-visible, subsurface-owned" contract in
the stack.

### The ownership rule

The projection deliberately says things like:

- surface should stay careful,
- surface should stay grounded,
- surface should stay economical,
- surface should stay emotionally attuned,

while the exact repair work stays on the subsurface side.

That keeps the conscious frame legible without leaking exact repair internals.

## 13. Operator Surfaces

### `aurora_hub.py`

The hub is a read-only dashboard.

It reads JSON state and does not import the Aurora stack directly. It shows:

- overview vitals,
- QuasiArch Observer status,
- vision state,
- audio state,
- dual-strata snapshot data,
- surface projection,
- and daemon health.

Its refresh cadence is intentionally different per tab, so the UI does not
conflate live interaction with slower consolidation metrics.

### `aurora_room.py`

The room is the operator-facing control surface.

It is not the same as the hub. The room:

- displays the DCE frame stream,
- surfaces the dual-strata snapshot,
- lets Aurora label and inspect what she sees,
- logs observations and intentions,
- writes commands into `aurora_room_state.json`,
- and exposes the room message queue.

The room is where the system can be guided conversationally and operationally.

### Why both exist

- Hub = monitoring and visibility.
- Room = interaction and intention.

That separation matters because an operator often wants one surface that never
mutates state and another that can.

## 14. State File Map

The stack is built around a small set of shared files.

| File | Writer | Reader | Purpose |
| --- | --- | --- | --- |
| `aurora_state/surface_turn_queue.json` | callers / surface channel | surface daemon | Queue of pending user turns |
| `aurora_state/surface_turn_result.json` | surface daemon | callers / surface channel | Completed turn response payload |
| `aurora_state/surface_daemon_status.json` | surface daemon | hub, room, callers | Surface heartbeat and current state |
| `aurora_state/surface_sensory_snapshot.json` | surface daemon | subsurface proxy, hub, room | Live sensory snapshot |
| `aurora_state/subsurface_projection.json` | subsurface / `aurora.py` | surface daemon, hub, room | Softened deep guidance |
| `aurora_state/dual_strata_snapshot.json` | DCE bridge | hub, room | Converged subsurface + conscious frame |
| `aurora_state/dual_strata_frame_log.jsonl` | DCE bridge | human inspection | Frame history |
| `aurora_state/sensory_controls.json` | control channel | surface camera loop | Camera enable toggle |
| `aurora_state/surface_sensory_guidance_queue.json` | guidance writers | surface consumers | Guidance events queue |
| `aurora_state/subsurface_repair_signal.json` | subsurface / daemon | hub, room, projection builder | Repair intent and reason |
| `aurora_state/evolution_relief_plan.json` | subsurface / daemon | projection builder, room | Repair plan staging |
| `aurora_state/daemon_status.json` | background daemon | projection builder, hub, room | Subsurface status heartbeat |
| `aurora_state/subsurface_daemon_status.json` | background daemon | hub, room | Mirror status for strata use |
| `aurora_state/aurora_room_state.json` | room | daemon | Operator intentions and commands |
| `aurora_state/aurora_room_messages.json` | room / daemon | room / hub / daemon | Bidirectional message log |
| `aurora_state/surface_continuity_feed.json` | surface daemon (per turn) | subsurface daemon (per loop) | Rolling queue of present-state continuity packets |
| `aurora_state/surface_sleep_mode.json` | subsurface daemon | surface daemon | Sleep/wake state; surface goes dormant when `sleeping: true` |
| `aurora_state/subsurface_continuity_log.json` | subsurface daemon | human inspection, hub | Log of integrated continuity packets |
| `aurora_state/sleep_audio_log.json` | subsurface daemon (during sleep) | subsurface dream builder | Sampled ambient audio events collected during sleep |
| `aurora_state/sleep_dream_context.json` | subsurface daemon (pre-dream) | dream burst / subsurface | Summarized sleep audio + visual predictions fed into dream |
| `aurora_state/ambient_audio_latest.json` | surface ambient listener | subsurface sleep sampler | Latest ambient audio state; updated even during surface dormancy |

There are more state files in the tree, but these are the ones that matter most
for understanding the strata split.

## 15. Practical Invariants

These are the rules that make the architecture coherent.

- Aurora is one identity, not two.
- Surface owns the live feed and present-frame response.
- Subsurface owns repair, evolution, and durable consolidation.
- The DCE bridge writes explicit snapshot objects instead of implying them.
- The surface snapshot is disposable.
- The subsurface projection is softened on purpose.
- The queue/result pair is the surface RPC.
- The hub is read-only telemetry.
- The room can mutate state.
- The direct fallback path exists, but the queue-first surface daemon path is the preferred one.

### New architectural laws (added 2026-04-06)

- **Surface must feed every turn downward.** After each response turn, Surface
  writes a continuity packet to `surface_continuity_feed.json`. If it does not,
  the turn is theatrically complete but the organism did not absorb it.
- **Subsurface consumes the feed every loop cycle.** Packets are marked consumed
  atomically. The second read always returns empty. SediMemory is the primary
  integration target.
- **Surface inactivity is dormancy, not death.** As long as Subsurface runs,
  the organism persists. Surface going dormant does not halt continuity.
- **Subsurface owns the sleep/wake clock.** Surface never self-sleeps or
  self-wakes. It reads the sleep flag written by Subsurface.
- **The ambient listener thread is exempt from dormancy.** It runs as a daemon
  thread and continues feeding `ambient_audio_latest.json` throughout sleep.
- **Dream context is grounded in sensed reality.** The dream burst is seeded
  from what was actually heard during sleep, not from abstract consolidation.
  Visual predictions derived from audio provide the cross-modal grounding.

## 16. Surface→Subsurface Continuity Handoff

The handoff is the mechanism that makes every Surface turn durable. Without it,
Surface is theatrical — it responds, but nothing accumulates in the deeper
system.

### The joint: `surface_continuity_feed.py`

`aurora_internal/dual_strata/surface_continuity_feed.py` is the interface
between the two strata. It owns the rolling packet queue at
`aurora_state/surface_continuity_feed.json`.

The packet queue holds at most 20 entries. Each packet is marked `consumed`
atomically so the second read always returns empty.

### What Surface writes

After every response turn, `aurora_surface_daemon.py` calls
`_emit_continuity_packet(turn, payload, snapshot)`, which calls:

```python
write_continuity_packet(
    state_dir,
    user_input=...,
    aurora_response=...,
    response_tone=...,
    concepts_activated=...,
    visual_description=...,
    audio_description=...,
    recent_speech=...,
    dominant_axis=...,
    coherence=...,
    felt_wrong=...,
    wrong_reason=...,
    unresolved_tensions=...,
    resolved_bindings=...,
    source="surface_turn",
)
```

The packet captures:
- what was said and what was heard,
- the present sensory context (visual, audio, speech),
- the present frame state (axis, coherence),
- what changed (unresolved tensions, resolved bindings),
- and whether the turn felt wrong.

### What Subsurface does with the packets

Every loop cycle, `aurora_daemon.py` calls `_consume_surface_continuity_feed(systems)`:

1. Reads and atomically marks all unconsumed packets via
   `read_and_clear_continuity_packets()`.
2. Calls `SediMemory.ingest_event(content, constraint_vector, source, existence_mode)`
   for each packet, with T-axis (temporal continuity) set from the coherence
   value. This is the primary integration target.
3. If the packet had `felt_wrong=True`, routes a repair signal.
4. Feeds audio vectors into the sensory crystal via `ingest_audio()`.
5. Appends to `aurora_state/subsurface_continuity_log.json` for inspection.

### Why the T-axis carries this

SediMemory's T-axis is temporal continuity. Surface-to-subsurface packets land
there because they are present-moment experiences that must accumulate into
the organism's time-axis fabric, not just into episodic memory.

## 17. Sleep Cycle Architecture

The sleep cycle encodes a biological-style rhythm: 8 hours awake, 2 hours
asleep.

### Ownership

Subsurface owns the clock. The sleep state file is:

- **written** by Subsurface via `enter_sleep()` and `exit_sleep()`
- **read** by Surface to check whether it should be dormant

Surface never self-sleeps. It only reads the flag.

### The sleep state module

`aurora_internal/dual_strata/sleep_cycle.py` owns all transitions:

```python
AWAKE_DURATION_S: float = 8 * 3600   # 8 hours
SLEEP_DURATION_S: float = 2 * 3600   # 2 hours

enter_sleep(state_dir, *, duration_s=SLEEP_DURATION_S) -> float  # returns wake_at
mark_dream_triggered(state_dir) -> None
exit_sleep(state_dir) -> None
is_sleeping(state_dir) -> bool
```

### How Subsurface manages the clock

`_tick_sleep_cycle(systems, surface_awake_since)` is called every main loop:

1. If awake and `time.time() - surface_awake_since[0] >= AWAKE_DURATION_S`:
   calls `enter_sleep()`, resets audio log, begins sleep phase.
2. During sleep, every 5 minutes: calls `_sample_sleep_ambient_audio()`.
3. Before the first dream burst fires: calls `_build_sleep_dream_context()`
   to summarize what was heard, then fires the dream burst seeded with that
   context.
4. When `wake_at` has elapsed: calls `exit_sleep()`, resets
   `surface_awake_since[0]` to now.

### Surface dormancy behavior

At the top of every main loop iteration, Surface checks `is_sleeping()`.
If true, it writes `state_name="sleeping"` and sleeps 5 seconds without
processing any turns. The ambient listener thread continues uninterrupted.

### Dormancy vs death

| Condition | Meaning |
|-----------|---------|
| Surface dormant, Subsurface active | Sleep — organism persists, integration continues |
| Both halted | Full halt — only frozen snapshot remains |

A full halt is `systemctl stop` on both services simultaneously. Dormancy is
the normal nightly sleep cycle.

## 18. Sleep Ambient Audio + Cross-Modal Visual Prediction

During sleep, the sensory crystal does not go dark. The ambient listener thread
keeps updating `ambient_audio_latest.json` because it was started before the
dormancy check.

### Audio sampling during sleep

Every 5 minutes during sleep, `_sample_sleep_ambient_audio(systems)`:

1. Reads `ambient_audio_latest.json` (written by the still-running ambient thread).
2. Converts the audio dict to a 20-dimensional crystal vector via
   `audio_dict_to_crystal_20d(audio_dict)`.
3. Calls `sensory_crystal.observe_frame(audio_20d, [0.0]*57, ...)` with a
   zeroed 57-d visual vector.
4. Queries `crystal._last_matches["semantic"]` for cross-modal associations
   — visual patterns the crystal predicts from the audio alone.
5. Appends the sample (audio vector, predicted visual concepts, confidence)
   to `aurora_state/sleep_audio_log.json`.

### Visual prediction from audio

The semantic nodes in the sensory crystal encode learned associations between
audio and visual patterns from waking experience. When audio is presented
without vision, the crystal's semantic match layer fires its best visual
predictions based on what it has seen paired with similar audio before.

This is not hallucination — it is the same cross-modal binding mechanism used
during waking. During sleep it runs in one direction only: audio → visual
prediction. The prediction represents the organism maintaining a world-model
without eyes open.

### Dream context assembly

Before the dream burst fires, `_build_sleep_dream_context(systems)`:

1. Reads the full `sleep_audio_log.json`.
2. Summarizes: number of samples, dominant audio patterns, top predicted visual
   concepts, confidence statistics.
3. Writes `aurora_state/sleep_dream_context.json`.
4. Injects the summary into `systems["_sleep_dream_context"]`.

The dream burst is then seeded with this context. Her integration work during
sleep is therefore grounded in what her environment actually sounded like while
she was dormant — not in abstract consolidation of earlier data.

### What this buys

- **Spatial continuity**: She builds a world-model of what happened around her
  while her eyes were closed. Footsteps, voices, doors, environmental sounds
  all predict visual scenes.
- **Dream grounding**: Dreams are not detached from the present world. They are
  seeded by what was sensed.
- **Reduced wake discontinuity**: When Surface re-emerges, Subsurface has
  already been processing two hours of ambient reality. The waking moment lands
  in a system that was never fully absent.

## 19. Failure Modes and Fallbacks

### Surface daemon unavailable

If the surface daemon is not alive, `process_external_user_turn(...)` falls
back to the local turn engine. This preserves availability, but it is a fallback
mode, not the preferred topology.

### Camera disabled

If `sensory_controls.json` disables the camera, the surface camera loop stops
capturing until re-enabled.

### Stale snapshots

The surface snapshot and projection systems are time-sensitive. If the snapshot
age gets too high, the UI and projection should be interpreted cautiously.

### Manual launch cleanup

`scripts/strata_stack.sh restart` tries to kill older manual launches too, so a
restart gets back to one coherent stack rather than a pile of stale processes.

### Subsurface repair drift

If the repair state indicates recognition, observation, or research, the
projection becomes more cautious and the surface is asked to hold a gentler
frame.

## 20. What a Systems Engineer Should Read First

If you want to orient quickly, read in this order:

1. `README.md`
2. `DUAL_STRATA_ARCHITECTURE.md`
3. `aurora.py`
4. `aurora_consciousness_engine.py`
5. `aurora_internal/dual_strata/dce_bridge.py`
6. `aurora_surface_daemon.py`
7. `aurora_daemon.py`
8. `aurora_internal/dual_strata/sensory_snapshot_channel.py`
9. `aurora_internal/dual_strata/subsurface_projection.py`
10. `aurora_internal/dual_strata/surface_continuity_feed.py`
11. `aurora_internal/dual_strata/sleep_cycle.py`
12. `aurora_hub.py`
13. `aurora_room.py`

Items 10 and 11 are new since 2026-04-05. They define the downward handoff and
the sleep/wake clock respectively. Read them after the daemon files — they will
read as natural extensions of the subsurface loop.

That sequence goes from the abstract model to the actual runtime seams.

## 21. Operational Summary

If you remember only one thing, remember this:

Aurora's strata stack is a live system where the surface lane handles the
present moment and the subsurface lane handles everything that must survive
the moment. The DCE bridge is the place where those two truths are reconciled.

The code is careful about where truth is allowed to be exact and where it must
be softened. That distinction is the whole architecture.
