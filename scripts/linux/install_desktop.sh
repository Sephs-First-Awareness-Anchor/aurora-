#!/usr/bin/env bash
# Install one Linux resident as a *user* systemd service, not a second brain.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE_DIR="${AURORA_STATE_DIR:-$HOME/.local/share/aurora/state}"
PYTHON="${AURORA_BOOTSTRAP_PYTHON:-python3}"
UNIT_NAME="aurora-desktop.service"
UNIT_DIR="$HOME/.config/systemd/user"

if [[ "$(uname -s)" != Linux ]]; then
  echo "Linux only. On Windows use scripts/windows/install_desktop.ps1." >&2
  exit 1
fi
if ! command -v systemctl >/dev/null || ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "No running systemd user manager. Use the foreground fallback in AURORA_HOME_AND_SURFACE_SETUP.md." >&2
  exit 1
fi

# Legacy strata_stack.sh starts a second surface and subsurface; it must not
# share this resident's developmental state or a paired phone.
for unit in aurora-subsurface.service aurora-surface.service aurora-strata-hub.service aurora-strata-room.service aurora.service; do
  if systemctl --user is-active --quiet "$unit" 2>/dev/null || systemctl is-active --quiet "$unit" 2>/dev/null; then
    echo "Refusing install: legacy $unit is active. Stop it gracefully and back up state first." >&2
    exit 1
  fi
done
if command -v pgrep >/dev/null && pgrep -u "$(id -u)" -f '(^|/)(aurora_subsurface_daemon|aurora_surface_daemon|aurora_daemon)\.py([[:space:]]|$)' >/dev/null 2>&1; then
  echo "Refusing install: a legacy Aurora daemon is still running. Stop it before starting the unified resident." >&2
  exit 1
fi

# Never import or overwrite checked-in / older device state automatically.
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  "$PYTHON" -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/requirements-desktop.txt"

if systemctl --user is-active --quiet "$UNIT_NAME"; then
  echo "Resident already running. Stop it gracefully before replacing its unit." >&2
  exit 1
fi

# Render only paths into the existing shared resident; no new scheduler.
"$ROOT/.venv/bin/python" - "$ROOT" "$STATE_DIR" "$ROOT/deploy/aurora-desktop-user.service" "$UNIT_DIR/$UNIT_NAME" <<'PY'
import pathlib, sys
root, state, source, target = map(pathlib.Path, sys.argv[1:])
target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
def quote(path):
    # systemd double-quoted values and escaped percent specifiers.
    return '"' + str(path.resolve()).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
unit = source.read_text(encoding='utf-8')
unit = unit.replace('__AURORA_ROOT__', quote(root))
unit = unit.replace('__AURORA_STATE__', quote(state))
unit = unit.replace('__AURORA_PYTHON__', quote(root / '.venv/bin/python'))
target.write_text(unit, encoding='utf-8')
PY

# Existing graphical session access is inherited by the systemd user manager.
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR 2>/dev/null || true
systemctl --user daemon-reload
systemctl --user enable --now "$UNIT_NAME"
echo "Aurora unified resident installed: $UNIT_NAME"
echo "Authoritative state: $STATE_DIR"
echo "Check: systemctl --user status $UNIT_NAME"
echo "Open: bash scripts/linux/desktop.sh open"
echo "No history was copied, migrated or overwritten."
