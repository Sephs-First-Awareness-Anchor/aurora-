# Desktop subsurface hub and surface-only phone — design (draft for Sir's decision)

Authors: Sunni (Sir) Morningstar & Cael Devo

## What exists, measured (2026-11-15)
- Phone bundles every root `*.py` (155 files, ~9.6 MB) plus all of `aurora_internal/` (200 files, ~7.8 MB) plus `aurora_manifold_directory/` (43 MB), and `aurora_bridge.py` imports root `aurora.py`: the phone runs her whole cognition. (`flutter_app/android/app/build.gradle`, `preparePythonSources`.)
- `strata_link` already carries phone → laptop continuity and sensory snapshots (port 8791, signed, seed/handoff); downlink projection is off until seeded.
- `aurora_hub.py` (tkinter, ~7,900 lines) reads `aurora_state/` JSON only; it has no concept view.
- Built this session: `crystal_web.py` (read-only search / lookup / neighbourhood over `dps_crystals.json`), `crystal_web_server.py` (stdlib, GET-only, loopback unless `--token`), `crystal_web_page.py` (one self-contained page: search, force-laid web, crystal card). 9 tests; trialled on real state after a pass (4,585 crystals, 437 with ties).

## Desktop subsurface hub
A local web hub (the concept web is its first panel), served by the subsurface process, same read-only discipline: concept web · evidence/maturity per crystal · resolution ledger · strata link status (what the phone last sent, what is queued) · pass report (`crystal_runtime`). The tkinter hub stays as it is. Reason for web: testable headless, searchable, and reachable from the phone over the private tunnel when Sir wants it, without the phone carrying any of it.

## Phone: surface only
Surface = present frame, live sensory capture, embodiment, speech in/out, the last projection from the subsurface. Mechanism, in stages, each measured before the next:
1. Surface allow-list in `build.gradle` (replace the copy-everything glob with an explicit list driven by `AURORA_STRATA_DOMAIN_MAP.md`); measure APK size, boot time, memory.
2. `aurora_bridge.initialize` boots only the surface systems; subsurface calls go through `strata_link` (uplink continuity + sensory; downlink projection).
3. Offline behaviour: the phone keeps being embodied and sensing, speaks from the last projection, and queues continuity for the next link. (Decision pending: whether a thin local fallback is wanted.)
4. The manifold directory (43 MB) leaves the phone unless the surface needs a named part of it.

## Not done / risks
- Nothing on the phone has been changed; no build was run (no Android toolchain here).
- Stage 2 changes what she is on the phone: she stops thinking there. That needs Sir's go and a rollback path (keep the current build channel until the link has been lived with).

## Findings since the draft (measured, 2026-11-15 afternoon)
- Hub panels are built (resolution ledger, strata link, crystal pass) beside the concept web; the strata panel shows named non-secret fields only and creates nothing on disk. The pass now leaves `crystal_pass_report.json` (latest + 24 passes of history) for the hub to read.
- `tools/import_closure.py` (static, reads source): `aurora.py` alone reaches 242 modules / 14.1 MB (56 modules / 7.2 MB at import time); the link and surface channel modules (`strata_link`, continuity feed, sensory snapshot/control, presence metrics, surface channel) reach 10 modules / 0.17 MB at import (31 / 1.85 MB with lazy imports). So the heavy part is not the link; it is `boot_aurora`.
- **The surface is not "no cognition" in the existing design.** `strata_link.py` states that turn events and the presence frame stay on the Surface device on purpose (latency-critical, "the Surface already runs it locally"), and `AURORA_STRATA_DOMAIN_MAP.md` gives the Surface the conscious frame, DCE bridge, expression and meaning/accuracy tracking (domain 3). `aurora_surface_daemon.py` boots the whole of `aurora.boot_aurora`, so surface and subsurface are roles of one codebase, not two programs. A surface-only phone therefore needs a **surface profile of the boot** (domain 3 + sensory + embodiment + the link) that leaves out genetic/lineage, environmental filter, experiential depth, evolution, adaptive and learning-pipeline systems (domains 1, 2, 4-7), not a thin client that has no cognition. Offline she can still take a turn from the present frame and the last projection; what she cannot do is consolidate, evolve or learn until the link returns.
- Stage 1 as first written (trim the gradle glob) cannot be done safely first: the phone's boot imports what the glob would remove. The order that works is: (1) surface boot profile in `boot_aurora` (systems list by domain, default unchanged), verified headlessly by a test that boots the profile and takes a turn; (2) the import closure of that profile becomes the gradle allow-list; (3) measure APK size, boot time and memory on the device.

