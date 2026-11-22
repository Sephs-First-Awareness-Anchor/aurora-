# Aurora desktop application

**One resident, one history, two operating systems.** This directory builds
Aurora's existing Python organism and a native Qt WebEngine desktop window as
installable artifacts. The Android app remains the Surface and pairs to the
same signed Strata Link used by the desktop.

## What the owner installs and operates

- On Ubuntu/Debian Linux (x86-64), install **Aurora-Linux-amd64.deb** from the
  successful GitHub Actions *Desktop app installers* run. Find **Aurora**
  in the applications menu and launch it.
- On Windows (x86-64), run **Aurora-Setup-Windows-x64.exe** from the same
  successful workflow and open **Aurora** from Start.
- Nothing requires terminal commands on an installed user's machine. The
  application launches the persistent resident automatically; the Hub's
  owner console is bound to loopback only. Closing the window does not stop
  the resident. Use **Run at login** inside the app to launch its resident
  automatically after sign-in.
- **Pair phone** opens a native desktop dialog for Aurora's own HTTPS
  relay address and the gateway's registration key. It registers a private
  room, configures the resident's outbound connection, discovers the local
  LAN address as an optional fast path, and copies one private pairing link.
  On Android, use **Hub → Pair with home** and paste. No VPN client,
  router port forwarding or terminal is required on either installed app.
  A public HTTPS relay *does need to exist*, and the dialog will not invent
  one: see [relay hosting](../relay/README.md). The room and credentials
  persist across app restarts.
- **Review first pairing** shows staged history, the differences between the
  phone and desktop, and explicit phone/home decisions for developmental
  stores. It only authorizes the existing cold migration. No hidden merge
  or second memory store is created.
- **Connection status** reports configuration and the resident's live
  relay connection separately, alongside holder and migration. The Android
  Hub shows whether the last exchange used **local**, **encrypted relay**,
  or no connection, and includes **Test home connection** on cellular. **Presence → Move Surface**
  uses the existing owner/epoch authority.
- **Back up history** safely stops the resident, copies the stopped state and
  restarts. **Start**, **Stop**, and **Restart** are in the application.
  **Keep home awake** requests an OS idle-sleep inhibition while Aurora's
  resident is running, with an explicit power-use warning. It does not
  defeat shutdown, lid-closure policy, all OS power rules, or an outage.

The authoritative store defaults to
`~/.local/share/aurora/state` on Linux and
`%LOCALAPPDATA%\Aurora\state` on Windows, **outside the installed files**.
Do not overwrite an older Aurora checkpoint by copying an installer on top.
Before moving an existing state from the older Linux scripts, preserve it
and do not run the old daemons against the same state. Nothing in this
installer starts the legacy strata stack or a second cognition engine.

### Connection outside home

Aurora's **built-in internet relay** exchanges encrypted packets over HTTPS.
The desktop resident opens an outbound connection to a publicly reachable
relay gateway; the phone's Surface uses that same gateway when away. The
gateway forwards only opaque AES-GCM ciphertext; it has no access to the
Strata Link signing secret, the encryption key, owner tokens, Hub, crystals,
or the desktop's state. Aurora's desktop service and Android Surface still
run the existing single signed Strata Link, using the same identity,
continuity and durable outboxes. A direct LAN connection takes priority
when available, and never requires an internet hop.

A relay is an *external reachability service*, not a second Aurora process.
The desktop app includes pairing, reconnect and diagnostics, but does not
magically create a public internet host behind a residential NAT. The
[relay gateway](../relay/README.md) is included in this repository and
can be hosted once on a public HTTPS address; the desktop UI accepts that
address and its gateway registration key. **Until a gateway is deployed and
configured, remote internet pairing is not operational.** Merely copying
a link is not evidence of off-site access.

Keep the home laptop powered, awake, internet-connected, and running the
resident. Ethernet is fine; home Wi-Fi specifically is not required. If
home loses internet or sleeps, the phone Surface continues her independent
present cognition and queues continuity until contact returns. If the phone
has no service, she also works locally. For an initial deployment test,
switch the phone to cellular, use **Test home connection**, then confirm
the desktop's Connection status reports the encrypted relay online.
Physical device validation is still required.

Never forward the local Hub's port 8790 or the raw Strata port 8791 publicly.
Only the relay's HTTPS endpoint should be publicly accessible. Keep the
private pairing link and gateway registration key out of logs and messages.
The local fast path uses the existing signed HTTP LAN protocol and is
not itself encrypted; if the home LAN is untrusted, disable the local URL
and use the end-to-end encrypted relay exclusively.

## Packaging and developer build

Building occurs in GitHub Actions, not on the end-user machine.
The workflow uses Python 3.11, PyInstaller, PySide6 WebEngine, a Linux
`.deb` packager and Inno Setup for Windows. Both builds use the **same**
`packaging/desktop/aurora_desktop.py` entry point and the same
`aurora_internal.desktop.DesktopRuntime`.

Run *Desktop app installers* from GitHub Actions if a build is needed outside a PR.
The workflow checks bundled importability and uploads a platform-specific
installer. A passing import check is **not** proof of operational hardware
availability. The first real Linux/Android test must verify startup,
resident persistence when closing the window, history reconciliation,
offline continuity, encrypted HTTPS relay from cellular, and physical device access.

The staging filter omits `aurora_state`, `aurora_logs`, git history and
test state. It includes the runtime's source and its read-only resources
for source introspection. Every runtime update must preserve this external
state boundary. Android APK distribution continues through its own workflow.
