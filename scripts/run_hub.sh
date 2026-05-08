#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

detect_display() {
  if [[ -n "${DISPLAY:-}" ]]; then
    return 0
  fi

  local xwayland_display
  xwayland_display="$(pgrep -u "$(id -u)" -af "/usr/bin/Xwayland :" \
    | sed -n 's/.*Xwayland \(:[0-9]\+\).*/\1/p' \
    | head -n 1)"
  if [[ -n "$xwayland_display" ]]; then
    export DISPLAY="$xwayland_display"
    return 0
  fi

  return 1
}

detect_xauthority() {
  if [[ -n "${XAUTHORITY:-}" && -f "${XAUTHORITY}" ]]; then
    return 0
  fi

  local runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  local candidate

  candidate="$(find "$runtime_dir" -maxdepth 1 -name '.mutter-Xwaylandauth.*' 2>/dev/null | head -n 1)"
  if [[ -n "$candidate" && -f "$candidate" ]]; then
    export XAUTHORITY="$candidate"
    return 0
  fi

  if [[ -f "${HOME}/.Xauthority" ]]; then
    export XAUTHORITY="${HOME}/.Xauthority"
    return 0
  fi

  return 1
}

# Only launch if a display is available
if ! detect_display && [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "[aurora-hub] No display found -- hub requires a graphical session."
  exit 0
fi

detect_xauthority || true

pick_python() {
  local candidate
  for candidate in "../.venv/bin/python" "../.venv/bin/python3" ".venv/bin/python" ".venv/bin/python3" "python3"; do
    if [[ "$candidate" == *"/"* && ! -x "$candidate" ]]; then
      continue
    fi
    if "$candidate" - <<'PY' >/dev/null 2>&1
import tkinter  # noqa: F401
from PIL import ImageTk  # noqa: F401
PY
    then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

wait_for_tk_display() {
  local python_bin="$1"
  local attempts="${2:-20}"
  local i

  for ((i=1; i<=attempts; i++)); do
    if "$python_bin" - <<'PY' >/dev/null 2>&1
import tkinter as tk
root = tk.Tk()
root.withdraw()
root.update_idletasks()
root.destroy()
PY
    then
      return 0
    fi
    sleep 1
  done

  return 1
}

PYTHON_BIN="$(pick_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[aurora-hub] Missing GUI dependencies. Aurora Hub requires tkinter + PIL.ImageTk."
  echo "[aurora-hub] Recommended fix: use the project .venv or install a Pillow build with Tk support."
  exit 0
fi

echo "[aurora-hub] Launching with $PYTHON_BIN"
if [[ -n "${DISPLAY:-}" ]]; then
  echo "[aurora-hub] DISPLAY=$DISPLAY"
fi
if [[ -n "${XAUTHORITY:-}" ]]; then
  echo "[aurora-hub] XAUTHORITY=$XAUTHORITY"
fi

if ! wait_for_tk_display "$PYTHON_BIN" 20; then
  echo "[aurora-hub] Tk still cannot reach the display. Exiting cleanly."
  exit 0
fi

exec "$PYTHON_BIN" -u aurora_hub.py
