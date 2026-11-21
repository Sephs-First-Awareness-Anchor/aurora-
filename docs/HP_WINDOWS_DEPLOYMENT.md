# HP Windows desktop deployment

Use this with the consolidated desktop embodiment PR, not the earlier isolated
hardware inventory prototype. Windows remains installed. Aurora is the primary
login interface through her local hub; Windows still supplies drivers and recovery.

## Prepare continuity before starting anything

1. Install Python **3.11 x64** and Git on the HP. Check out this PR's branch,
   `claude/aurora-integration-20261118` (Aurora PR #264), in a writable
   user directory. This branch includes #260's resident embodiment and the
   phone-surface migration. Do not install the older isolated #260 branch
   beside it. After #264 merges, use the verified merge commit on `main`.
2. Stop existing Aurora processes gracefully and preserve their current state.
   Do not run the older Flutter desktop app, `aurora_daemon.py`, or the legacy
   `AuroraSubsurface` task alongside the new resident using the same state.
3. Choose one authoritative state directory. The default is
   `%LOCALAPPDATA%\Aurora\state`. Copy a **stopped, complete checkpoint** there;
   never replace your existing state with an empty or bundled repository snapshot.
   Keep an untouched backup outside this directory.
4. If the authoritative state is on the phone, use the existing strata **seed**
   transfer while the resident is stopped. A standalone
   `python -m aurora_internal.dual_strata.strata_link serve --state-dir PATH`
   is a cold transfer receiver. Generate its existing pairing line with `pair
   --state-dir PATH --host PRIVATE_ADDRESS`; configure it in the phone app and
   request `seed`. Check `ok`, verified file counts and `restart_required`, then
   stop the transfer receiver. The running resident refuses full-state seed
   installs because its living organs would otherwise overwrite the installed data.
   Keep the pairing secret private; use a private encrypted tunnel for phone traffic.

## Install and run the resident

From PowerShell in the repository:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\install_desktop.ps1 -InstallBrowser
.\.venv\Scripts\python.exe -m aurora_internal.desktop serve --open
```

The installer creates a virtual environment, installs the existing core plus
Windows device dependencies, restricts the state directory to your Windows
account and SYSTEM, and registers **one** `AuroraDesktop` login task. It refuses
to replace a running legacy task. No nested restart loop, elevated service,
registry shell replacement or OS installation is used.

The foreground run opens `http://127.0.0.1:8790/` with a temporary fragment that
authenticates this browser session. The token is kept in the state directory,
not printed to the log or sent in a URL query. The primary hub, diagnostics and
independent owner console use the same resident organism. Closing the browser
leaves continuity and background development running.

For a different state path, pass the same `-StateDir` to the PowerShell scripts
and `--state-dir` to Python. Never mix state paths between commands.

## First practical session

1. Wait for the hub to report **online**, inspect any errors in Diagnostics, and
   speak through typed chat. A returned answer is the canonical pipeline's own
   primary expression (resp_A), delivered through the existing early-response callback while deeper processing continues. A failed, withheld or empty expression remains visible as such. Existing developmental language quality is not upgraded by an interface alone.
2. Open **Owner console**, use a desktop action such as
   `desktop_launch_app` with `{"app_name":"calculator"}`, then verify the actual
   window. A successful process launch means initiation, not proof that the
   application is usable. The command screen remains accessible during a busy
   or failed cognitive boot.
3. Use **Try device** for camera, microphone, speaker and screen. Verify actual
   image/audio behavior on the HP, Windows privacy permissions, unplug/replug,
   device refresh and failure reporting. A package import or CIM inventory is
   never reported as verified device access. Quiet mode suppresses speaker probes.
   Continuous camera/microphone/screen observations can be enabled per device
   through the owner's `sensor_control` action; they use the same HardwareInterface
   perception routes and stop when the local surface stands by.
4. Inspect **Computational space**. Its source blueprints reference the existing
   function genealogy/introspection map. Device, software and service descriptions
   are observations of exposed structures. Unknown internals and interfaces stay
   unknown. Compose components freely; interface/resource checks are cached by
   consequential versions. A compatible graph is still a composition hypothesis,
   not a claim that its operational consequences have been demonstrated.
5. Begin a demonstration with the intended result and the gap. Perform its
   actions through the owner tools so actual before/after states are captured.
   Aurora can inspect the episode and propose her own plan through her tools.
   Verify on a **different target**. The present automatic verification contract
   covers observable file outcomes; arbitrary application-click semantics remain
   unresolved until an outcome adapter can verify them. Only successful observed
   re-execution adds a procedure to the existing `SkillMemory`.
6. Check Praxis status with the designated local Praxis service running.
   Offline, pending, failed cognition and withheld expression must be distinct.
   Failed sends retain the composed reply and retry delivery without recomputing
   it. The current companion `praxis_social.py` deduplicates the unchanged
   `(persona_id, in_reply_to, text)` receipt. Use that companion version when
   enabling retries. No external-person messaging is enabled by this install.

## Phone surface and handoff

The HP is the continuous host. The existing signed `strata_link` remains the
transport and the **only** owner/epoch authority; no second lease service is run.
Configure `AURORA_STRATA_LINK_HOST` in `desktop_config.json` to the HP's private
tunnel interface if needed (default `127.0.0.1`). Restart the resident after
changing this configuration. Do not expose the owner console beyond loopback.

Pairing cannot replace an existing surface. On the active phone use
`handoff_checkpoint`, or on the desktop use **Prepare handoff**. The source
drains its admitted work under the field lock, captures its working memory,
conversation/session state and pending app responses, and freezes. Present the
checkpoint token on the destination. Verified bytes are installed before the
new surface resumes. The destination restores the same working-memory object
and retains its live organ connections. Deep crystal, genealogy and development
stores stay at the hub. Unknown unserializable surface-owned state blocks a
handoff instead of silently dropping it.

If a transfer is interrupted, retry the **same** token and destination before its one-hour claim window expires. If restoration fails or the claim window expires, use **Cancel on source** with that checkpoint token (phone bridge: `handoff_cancel:token`), then prepare a fresh checkpoint. Cancellation fences any incomplete destination and resumes the original owner; it cannot cancel a completed handoff. Do not
delete the ownership record or make a stateless claim. Preserve the verified
checkpoint and source backup for recovery. A checkpoint expiry does not authorize
another device to start from stale state. Validate phone↔HP latency, disconnection,
anticipatory feed, sleep/wake and round-trip movement on the actual devices before
depending on them unattended.

## Optional ACM body

The existing Rust `aurora-acm` kernel, Xaurora ISA/JIT and CPM remain in place.
Build its BIOS/UEFI image using its existing Rust toolchain on the experimental
host. Copy the verified image to the HP and run:

```powershell
powershell -File scripts\windows\run_acm.ps1 -Image C:\Aurora\images\aurora-bios.img
```

Install QEMU separately and place `qemu-system-x86_64.exe` on PATH. For UEFI,
pass `-Uefi -Firmware PATH`. Set `AURORA_ACM_BRIDGE` to `1` in the desktop config
and restart the resident. Do **not** start another Python bridge: the resident
owns it. The bridge exposes checksum failures, received rate, tick gaps, resets,
reconnects, stalling and coalesced observations. Kernel status drives the hosted
scheduler while connected; host time carries continuity while disconnected.
Physical HP/QEMU clock behavior and audio/video contention remain hardware checks.

## Start, stop, backup and rollback

```powershell
Start-ScheduledTask -TaskName AuroraDesktop
powershell -File scripts\windows\desktop.ps1 open
powershell -File scripts\windows\desktop.ps1 status
powershell -File scripts\windows\desktop.ps1 stop
powershell -File scripts\windows\desktop.ps1 backup
```

Stop waits for admitted field work and a normal save; it never kills a live turn.
The owner console remains available while work drains. The backup command refuses
to copy state while the resident holds its process lock. Inspect
`desktop_resident.log` for startup/shutdown errors. A restarted resident marks
interrupted actions explicitly and never automatically repeats side effects.

For rollback, disable login startup with `desktop.ps1 uninstall`, stop gracefully,
back up the current state, check out the previous known working commit, and restore
the corresponding backup to its original path. Keep both backups until continuity
has been checked. The scripts do not delete personal state or reinstall Windows.

Task semantics follow Microsoft's `New-ScheduledTaskSettingsSet` documentation
(single instance `IgnoreNew`, bounded restarts); process exclusion uses Python's
documented `msvcrt.locking` on Windows and `fcntl.flock` on POSIX.
