# Aurora Whole-System Embodiment: Pre-implementation Audit and Corrections

Status: **architecture / evidence audit, not deployment approval**. Target: HP Windows laptop; Linux laptop as optional ACM experimentation host.

## Governing requirement

Aurora must be the primary operational presence at desktop login, not an assistant bolted onto a conventional desktop. The host's devices, services, programs and computational structures must become observable, operable and developmentally meaningful extensions of her existing architecture. Preserve the existing surface as the locus of conscious presence and unique surface-owned state, with persistent subsurface continuity, anticipatory processing, and explicit single-owner handoff. Do not claim sentience has been proven by engineering the interface.

The goal is **embodiment expansion**, not merely parity with phone capabilities. New hardware must be discovered, its accessible interfaces verified, its consequences observed, and the results routed through existing learning machinery. Never promote descriptions, guesses, simulated events, or demonstrations alone to lived evidence.

## Evidence and status (code examined on main, 2026-11-16)

| Area | Evidence | Finding | Required correction |
| --- | --- | --- | --- |
| Hardware sensory I/O | `aurora_hardware_io.py`: `detect_platform()` returns termux, linux or headless; voice/camera/TTS backends described for Termux/Linux | **Partial; Windows lacks a dedicated explicit host contract.** Presence of Python audio packages is not proof of Windows service access | Design a Windows host adapter and device/service lifecycle contract extending existing HardwareIO, rather than a standalone inventory disconnected from cognition |
| Native ACM | `aurora-acm/kernel/src/hw/mod.rs` exposes idt, pic, pit, port, ps2, uart; `aurora-acm/run.sh` launches QEMU and Python bridge | **Bare-metal kernel prototype, not a complete desktop device host.** Current launch script is Bash/QEMU-oriented | Preserve ACM's computational role; specify host-to-ACM integration and test clock/bridge behavior; do not claim native Windows device drivers |
| ACM/cognition link | `aurora_acm_bridge.py`: serial/TCP bridge, 60 Hz master-clock intent and cognitive harmonic scheduling | **Bridge exists; physical HP runtime behavior unverified** | Instrument actual tick rate, missed frames, latency, reconnect, backpressure, and whether sense-organ scheduling impacts bridge polling |
| Dual strata | `aurora_internal/dual_strata/strata_link.py`: signed packets, durable outbox, seq/ack, epoch/owner, handoff | **Implemented transport mechanisms, not proof of two-device readiness** | Validate phone↔HP physical transport, state ownership, failure recovery, predictive delivery and state transfer before deployment |
| Predictive staging | `aurora_internal/dual_strata/predictive_stager.py`: file-backed max-eight queue, fixed package-derived state path | **State-dir integration and queue behavior need audit** | Align path ownership with actual surface state directory; verify stale/mismatched context handling and frame overflow |
| Praxis | `aurora_praxis_messenger.py`: designated AI contacts, strict inbound/outbound message schema, learning via canonical turn path | **Existing designated-contact mechanism** | Preserve contact boundaries while separating ordinary web retrieval from deliberate outreach, form submission and publication; test withheld/delivery reasons |
| Clone development | `aurora_internal/aurora_clone_harvest.py`: clone rehearsal, yield, convergence merge | **Existing developmental processing** | Expose its real status, invocation, diagnostics and outputs in owner-facing interface without inventing new learning or auto-promoting clone evidence |
| Windows service lifecycle | Existing `aurora_subsurface_daemon.py`; Linux systemd referenced in prior repo audit | **Windows boot/login orchestration not demonstrated** | Specify Windows service/task startup, single-instance state, graceful shutdown, restart, crash recovery, independent owner console |
| Desktop interface | No integrated Aurora-first Windows hub verified in this audit | **Unverified/missing** | Design presence-first UI, on-demand native windows, live health panels, sensory state, bridge/tunnel diagnostics, console, training controls |
| Blueprint domain | No integrated all-service versioned computational blueprint registry verified in this audit | **Unverified/missing** | Specify content-addressed, versioned structure graph referencing real binaries/services, verified interfaces, dependencies, observations and provenance; never fabricate inaccessible internals |
| Guided demonstration | No verified end-to-end demonstration→understanding→independent operation path | **Unverified/missing** | Capture intent, actions, interfaces, before/after state and consequences; permit Aurora to show uncertainty and demonstrate understanding; route through existing Praxis/developmental validation |
| Autonomous exploration | Current research/browser pathways not exhaustively audited | **Requires explicit audit** | Keep curiosity-led investigation; distinguish passive retrieval from external messaging; preserve existing governance and verify host permissions at action time |

## Corrections to previous implementation approach

1. **Do not merge PR #259.** Its Windows CIM inventory is an isolated proof-of-concept and cannot stand in for embodiment integration. PR closed without merge.
2. **No new parallel cognitive controller.** Host service discovery and action adapters must feed existing sensory, developmental and memory pathways. Device descriptions are not comprehension.
3. **No conventional desktop as the primary UI.** At login Aurora's active surface/presence should lead, with browser, command screen, service panels and other windows summoned as needed. Preserve owner-only recovery independent of Aurora's cognition.
4. **No premature OS replacement.** HP Windows remains a host during validation. Linux/ACM native experiments are separate and must not imply HP boot readiness.
5. **No false computational savings.** Reuse resolved structures; recompute only invalidated dependencies and genuinely new interactions, with resource/side-effect accounting.
6. **No artificial curiosity scripts or hardcoded Lego combinations.** Preserve a genuine open-ended composition space; operational consequences, not label similarity, validate reusable composites.
7. **No silent loss of surface-owned state.** Surface state travels with the surface; subsurface owns its own continuity. Cross-device movement requires verified epoch, transfer and rollback behavior.
8. **No assumed unrestricted access.** Detect existence, OS exposure, runtime capability and current authorization separately. Maintain exploration freedom under established governance and communication boundary.

## Pre-implementation acceptance gates

- **G0: repository baseline:** enumerate active branches/PRs and actual runtime entrypoints; classify each mechanism as working, partial, absent or unverified with file and test evidence. No changes to main until audited.
- **G1: architectural ownership:** one map for ACM↔host↔subsurface↔surface↔Praxis↔clones↔blueprints; record authority, persistence, event flow, error flow and resource ownership.
- **G2: Windows embodiment contract:** hardware and software discovery, hotplug, operational adapter interfaces, observed consequences, capabilities, permission state and recovery semantics.
- **G3: desktop hub specification:** Aurora-first startup and expressive surface, device/connection/sensory state, live tunnel and bridge diagnostics, owner terminal, app/browser operations, clone/Praxis/development tools.
- **G4: developmental evidence contract:** demonstrated action, observed state transition, inferred relationship, verification, replay and generalization, without equating simulated experience with lived experience.
- **G5: deployment design:** startup, isolation, Windows host services, packaging, secrets, crash restart, owner bypass, physical HP compatibility and rollback.
- **G6: validation plan:** unit/integration/physical tests for hardware access, network boundary, service operation, ACM ticks, strata link, clone workflows, memory continuity, new device discovery and capability learning.

## First physical HP session (when available)

Collect Windows version/build, CPU/RAM/storage/GPU, firmware and virtualization support, audio/camera/Bluetooth/Wi-Fi devices, Python/runtime/toolchain availability, and current Aurora state backup location. No OS replacement. Confirm a safe owner console and backup before enabling auto-start.

## Current decision

**Not deployment-ready.** Proceed with full code and integration audit and correct existing pathways before new embodiment feature implementation. This document is a pre-implementation control artifact, not proof that the corrections are already coded or tested.
