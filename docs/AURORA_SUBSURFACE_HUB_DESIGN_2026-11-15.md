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
