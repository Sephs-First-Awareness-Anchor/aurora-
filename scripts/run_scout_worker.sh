#!/usr/bin/env bash
set -euo pipefail

# Aurora Build 694 step 16 (Subsurface Presence and Evidence Scout spec,
# section 26): the desktop launcher for aurora_scout_daemon.py -- the
# same lightweight, disposable worker Android starts in-process
# (aurora_bridge._start_scout_worker) but here run as its own separate
# process, matching how Room/Hub/Surface/Subsurface are already each
# their own process on desktop. No display/GUI dependency (unlike
# run_room.sh/run_hub.sh) -- the Scout worker is headless.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="${AURORA_SCOUT_STATE_DIR:-$REPO_ROOT/aurora_state}"

cd "$REPO_ROOT"

pick_python() {
  local candidate
  for candidate in "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/.venv/bin/python3" "python3"; do
    if [[ "$candidate" == *"/"* ]]; then
      [[ -x "$candidate" ]] && echo "$candidate" && return 0
      continue
    fi
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(pick_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[aurora-scout] No usable python3 interpreter found." >&2
  exit 1
fi

echo "[aurora-scout] Launching with $PYTHON_BIN, state_dir=$STATE_DIR"
exec "$PYTHON_BIN" -u aurora_scout_daemon.py --state-dir="$STATE_DIR"
