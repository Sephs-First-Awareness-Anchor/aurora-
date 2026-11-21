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
- **Pair phone** checks the desktop's *live Tailscale connection* and
  automatically selects its stable private VPN IPv4 address. An ordinary
  home-Wi-Fi address is **not** silently offered as remote-capable. If
  Tailscale is missing, an in-app setup button opens its official
  installation page. The owner must connect the Linux/Windows desktop and
  Android phone to the same Tailnet once, including Android's system VPN
  permission. After that, Aurora creates and copies the signed pairing
  line. In Android **Hub → Pair with home** paste it.
- **Review first pairing** shows staged history, the differences between the
  phone and desktop, and explicit phone/home decisions for developmental
  stores. It only authorizes the existing cold migration. No hidden merge
  or second memory store is created.
- **Connection status** shows the desktop's actual mesh VPN state, selected
  route, holder, and migration. Android's Hub distinguishes a remote VPN
  route from LAN-only pairing and includes **Test home connection** for a
  real signed network exchange over cellular. **Presence → Move Surface**
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

The current release requires the Tailscale system client on both devices,
joined to the same Tailnet. That one-time OS networking step is **not yet
fully embedded inside the Aurora package**; it can be initiated in Aurora
without a terminal. Permit inbound TCP 8791 only on the trusted private VPN
interface. Never forward TCP 8790 publicly: Aurora's independent owner
console remains loopback only. It is essential that the home machine
remain powered, awake, connected and running its resident. When the home
machine sleeps or loses internet, live subsurface exchange is impossible:
the phone continues locally and eligible continuity is queued for retry.
Android's app/service and OS VPN must also be allowed to run on cellular
under the phone's battery settings. Real off-site hardware tests remain
required before calling the feature dependable.

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
