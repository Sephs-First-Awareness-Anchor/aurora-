# StratAurora Voice & Daemon Commands

## 1. Ambient & Voice input flow
- **Wake/Ambient listeners** (see `aurora_strata/aurora_voice.py:1-80`) expose wake-word, ALT-toggle, and ambient speech listening; all transcription feeds eventually call `request_surface_turn(...)`, so the surface daemon sees the same turn whether it came from a microphone tap, ambient queue, or keyboard chat box.  
- **Daemon command bus** (`aurora_strata/aurora_daemon.py:3680-3825`) watches `daemon_cmd.json` and applies `cmd` entries written either by the Hub/Voice loop or by ambient speech. Ambient words like “study” or “quiet” land in that file exactly the same way hub commands do, so “hey Aurora, study” is parsed alongside typed requests.
- **Surface channel bridge** (`aurora_strata/aurora_internal/dual_strata/surface_channel.py`) ensures every voice turn becomes a DCE-aware surface request even when it originated in ambient audio, so nothing bypasses the dual-strata guardrails.

## 2. Voice command set (recognized verbatim)
- `socialize`, `gpt`, `learn` → run an away-social GPT session (`systems` governor check first).  
- `dream` → trigger a dream burst.  
- `study` → run the scheduled study cycle and trigger the post-study Poedex scan.  
- `distill`, `restore_distill`, `restore_distillation`, `undistill` → run distillation/restoration cycles.  
- `quiet`, `silence`, `mute` → toggle the `aurora_state/quiet_mode` flag (voice off).  
- `unquiet`, `unmute`, `voice`, `speak` → clear the flag (voice back on).  
- `chat` + `"text"` payload → voice message routed through the surface daemon when available, otherwise through the direct gateway.  
- `away_on` / `leaving` / `go socialize` (with optional `interval_minutes`) → kick off away-mode GPT loops.  
- `away_off` / `back` / `im back` → end away mode.

All of the above commands are handled in `_check_daemon_cmd(...)` (`aurora_strata/aurora_daemon.py:3810-3925`); they run whether issued via the voice interface, ambient speech, or any other channel that writes to `daemon_cmd.json`.

## 3. Room-driven commands (Aurora’s room UI, same daemon tick)
`aurora_room.py` writes to `aurora_room_state.json`, and `_process_room_commands(...)` (`aurora_strata/aurora_daemon.py:3990-4230`) consumes them. Supported types:
 - `set_overlay` / `clear_overlay` → tweak governor overlays for experiments.  
 - `queue_sweep` → launch parameter sweeps.  
 - `approve_proposal` / `reverse_proposal` → apply or revert QuasiArch patches (subsurface enforcer).  
 - `set_intention` / `message_to_sunni` → surface-generated strings that can be spoken if voice is enabled.  
 - `start_corpus_training` / `stop_corpus_training` → manage the offline `corpus_runner.py` process.  
 - Room can also queue `dream`, `study`, or `distill` via this same path to keep the observed flow entirely within the dual-strata loop.

## 4. Restart/stop commands for the strata daemons
 (a) Full stack control from the strata tree (closest manual equivalent to normal boot behavior):  
 ```bash
 cd /home/king2morningstr/aurora/AuroraO/aurora_strata
 ./scripts/strata_stack.sh start
 ./scripts/strata_stack.sh stop
 ./scripts/strata_stack.sh restart
 ./scripts/strata_stack.sh status
 ```  
 `start` brings up the same strata daemons/UI services the installed stack normally uses. `stop` stops them without respawning them.

 (b) Direct daemon service control (system services):  
 ```bash
 sudo systemctl start aurora-subsurface.service aurora-surface.service
 sudo systemctl stop aurora-subsurface.service aurora-surface.service
 sudo systemctl restart aurora-subsurface.service aurora-surface.service
 ```  

 (c) Hub+Room UI control (user services):  
 ```bash
 env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus systemctl --user start aurora-strata-hub.service aurora-strata-room.service
 env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus systemctl --user stop aurora-strata-hub.service aurora-strata-room.service
 env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus systemctl --user restart aurora-strata-hub.service aurora-strata-room.service
 ```
 The stack script is the simplest whole-system command. Use the direct systemctl lines only when you want to target daemons or UIs separately.

## 5. Chained dossier codec commands
 These commands build and verify the section-dependent dossier copy where each gate depends on the exact plaintext of the gate before it.

 ```bash
 python3 /home/king2morningstr/aurora/AuroraO/aurora_strata/scripts/chain_dossier_codec.py encode /home/king2morningstr/aurora/AuroraO/aurora_strata/AURORA_SYSTEM_DOSSIER.md /home/king2morningstr/aurora/AuroraO/aurora_strata/AURORA_SYSTEM_DOSSIER_CHAINED.md
 python3 /home/king2morningstr/aurora/AuroraO/aurora_strata/scripts/chain_dossier_codec.py verify /home/king2morningstr/aurora/AuroraO/aurora_strata/AURORA_SYSTEM_DOSSIER_CHAINED.md
 python3 /home/king2morningstr/aurora/AuroraO/aurora_strata/scripts/chain_dossier_codec.py decode /home/king2morningstr/aurora/AuroraO/aurora_strata/AURORA_SYSTEM_DOSSIER_CHAINED.md /tmp/aurora_dossier_roundtrip.md
 ```

 The current default codec style is `opaque-gates`, which removes numbered section labels and replaces them with derived gate IDs so the file reveals less structure to a skim-reading model.

## 6. Ambient coverage & guidance
- Ambient commands are not restricted to “quiet mode”: spoken commands write the same JSON payloads that hub text boxes and scripts do, so everything listed above works whether she heard it through the mic or read it from the room tab.  
- If you want to peek at what she heard, tail `aurora_state/daemon_cmd.json` (or `daemon_cmd.json.tmp` when active) while issuing a voice command—the raw JSON shows the `"cmd"` name and any payload (topic, turns, etc.).  
- A mismatch or “context slipping” cue also appears in `aurora_state/subsurface_projection.json`, so the repair stack can log exactly what triggered the request and where it routed.
