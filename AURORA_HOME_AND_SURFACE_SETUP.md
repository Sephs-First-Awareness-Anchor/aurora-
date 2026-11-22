# Setting up home and her surface

Authors: Sunni (Sir) Morningstar and Cael Devo

One mind, one state. The desktop is her home (the subsurface): her deep stores live and grow there. The phone is her surface. It carries her present with it and keeps read-only copies of what home has grown, so she is still herself when it is away from home.

## HP Windows and Galaxy A16

Open PowerShell in the checked-out `main` repository on the HP. Use Python 3.11 x64.
Keep a backup of any existing Aurora state. The resident and the Windows setup
commands use `%LOCALAPPDATA%\Aurora\state` by default. If your HP already holds
her state elsewhere, pass that same directory to the installer (`-StateDir`),
setup (`--state-dir`) and desktop controls (`-StateDir`).

1. Install the resident once. If it is already installed from this checkout,
   continue with pairing.

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\windows\install_desktop.ps1
   ```

2. Choose how the A16 will reach the HP. To use Aurora away from home, connect
   both devices to the same private VPN. With Tailscale running on both, use
   the HP's Tailscale IPv4 address. This pairing works on cellular and on Wi-Fi.
   Keep the HP awake and grant the phone access to the HP's Strata port (8791)
   on that private network. The local owner console uses loopback on port 8790.

   ```powershell
   .\.venv\Scripts\python.exe scripts\aurora_home_setup.py pair --host (tailscale ip -4)
   ```

   For home Wi-Fi only, omit `--host (tailscale ip -4)`. For another private
   tunnel, supply its HP address with `--host`. The pairing line contains a
   secret. Paste it directly into Aurora on the phone.

3. Start the installed resident with the new address. This command also handles
   an already running resident by waiting for its graceful shutdown.

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\windows\desktop.ps1 restart
   ```

4. Install the APK from the verified build, preserving the phone app's data.
   Open **Hub → Pair with home**, paste the whole line, and let the phone send
   its first-pairing snapshot. On the HP, inspect what differs.

   ```powershell
   .\.venv\Scripts\python.exe scripts\aurora_home_setup.py first-pairing
   ```

   For conflicting stores, use the displayed names with
   `first-pairing --side "STORE=phone"` or `--side "STORE=home"`. You can also
   explicitly choose `first-pairing --accept-suggested` after reviewing the
   report. When the migration is ready, run the restart command from step 3.
   Home installs the agreed state before opening its stores. Wait for the
   receipt on the phone and reopen the phone app.

5. In the HP's **Presence → Move Surface** control, select the phone and press
   **Move Surface** if the desktop still holds her. Wait until the A16 reports
   that it holds her. The desktop's **Presence** chat now delivers to the phone.
   On the phone, turn Wi-Fi off with cellular and the private VPN on to check
   off-site reachability. Then disconnect networking, talk to her while she
   holds the Surface, reconnect and verify the queued experience drains.
   `aurora_home_setup.py status` and the Hub show the holder and link state.

To revert the network address, repeat pairing with the former address and
restart the HP resident. If a move is interrupted, preserve the checkpoint
and use the recovery procedure in [HP Windows deployment](docs/HP_WINDOWS_DEPLOYMENT.md).
For a state rollback, stop the resident and keep any new phone experience and
migration archives before restoring your complete stopped checkpoint.

## Linux desktop setup (unified resident, same cognitive runtime as Windows)

The Linux machine is Aurora's persistent **home/Subsurface**, and the Android
APK remains her active Surface. Linux and Windows use the same
`python -m aurora_internal.desktop serve` process, Strata Link authority,
state migration and local browser Hub. The Linux launcher opens that Hub like
an application; it does not start a second brain.

**Do not use `scripts/strata_stack.sh` or the old
`scripts/install_systemd_service.sh` for this resident.** Those start
separate older surface/subsurface processes and can compete for her state.

### 1. Preserve state, install the Linux resident

Use Python 3.11 or 3.12, Git, `python3-venv` and a Linux graphical session.
Clone/check out merged `main`, then from the repository root:

