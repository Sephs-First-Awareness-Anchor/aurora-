# Desktop embodiment audit and coordinated design

Baseline: `main` f5c7beb5020194c2d0cc032e7d4f6eb223c7c902, 17 November 2026.
Target: HP Windows, retaining Windows and its recovery desktop. This audit covers
the runtime seams below, not a proof of every algorithm or of consciousness.

## Findings before implementation

| Area / traced source | Existing mechanism | Integration conflict / correction |
| --- | --- | --- |
| ACM, `aurora-acm/kernel/src/{cpm,xaurora,bridge,hw}`, `aurora_computational_model.py` | Rust kernel, ISA/JIT, scheduler, UART status; Python CPM with crystal head and genealogy programs | Preserve both. Windows hosts the Python organism and device APIs; optional QEMU runs ACM. No native HP drivers or OS replacement claimed. |
| `aurora_acm_bridge.py` | Framed axes/status TCP bridge | Multiple status frames collapse to the last frame; old last_status can be ticked again; harmonic threads compete with daemon schedules; no stop/reconnect/backpressure accounting. Add hosted transport with one clock authority and bounded delivery into the resident runtime. |
| `aurora.py`, app bridge, daemons | Canonical boot and turn pipeline, full/surface/subsurface profiles | Running the Windows app plus background daemon would boot two full organisms writing the same stores. Desktop host must boot once; foreground turns and background work share the same organs and field lock. UI lifetime must not own continuity. |
| `strata_link.py`, `strata_state_transfer.py` | HMAC, durable queues, seq/ack, verified seed/handoff | A stateless claim can replace an existing owner; ownership alone does not stop cognition; full-state seed can overwrite live stores. Require checkpoint handoff, epoch fencing at turn admission, paused source, restore-before-ready, source cancellation/recovery, and explicit cold-seed procedure. Keep legacy full-state transfer available only as a cold migration. |
| `predictive_stager.py` | Bounded hypothesis queue and pressure perspectives | Fixed path; no expiry, destructive network relay, mismatched context and rewrapping risk. Use explicit state-dir adapters, age/epoch checks, copy-before-ack relay and original timestamps. |
| `surface_continuity_feed.py`, presence, sensory channels | Experience handoff and transient sensory observations | Transporting a completed turn is too late for anticipation. Add pre-processing raw input as a disposable channel, consumed before the completed continuity event; never record a prediction as lived experience. |
| `aurora_hardware_io.py`, `aurora_desktop_agent.py` | Real audio, camera, TTS, browser, app and file helpers | Windows is misclassified as Linux/headless; Linux app launch invokes `os.getuid`; fixed output paths; imports mistaken for access. Extend existing adapters, report discovered/exposed/authorized/verified separately, refresh hotplug inventory and feed observations into existing sensory/gateway paths. |
| `tool_registry.py`, `aurora_autonomy.py`, runtime governor | Tool dispatch, autonomy boundaries/quotas, constraint economics | No enforced desktop communication boundary around browser actions, shell and macros. Keep research available; autonomous interaction cannot send to people or escape through shell/macros. Owner commands are independently authenticated, explicit acts; designated Praxis messaging retains its own fences. |
| `aurora_praxis_bridge.py`, messenger | Consequence witness, pressure/sediment routing, partner attribution, voice gate and delivery queues | Desktop must start these against the resident organs and lock; show actual offline, withheld and pending states. Do not introduce an alternative learning or partner service. |
| clone harvest / historical experience | Idempotent organ harvest, rehearsal, reasoning paths, demonstration grammar | Desktop bootstrap omitted absorption/status. Synchronous harvest also blocked startup and repeatedly serialized large evidence stores. Reuse harvest and historical environment, yielding to live turns. No clone executable, weights or speculative promotions may be injected through the hub. |
| `crystal_runtime.word_profiles` | Durable WordUse plus old conversation profiles | Same utterance counted twice. Integrate #255's fallback-only reconstruction, preserving legacy checkpoints. |
| dream substrate / canonical genealogy | Dream encounter, perturbation and association | Prefixes used as ancestors; random association calls promotion. Use canonical parent IDs and transient association hypotheses. Dreams remain downstream of lived evidence. |
| introspection / QuasiArch / function lineage | Existing source anatomy and diagnostic episodes | No computational composition workspace. Reference this map rather than rebuild semantic knowledge; preserve source versions, typed contracts and unresolved semantics. Composition must cache pure structural checks, invalidate consequential dependencies and never cache actions. |
| teaching / `SkillMemory` / reasoning paths | Existing procedural memory and reply demonstrations | No desktop intent → actions → before/after → dependency → repeat-back verification. Add an observation journal and independent replay through the same adapters. Owner demonstration is observed instruction, never Aurora's own execution. Only verified re-execution can support a procedural skill. |
| Tk hub / Flutter / #254 concept web | Diagnostics, phone interface, read-only concept web | No Aurora-first resident Windows hub or independent owner control. Consolidate concept/ledger panels into a local presence-first hub, with separate diagnostics and owner console routes that remain responsive while cognition is busy. Preserve existing clients. |
| Windows task / batch | Login task and endless restart loop | Repo-local state, nested restarts, no singleton, no graceful stop or rollback. One scheduled resident host, writable external state, bounded restart, login hub launch, recovery/backup/stop procedures. |

## One organism and explicit authorities

The resident desktop host owns one `boot_aurora` result. The canonical turn
pipeline is the conscious surface. Its background worker calls the existing
daemon's developmental functions, existing curiosity, Praxis, clone absorption
and historical experience using the same organs and lock. HTTP handlers never
boot a second stack. Diagnostics read snapshots; the owner console remains
available independently of a successful boot. The hub displays canonical resp_A through the existing on_surface_ready callback; optional resp_B never replaces that primary expression. Clone harvest joins the same field in idle batches. Owner/final checkpoints persist state without starting a new whole-store developmental weave; normal idle saves retain that pass. A process lock protects the state
directory. Raw input and device observations carry provenance into the existing
channels; blueprints and demonstrations are environmental records, not second
crystal/skill/promotion stores.

Windows remains responsible for device drivers, desktop applications and recovery.
ACM is an optional connected native execution substrate, not emulated Windows
device support. Hosted bridge status explicitly distinguishes disconnected,
connected, malformed, stalled and coalesced frames. Exactly one scheduler owns
developmental cycles, whether their due times come from kernel ticks or host time.

## Open work reconciliation

Expand #260 into the single desktop integration PR. Reuse #254's read-only
concept graph/panels without its alternate crystal runtime. Reuse #255's precise
WordUse fix. #240's standalone lease prototype is superseded by the transport's
existing ownership/state-transfer protocol; do not run two lease authorities.
#239/#237 remain separate older application changes; current main has their messenger/transport architecture, but inspection still
found a single-slot late-reply buffer and dropped failure paths. This PR fixes
those in place, without replacing current files with older branch versions. #258 supplies dream evidence regression requirements.
No unrelated branch is merged or closed automatically.

## Acceptance and limits

Tests must exercise the real hosted boot/turn seam, foreground/background lock,
restart and HTTP console, actual loopback strata transport, stale/duplicate
frames, disconnected service outcomes, blueprint invalidation, demonstration
failure/success and existing developmental/Praxis regressions. Separate measured
results from source inspection in the final validation record. Hardware access,
Windows task behavior, hotplug, HP audio/camera/display, phone tunnel and QEMU
timing require an HP session. No unattended deployment or native OS installation
is performed by this PR.
