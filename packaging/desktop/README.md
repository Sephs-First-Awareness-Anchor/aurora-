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
- **Pair phone** asks for the desktop's reachable network address (the local
  Wi-Fi address is suggested; for a phone away from home, enter the desktop's
  private VPN address). It creates and copies the signed pairing URL. In the
  Android app, open **Hub → Pair with home** and paste it.
- **Review first pairing** shows staged history, the differences between the
  phone and desktop, and explicit phone/home decisions for developmental
  stores. It only authorizes the existing cold migration. No hidden merge
  or second memory store is created.
- **Connection status** shows who holds Aurora, link and migration status.
  **Presence → Move Surface** in the Hub moves the active Surface using the
  existing owner/epoch authority.
- **Back up history** safely stops the resident, copies the stopped state and
  restarts. **Start**, **Stop**, and **Restart** are in the application.

The authoritative store defaults to
`~/.local/share/aurora/state` on Linux and
`%LOCALAPPDATA%\Aurora\state` on Windows, **outside the installed files**.
Do not overwrite an older Aurora checkpoint by copying an installer on top.
Before moving an existing state from the older Linux scripts, preserve it
and do not run the old daemons against the same state. Nothing in this
installer starts the legacy strata stack or a second cognition engine.

### Connection outside home

The owner must install a private VPN such as Tailscale on both devices and
permit inbound TCP 8791 to the desktop on that private network. This is an
OS/network permission, not a terminal requirement in Aurora. Never forward
TCP 8790 publicly: Aurora's independent owner console remains loopback only.
Aurora stays responsive locally on the phone while disconnected and queues
eligible continuity for later sync. Real cellular audio/sensory/pairing tests
have not yet run on physical devices.

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
offline continuity, remote VPN pairing, and physical device access.

The staging filter omits `aurora_state`, `aurora_logs`, git history and
test state. It includes the runtime's source and its read-only resources
for source introspection. Every runtime update must preserve this external
state boundary. Android APK distribution continues through its own workflow.