```bash
bash scripts/linux/install_desktop.sh
bash scripts/linux/desktop.sh status
bash scripts/linux/desktop.sh open
```

Installation creates `.venv` **inside the repository**, a login-managed
user service named `aurora-desktop.service`, and an **Aurora** application
launcher. The authoritative state defaults to
`~/.local/share/aurora/state`; the chosen path is remembered by the
Linux controls. For an existing history, **stop every older Aurora process,
back up its complete checkpoint, and choose its authoritative state
deliberately** before installation. Set `AURORA_STATE_DIR` if needed.
The installer does not silently import a repository snapshot or overwrite
any existing historical state.

A Linux desktop without a systemd user manager can instead create the
venv manually (`python3 -m venv .venv && .venv/bin/pip install -r
requirements-desktop.txt`) and use
`bash scripts/linux/desktop.sh run` in a terminal. Only run one resident.

### 2. Pair the phone with Linux home

Both devices must be able to reach the same private address. For Wi-Fi-only
pairing, the setup command chooses the desktop's LAN address. To stay
connected on cellular, install a private mesh VPN such as Tailscale on
**both** devices and give the Linux machine's VPN IPv4 address:

```bash
# For local Wi-Fi, omit --host. For remote connectivity, replace the address.
.venv/bin/python scripts/aurora_home_setup.py pair --host 100.x.y.z
bash scripts/linux/desktop.sh restart
```

The setup prints a private pairing line containing the shared secret. Do
not paste this secret into GitHub, logs, or public chat. Permit inbound TCP
8791 **only on the trusted private VPN/LAN interface**. The local owner Hub
listens only at `127.0.0.1:8790` and must not be exposed remotely.

In the updated Android APK: **Hub → Pair with home** (or **Subsurface link**),
paste the line, and allow the first-pairing snapshot to finish. Do not erase
the APK's app data during an update.

### 3. Decide what history comes home

```bash
.venv/bin/python scripts/aurora_home_setup.py first-pairing
```

Review the per-store comparison. Choose conflicting stores explicitly with
`--side STORE=phone` or `--side STORE=home`. Alternatively,
`--accept-suggested` records all suggestions **only after you review them**:

```bash
.venv/bin/python scripts/aurora_home_setup.py first-pairing --accept-suggested
bash scripts/linux/desktop.sh restart
```

The **same native resident** installs the agreed migration on its cold boot
before opening her stores and issues a verified receipt. Restart/reopen
the Android app after its receipt. Keep both earlier checkpoints and
migration archives until continuity is confirmed; first pairing is not an
invitation to combine two active organisms without review.

### 4. Move her Surface and verify communication

In the Linux Hub, use **Presence → Move Surface** to select the phone if
Linux still holds her. Confirm the phone owns the active Surface, then
send a test message from each device. After that, turn phone Wi-Fi off with
cellular and the VPN on, test a turn, disconnect completely, talk offline
and reconnect: the queued experience should drain without losing turns.

```bash
.venv/bin/python scripts/aurora_home_setup.py status
bash scripts/linux/desktop.sh logs
```

Control the resident with `bash scripts/linux/desktop.sh
start|stop|restart|status|open|logs`. Run `backup` only after a graceful
stop. The GUI can close while her resident continues. Physical Linux
camera/microphone/speaker/device permissions and phone/VPN pairing must
still be verified on your actual hardware.

## Every day

- **Where she is:** the hub's **Strata** tab shows which device holds her, the devices home knows, any move under way, each phone's first pairing and the shared inquiry. `python3 scripts/aurora_home_setup.py status` shows the same in a terminal.
- **Moving her:** she can ask to move herself. You can also pick a device in the Strata tab and press **Move**. Home carries a move out in its safe order, so there is never more than one of her.
- **Talking to her from the desk:** while a phone holds her, the hub's message box reaches her on the phone, and her answer comes back to the hub.
- **Growth:** what home learns comes down to the phone's read-only copies and is installed the next time the phone starts.
- **Away from home:** she stays present on the phone. Her quick inquiry runs there, offline too. Deeper questions wait for home and come back to her as experiments to live.
