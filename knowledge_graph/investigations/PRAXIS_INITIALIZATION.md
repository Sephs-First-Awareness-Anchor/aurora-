# Why Aurora can fail to recognise that Praxis is initialised

Authors: Sunni (Sir) Morningstar & Cael Devo

Source: main at `f5c7beb`. Graph: `knowledge_graph/` built from that commit with the desktop boot and turn
recordings. The graph's own trace is `aurora_knowledge_graph.py investigate praxis`; this note reads it together
with the code it points at. Each finding is marked **seen** (read in the code or recorded in a run) or
**inferred** (follows from what was seen, not observed on a device).

## Short answer

"Praxis is initialised" means four different things in Aurora, and they become true at different times:

1. the Praxis server is up (outside Aurora);
2. `aurora_praxis_bridge.start_praxis_bridge` returned a bridge (the start record says `started`);
3. the bridge has completed a handshake with the server (`discovery == "compatible"`, `online`);
4. the organism actually holds what Praxis sent.

Every reader checks only one of them, and two of the gaps are structural:

- The bridge only asks the server who it is when the field is idle, so (1) can be true for a long time while (3) stays false and the Hub says `offline`.
- The bridge writes its context into a private copy of the systems dict, so (4) never reaches the rest of Aurora even when (2) and (3) are true.

## The path, step by step

### 1. The initialisation event

**Seen.** `AuroraService.onCreate` launches `bootPython()` (AuroraService.kt:518). That calls
`aurora_bridge.initialize(stateDir)` (AuroraService.kt:754) on the service's IO coroutine scope.
`initialize` (aurora_bridge.py:2486) runs in this order:

| step | line | state it changes |
|---|---|---|
| `_boot_state = {"stage": "initialize() entered", "finished": False}` | 2488 | boot stage |
| `_systems = _aurora.boot_aurora(...)`, under `_lock` | 2565 | the organism exists; every stats reader now answers |
| `_boot_completed_at = time.time()` | 2581 | the background-work clock starts: "boot completed" for every idle predicate |
| historical stages, then `absorb_harvest(_systems)` under `_lock` | 2813-2817 | clone harvest |
| `start_historical_experience_environment` | 2822 | |
| `_praxis = start_praxis_bridge(_systems, ...)` | 2860 | the bridge exists, its thread `aurora-praxis` starts |
| `_systems["praxis_bridge"] = _praxis` | 2868 | |
| messenger, learning probe | 2896-2915 | |
| `_boot_state["finished"] = True`, return `"ready"` | 2933-2941 | Kotlin emits the `ready` event (AuroraService.kt:794) |

### 2. Who reads it, and what they read

**Seen.** The graph's cross-language trace gives the read path:

Dart `PraxisBridge.status` (praxis_bridge.dart:78) → MethodChannel `getPraxisStatus` → Kotlin
`MainActivity.configureFlutterEngine` (MainActivity.kt:329) → `AuroraService.callPythonString("get_praxis_status")`
→ Chaquopy → Python `get_praxis_status` (aurora_bridge.py:2368) → `_praxis.status()` or `_praxis_absent_status`.

The Hub row takes a second path. It reads `get_cognitive_stats` (aurora_bridge.py:11571), which builds `praxis_status`
from the same two sources at 11823-11830.

Five places can turn a live state into "not_initialized" or "offline" on the way:

| place | what it answers | basis |
|---|---|---|
| `get_cognitive_stats` line 11581 | `{"error": "not_initialized"}` while `_systems is None`; every praxis key is then missing | seen |
| `_praxis_absent_status` 2349 | `status` stays `"not_initialized"` in all four absent cases (FIX-A117); only `init_phase` says which | seen |
| Kotlin `callPythonString` (AuroraService.kt:237-244) | any Python exception becomes `"{}"`; when `scope` is null (after `onDestroy`) the callback never fires and the Dart call never completes | seen |
| Dart `PraxisStatus.fromJson` (praxis_bridge.dart:49) | `status ?? 'not_initialized'`. It drops `init_phase` and `init_detail`, so the Praxis screen cannot say why. The Hub row keeps them (hub_screen.dart:719-725) | seen |
| `PraxisBridge._status_label` (aurora_praxis_bridge.py:1166-1180) | `"offline"` whenever `online` is False, including before the first handshake, so "never asked" and "unreachable" look the same | seen |

### 3. Where behaviour diverges

**A. The boot window (seen in code and in a run).**
`_systems` is set at line 2565, so the Hub and stats answer from then on. The bridge starts only after the clone harvest.
`absorb_harvest` (aurora_clone_harvest.py:718) hashes the bundled 15 MB `aurora_clone_harvest.jsonl.gz` and stops early only if the ledger already holds that file's signature. Otherwise it streams every segment through the organs while `initialize` holds `_lock`.

In this container, on main, the phone `initialize` stayed at stage `absorbing clone harvest` from about 150 s until the 1,500 s timeout. The Praxis start was never reached. Throughout that run:

- `get_praxis_status` answered `not_initialized` with `init_phase: boot_pending, init_detail: absorbing clone harvest`;
- the desktop `ready` had not been sent.

