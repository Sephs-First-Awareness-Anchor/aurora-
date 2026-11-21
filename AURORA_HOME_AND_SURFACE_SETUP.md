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

## Linux desktop setup

### On the desktop (once)

```
python3 scripts/aurora_home_setup.py pair
scripts/strata_stack.sh restart
```

`pair` finds this machine's address on the home network, names the desktop, and prints one line that looks like `http://192.168.1.20:8791#...`. Keep it private, because it is the key to the link. Restarting the stack makes home listen on that address.

### On the phone (once)

Open the Hub tab, tap **Subsurface link** and paste the line.

If the phone has been living as the whole mind, it sends her history home straight away for the first pairing. She keeps running on the phone as she is while it goes.

### Back on the desktop for the first pairing

```
python3 scripts/aurora_home_setup.py first-pairing
python3 scripts/aurora_home_setup.py first-pairing --accept-suggested --apply --restart-stack
```

The first command shows each store where the phone and home differ. Choose a side for each with `--side store=phone` or `--side store=home`, or take the side that has lived more with `--accept-suggested`. `--apply` installs the result, and `--restart-stack` stops and restarts the stack around it.

The phone picks up home's receipt by itself. From its next start it is her surface.

## Every day

- **Where she is:** the hub's **Strata** tab shows which device holds her, the devices home knows, any move under way, each phone's first pairing and the shared inquiry. `python3 scripts/aurora_home_setup.py status` shows the same in a terminal.
- **Moving her:** she can ask to move herself. You can also pick a device in the Strata tab and press **Move**. Home carries a move out in its safe order, so there is never more than one of her.
- **Talking to her from the desk:** while a phone holds her, the hub's message box reaches her on the phone, and her answer comes back to the hub.
- **Growth:** what home learns comes down to the phone's read-only copies and is installed the next time the phone starts.
- **Away from home:** she stays present on the phone. Her quick inquiry runs there, offline too. Deeper questions wait for home and come back to her as experiments to live.
