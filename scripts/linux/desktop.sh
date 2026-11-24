#!/usr/bin/env bash
# Day-to-day Linux controls for the *same* resident used by Windows.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE_FILE="$HOME/.config/aurora/resident-state-dir"
if [[ -n "${AURORA_STATE_DIR:-}" ]]; then
  STATE_DIR="$AURORA_STATE_DIR"
elif [[ -f "$STATE_FILE" ]]; then
  IFS= read -r STATE_DIR < "$STATE_FILE"
else
  STATE_DIR="$HOME/.local/share/aurora/state"
fi
PYTHON="$ROOT/.venv/bin/python"
ACTION="${1:-status}"
UNIT="aurora-desktop.service"

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing virtual environment. Install with scripts/linux/install_desktop.sh or python3 -m venv .venv." >&2
  exit 1
fi

case "$ACTION" in
  run)
    # Foreground alternative when no systemd user service is available.
    # Reuse the same single-process cross-platform engine.
    cd "$ROOT"
    exec "$PYTHON" -m aurora_internal.desktop serve --state-dir "$STATE_DIR" --open
    ;;
  start|stop|restart)
    systemctl --user "$ACTION" "$UNIT"
    ;;
  open|status)
    cd "$ROOT"
    exec "$PYTHON" -m aurora_internal.desktop "$ACTION" --state-dir "$STATE_DIR"
    ;;
  backup)
    if ! command -v flock >/dev/null; then
      echo "Backup requires flock (util-linux) to verify the resident is stopped." >&2
      exit 1
    fi
    mkdir -p "$STATE_DIR"
    dest="${2:-$(dirname "$STATE_DIR")/backup-$(date +%Y%m%d-%H%M%S)}"
    [[ ! -e "$dest" ]] || { echo "Backup exists: $dest" >&2; exit 1; }
    # POSIX lock is identical to aurora_internal.process_lock.ProcessLock.
    (
      flock -n 9 || { echo "Resident is running; stop it and retry." >&2; exit 1; }
      mkdir -p "$dest"
      cp -a "$STATE_DIR/." "$dest/"
      rm -f "$dest/desktop_resident.lock"
    ) 9>"$STATE_DIR/desktop_resident.lock"
    echo "Backup completed: $dest"
    ;;
  logs)
    exec journalctl --user -u "$UNIT" -f
    ;;
  uninstall)
    systemctl --user disable --now "$UNIT"
    echo "Login startup disabled. Your state remains in $STATE_DIR"
    ;;
  *)
    echo "Usage: bash scripts/linux/desktop.sh {run|start|restart|stop|status|open|backup|logs|uninstall}" >&2
    exit 2
    ;;
esac