**Inferred:** the window comes back on any boot after an app update that ships a new harvest file, and it is longer on a phone than in this container.

**B. Recognition waits for an idle field (seen).**
The bridge loop (`_run`, aurora_praxis_bridge.py:1145) calls `_channel_open()`, which does the handshake, only after `_capacity()` is true. `_capacity` is `live_idle`, which `initialize` sets to `_praxis_live_idle` → `_historical_experience_live_idle` (aurora_bridge.py:2246). That predicate returns False whenever:

- `_lock` is held (every live turn, the harvest, and each historical-experience witness event);
- output was produced in the last 8 s;
- less than 120 s (`BOOT_SETTLE_S`) has passed since `_boot_completed_at`;
- less than 20 s has passed since the lock was last released;
- a Praxis messenger DM is waiting (`_messenger_waiting`, 2230). Praxis's own messenger therefore keeps the Praxis bridge from asking whether Praxis is there.

The handshake is only a network call to `/hello`. It never touches the field, yet it is gated as if it did. Until it runs, `online` stays False and the status says `offline`.

**Inferred:** this is the most likely cause of "Praxis finished initialising but Aurora does not see it". It needs nothing to fail, only a busy or settling field.

**C. What Praxis sends never reaches Aurora's shared state (seen).**
`PraxisBridge.__init__` stores `self.systems = dict(systems or {})` (aurora_praxis_bridge.py:383), a shallow copy taken at start. `_witness` writes the current situation to `self.systems["_praxis_context"]` (779), and the comment says "her own organs may inspect it".

They cannot. The write goes into the bridge's private copy, and the graph shows `bus:_praxis_context` as written and never read anywhere in the repo, apart from `tests/test_praxis_contract_fence.py:217`, which reads `bridge.systems`, the same copy.

Every other Praxis-side component keeps the shared dict:

- `PraxisMessenger` (aurora_praxis_messenger.py:370);
- `PraxisInitiative` (aurora_praxis_initiative.py:121);
- `LearningProbe` (aurora_learning_probe.py:92);
- the historical experience environment (aurora_historical_experience_environment.py:190).

Situations still cross through the sensor gateway: `_gateway_parts` (aurora_praxis_bridge.py:699) reads the `aurora` object out of the copy, and the copy holds the same object. Only the context record is cut off.

**D. A second boot in the same process (inferred, not observed).**
`onDestroy` cancels the coroutine scope (AuroraService.kt:835) but stops neither Python nor the bridge, and nothing calls `stop_praxis_bridge`. If Android recreates the service in a live process:

- `initialize` builds a new `_systems`;
- `start_praxis_bridge` returns the existing `_bridge` singleton (aurora_praxis_bridge.py:1246), which still holds its copy of the old dict and the old `aurora` object;
- the bridge would report `online` and witnessed situations while feeding an organism the app no longer uses.

`initialize` has no re-entry guard, and the app never stops `AuroraService` itself, so this needs the system to restart the service without killing the process.

**E. Desktop never starts Praxis (seen).** The desktop boot in `aurora.py` has no call to `start_praxis_bridge`. Both desktop recordings show the `praxis_bridge` organ unset. On the desktop, Praxis is "not initialised" by design.

### 4. Persistence across runtime boundaries

**Seen.**
- The bridge persists `episode_id` and its counters through `_persist_state` (aurora_praxis_bridge.py:1061) into `<state_dir>/praxis/`, and keeps its offline spool there.
- The start record (`_start_record`, 1222) and `_boot_state` live only in process memory. After a process restart they begin again at `never_attempted` and an empty stage, so the reason for the last failure is gone.
- `last_boot_health.json` is the only durable boot record (AuroraService.kt:770-780), and it does not carry the Praxis phase.

## Suggested repairs (not made; for review)

1. Move the handshake out of the capacity gate. Run discovery on its own timer and keep only `pull_once` behind `_capacity()`. Status could then show `discovered` or `unreachable` instead of `offline` before the first ask.
2. Keep the shared dict in the bridge (`self.systems = systems`), as the messenger does, so `_praxis_context` reaches the organs. Add a test that reads `_systems["_praxis_context"]` rather than `bridge.systems`.
3. Carry `init_phase` and `init_detail` through `PraxisStatus.fromJson`, so the Praxis screen says what the Hub says.
4. Make `_praxis_absent_status` return `status: "boot_pending"` (and the other phases) rather than `not_initialized` for every case, or have the Dart side read `init_phase` first.
5. Add a re-entry guard to `initialize`, and call `stop_praxis_bridge` before a second boot.
6. Write the Praxis phase into `last_boot_health.json`.

## What would confirm it on a device

- Run `scripts/aurora_kg_observe.py phone --state <copy of the phone's state> --deadline 1800` on a state whose clone ledger already holds the bundled harvest. The boot then passes the harvest and records `final_boot_state` and the `praxis` probes, including `systems_slot_set` and `thread_alive`.
- Then, with a Praxis server on the endpoint, log the time of the first `/hello` against `_boot_completed_at` and `_lock.last_released`.
