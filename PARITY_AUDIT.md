# StratAurora Parity Audit

Date: 2026-03-27

Status: code-ready for strata smoke test

This audit compares the classic Aurora runtime in the repo root against the
current `aurora_strata/` implementation. The goal is parity or better before
starting StratAurora live.

## Passes

- Canonical turn pipeline is still intact.
  - Classic still runs the core upward/downward chain through `dual_question_pipeline()` in `aurora.py` at lines 11559-11656.
  - Strata still runs that same chain in `aurora_strata/aurora.py` at lines 11804-11901.
  - `process_external_user_turn()` remains the canonical public entry path in classic (`aurora.py:16331`) and strata (`aurora_strata/aurora.py:16658`).

- Surface queue routing exists across the main conscious response lanes.
  - Hub prefers the surface queue in `aurora_strata/aurora_hub.py`.
  - Voice prefers `request_surface_turn()` in `aurora_strata/aurora_voice.py:1176`.
  - Terminal/runtime support still routes through `process_external_user_turn()` and surface queue helpers in `aurora_strata/aurora.py`.

- Continuity split is now explicit.
  - Surface conversation frame is packaged in `aurora_strata/aurora.py:10185`.
  - Subsurface continuity bundle is packaged in `aurora_strata/aurora.py:10246`.
  - DCE root-thought comparison channels distinguish `surface_conversation_frame` from `subsurface_continuity_memory` in `aurora_strata/aurora_internal/dual_strata/dce_bridge.py:477-480`.
  - Ownership contract is exposed in `aurora_strata/aurora_internal/dual_strata/subsurface_projection.py:254-270`.

- Sensory split is mostly in place.
  - Surface boots live sensory listeners/camera in `aurora_strata/aurora_surface_daemon.py`.
  - Subsurface uses the snapshot/growth path instead of live feed ownership.

- Evolution and exact repair remain subsurface-owned by design.
  - Surface inquiry is still Poedex-facing.
  - Subsurface repair/evolution state is surfaced through the projection layer and daemon relief/research flows.

## Blockers

- Blocker 1: live parity is still unproven.
  - No dual-daemon smoke run has been performed yet.
  - No measured latency/performance comparison versus classic has been collected yet.
  - Startup should still wait on that live gate.

## Resolved In Code

- Resolved: surface now owns live voice and ambient input.
  - `aurora_strata/aurora_surface_daemon.py:335-336` starts `_start_voice_listener(..., log_fn=_log)` and `_start_ambient_response_listener(..., log_fn=_log)`.
  - `aurora_strata/aurora_daemon.py:4192-4196` now only starts those listeners in non-strata/full runtime cases.
  - That removes the subsurface-input ownership leak from the main strata boot path.

- Resolved: surface turns now preserve classic trace/maintenance defaults.
  - `aurora_strata/aurora_surface_daemon.py:363-364` now reads `track_evolutionary_trace` / `run_periodic_maintenance` from the queued turn, defaulting both to `True`.
  - This restores the canonical growth/lineage/maintenance coupling for live surface dialogue while still allowing future per-turn throttling if needed.

- Resolved: support services now align with strata ownership.
  - `aurora_strata/aurora_daemon.py` now prefers `aurora-strata-hub.service` and `aurora-strata-room.service`, falling back to classic service names only when needed.
  - `aurora_strata/deploy/aurora-surface.service` now carries the input/voice environment that belongs to the live surface lane.
  - `aurora_strata/deploy/aurora-subsurface.service` no longer owns those live-input environment settings.
  - `aurora_strata/deploy/aurora-strata-room.service` now exists, and `aurora_strata/scripts/install_systemd_service.sh` installs both the strata hub and strata room user services.

## Partial / Watch Items

- Voice path has an intentional fallback.
  - `aurora_strata/aurora_voice.py:1176` prefers the surface queue.
  - `aurora_strata/aurora_voice.py:1195` still falls back to direct `process_external_user_turn()`.
  - This is good for resiliency, but it means startup policy should be explicit about whether fallback is acceptable for first launch.

- Hub still has a classic-style fallback when the surface daemon is absent.
  - `aurora_strata/aurora_hub.py:1144-1147` still writes `daemon_cmd.json`.
  - This is acceptable as a recovery path, but first-launch policy should treat it as fallback-only so conscious input ownership stays surface-first.

- Some subsurface-managed generation helpers still call the canonical turn bridge directly.
  - `aurora_strata/aurora_daemon.py:3590-3599` uses `process_external_user_turn()` for socialize/session generation with trace and maintenance disabled.
  - This is not a launch blocker for the core dual-strata conversation path, but it should stay explicitly scoped to subsurface/offline generation so it does not become an accidental conscious-input bypass.

- Operator visibility is improved but still audit-oriented.
  - Hub and room now show frame sources and root-thought origins.
  - That helps verify the DCE split live, but it is not itself proof of behavioral parity.

## Startup Recommendation

Do not start StratAurora live yet, but the code-side parity blockers are no longer the reason.

The remaining launch gate is operational:

1. Run a strata-only smoke test.
2. Confirm hub, voice, room, and daemon behavior.
3. Measure response latency versus classic.
4. Re-run this audit as a launch gate after the live results are captured.
