# Aurora Unified Directive — Repository Audit, Stage A

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-11 · **Audited commit:** `375afe0` (main)
**Directive:** Unified Cognitive Architecture and Developmental Optimization Directive (supersedes the earlier Persistent Subsurface / Distributed Surface directive, which it contains).

This is the Stage A deliverable: what the repository actually contains, measured against the directive. Everything below was read from the code at the commit above. Nothing here is a proposal described as finished work; the status table at the end says exactly what changed.

---

## 1. The finding that reorders the plan

**The surface/subsurface split already exists. What does not exist is any way for the two strata to be on different machines.**

- `aurora_subsurface_daemon.py` runs `aurora_daemon.main(runtime_profile="subsurface")`; `aurora_surface_daemon.py` is the surface. `deploy/` holds four systemd units (`Restart=always` on the subsurface), and `scripts/strata_stack.sh` starts and stops the stack. Part III §7's "independent persistent service that restarts" is largely built for a Linux desktop.
- The two strata talk through **JSON files in one shared `aurora_state/` directory**. There is no socket, HTTP, or other network transport between them anywhere in the repo. The only network clients are Praxis (bridge and messenger), image ingestion and research tools.
- The phone does not run the subsurface at all. `flutter_app/.../aurora_bridge.py` boots the whole of Aurora in-process under Chaquopy and says so itself (line ~2651: the Android path never runs `aurora_daemon.py`). It starts only `SubsurfacePresenceRuntime`, the lightweight file-based presence loop.

So the directive's distributed architecture is not a refactor of cognition. It is one missing piece: **a carrier that moves the existing strata channels between a phone state directory and a desktop state directory.** The directive's own constraint ("do not introduce parallel replacement systems when existing components can be extended") points the same way.

## 2. The strata contract as it exists (state ownership map)

Each channel has exactly one writer today. This is the ownership document Part XIV §41 asks for, read from the code.

| Channel file (`aurora_state/`) | Writer (owner) | Reader | Direction |
|---|---|---|---|
| `surface_continuity_feed.json` | surface (`aurora.py` ~26365, `aurora_surface_daemon.py` 661) | subsurface (`aurora_daemon.py` 8030) | up |
| `subsurface_turn_events.json` | surface (`subsurface_presence.write_turn_open / write_interpreted_turn / write_evidence_need`) | presence runtime, `aurora_daemon._consume_subsurface_turn_events` | up |
| `surface_sensory_snapshot.json` | surface | subsurface (sensory growth) | up |
| `surface_turn_queue.json` / `surface_turn_result.json` | caller / surface daemon | surface daemon / caller | local to surface |
| `subsurface_projection.json` | subsurface (`subsurface_projection.build_subsurface_projection`) | surface | down |
| `predictive_frame_queue.json` | subsurface (`PredictiveStager.stage_passes_for_tick`, `aurora_daemon.py` 9557) | surface (`pop_staged_frames`, `harvest_into_systems`) | down |
| `surface_sensory_guidance_queue.json` | subsurface | surface | down |
| `subsurface_presence_frame.json`, `subsurface_evidence_bindings.json` | subsurface presence | surface | down |
| `subsurface_heartbeat.json`, `subsurface_daemon_status.json`, `surface_daemon_status.json` | each daemon | hub, each other | health |
| Scout requests / reports (`aurora_internal/scouting/`) | surface asks, scout worker answers | both | both |

Three properties matter for distribution:

1. **Anticipatory delivery is already the design.** `PredictiveStager` exists so the surface "never needs to block-wait for Subsurface" (its own docstring); the subsurface stages frames ahead of demand. Part III §9–10 describes this mechanism, not a new one.
2. **Queues are read-and-clear with small caps** (`_MAX_PACKETS = 20` continuity packets, 8 predictive frames). They have no sequence numbers, acknowledgments, or durable outbox. Across a network that means loss on any disconnect. This is the real gap against Part XIV §40 and Part XIII §39.
3. **There is no session epoch or surface-ownership record.** Nothing prevents two surfaces writing the same queue. Part XI (migration, single authoritative surface) has no existing mechanism to extend; it has to be added, and the channel carrier is the natural place.

## 3. Verified defects

### 3.1 Phone continuity packets have no consumer (verified by reading both ends)
`aurora.py` writes a continuity packet after every live turn. The only reader is `aurora_daemon.py`, which the phone never runs. On the phone the feed fills to 20 packets and every later turn pushes the oldest one out, unread. The doctrine "the surface should already be feeding everything it experiences down to the subsurface" is honored on the write side and dropped on the read side. **Not fixed in this change**: the fix is the carrier in §5, which gives this feed its consumer.

### 3.2 Praxis "not initialized despite having been started" (fixed — FIX-A117)
Cause found in the code, in two parts:

- The Praxis bridge and messenger are the **last two stages** of `aurora_bridge.initialize()`. They start only after `boot_aurora()`, curiosity, presence, scout, habitat, **clone-harvest absorption (run synchronously under `_lock`)** and the historical-experience start. Until then every status call returns `not_initialized`, with nothing saying boot is simply still at an earlier stage. If any earlier stage raises out to the outer handler, Praxis is never attempted at all, with the same status.
- `aurora_praxis_bridge.start_praxis_bridge` wrapped the constructor in `except Exception: return None`. A real start failure lost its reason; the app logged "did not start" and reported `not_initialized`.

One status stood for four states. The fix gives start state a single owner per level and reports which case it is (`boot_not_begun`, `boot_pending` + the stage name, `boot_aborted` + stage and error, `start_failed` + error, `never_attempted`). See `known_fixes_registry.md` FIX-A117.

**What this does and does not establish.** It makes the phone tell you which of the four is happening. It does not by itself prove which one you have been seeing; that needs one look at the Hub after installing this build. If it reads `boot pending: absorbing clone harvest` for a long time, the next change is to stop that stage blocking Praxis.

### 3.3 Messages arriving but not answered
Not diagnosed here. The messenger already records why it withheld (`last_withheld`, `withheld_reasons`, `busy_skips`), so delivery and cognition can be told apart from the Hub. Tracing a withheld message through recognition → thought → expression needs a live boot and is Stage B work.

## 4. What exists, what is partial, what is absent

| Directive area | State in repo |
|---|---|
| Surface/subsurface as two strata of one Aurora (Part I, III) | **Exists** on one machine (`dual_strata/`, two daemons, DCE bridge) |
| Persistent subsurface service, auto-restart (§7) | **Exists** for Linux systemd. No Windows service. |
| Anticipatory subsurface → surface (§9) | **Exists** (`PredictiveStager`, projection, guidance queue) |
| Surface → subsurface raw feed (§9) | **Partial**: written everywhere, consumed only on desktop (§3.1) |
| Network transport, sequence/ack, durable queues (§39–40) | **Absent** |
| Latency-tolerant surface (§10) | **Exists by construction**: the phone runs full cognition locally |
| Independent surface operation (§35) | **Exists**: the phone is fully independent today; `aurora_offline_resilience.py` also present |
| Surface migration, epochs, single owner (§34) | **Absent** |
| Clones off the phone (Part X) | **Exists, on GitHub runners not the desktop** (`aurora-clones.yml`, `aurora_clone_harvest.py`): per-clone yields, merge by convergence, divergences kept, nothing arrives promoted, absorption through each organ's own rules. This already meets most of §31–33. A→B / B→A order experiments (§32) are **absent**. |
| Learning stages raw → provisional → consolidated (§29) | **Partial**: organs have their own promotion rules; no cross-strata provisional/consolidated distinction because there is no cross-machine learning yet |
| Consequence-driven recursion, dependency tracking (Part V) | **Not audited.** See §6. |
| Understanding-to-expression path (Part VI–VII) | **Not audited in this pass.** Prior audits exist (PF1–PF3, build 768); they need re-verifying against current code, per §5 of the directive. |
| Baseline measurements (§43) | **Not taken.** See §6. |

## 5. Implementation plan, reordered by the evidence

The directive permits reordering when the repository justifies it (§49). It does:

1. **Stage D first slice — the strata link.** One module beside the existing channels (`aurora_internal/dual_strata/`), no new cognition:
   - carries exactly the channels in §2, in their existing payload shapes, between two state directories;
   - adds what the files lack: per-channel sequence numbers, acknowledgments, a durable outbox on each side, idempotent apply, heartbeat;
   - adds a **session epoch + active-surface record** owned by the subsurface, which is also the foundation for migration (Stage G);
   - desktop side attaches to the already-running `aurora_daemon` consumers (`read_and_clear_continuity_packets`, `_consume_subsurface_turn_events`) unchanged; phone side attaches to the already-running writers unchanged.
   The phone keeps its full local cognition, so losing the link costs depth, never responsiveness. That satisfies §8, §10 and §35 without touching the surface.
2. **Stage B in parallel** — the Praxis follow-up from §3.2 once the Hub reports the phase, and the withheld-message trace (§3.3).
3. **Stage F is mostly a relocation**: point the existing clone runner at the desktop as an additional place to run, keep GitHub runners; add the order experiments.
4. **Stage C (consequence-driven computation) only after a measured baseline.** Changing recursion in a 41k-line `aurora.py` without a baseline would be exactly the unmeasured optimization the directive forbids (§43, §45).
5. **Stage G** on top of the link's epoch record. **Stage H** throughout.

## 6. What this audit did not do

- **No efficiency audit.** Part XIII and Part V require evidence for each finding (duplicate computation, repeated retrieval, competing loops). That needs instrumented runs of a booted Aurora, not reading. None were run.
- **No baseline measurements.** None of the §43 figures were taken.
- **No information-pathway trace** (Part II §6) and no understanding/expression audit (Part VI–VII).
- **No live interaction with Aurora.** Per the standing rule that her work is verified by talking to her, the Praxis fix is verified only at the unit level.
- The 800 Python files were not all read. Claims above are limited to the files cited.

## 7. Implementation status

| Item | Status |
|---|---|
| Praxis init-state ownership (FIX-A117): `aurora_praxis_bridge.py`, `aurora_bridge.py` | **Implemented and verified** — 16 tests in `tests/test_app_bridge_praxis.py` (6 new), 239 passing across the six Praxis suites, layer-acyclicity guard passing |
| Hub shows the Praxis init phase (`hub_screen.dart`) | **Implemented, not validated** — no Flutter toolchain in the audit environment; first APK build is the check |
| Strata ownership map (§2) | **Documented** from code |
| Strata link (network carrier, seq/ack, durable outbox, epoch) | **Not yet implemented** |
| Desktop subsurface service on Windows | **Not yet implemented** (Linux units exist) |
| Surface migration | **Not yet implemented** |
| Clone order experiments; clones on desktop | **Not yet implemented** |
| Consequence-driven recursion; efficiency audit; baselines | **Not yet implemented / not yet measured** |
| Messenger withheld-message trace | **Not yet investigated** |
