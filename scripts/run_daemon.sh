#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ENTRY_SCRIPT="${AURORA_DAEMON_ENTRY:-aurora_daemon.py}"
LOCK_NAME="${AURORA_DAEMON_LOCK_NAME:-aurora_daemon}"
LOG_LABEL="${AURORA_DAEMON_LABEL:-aurora-daemon}"
ALLOW_X_CLIENTS="${AURORA_ALLOW_X_CLIENTS:-0}"
PYTHON_BIN=""

pick_python_bin() {
  local candidate
  for candidate in \
    "../.venv/bin/python" \
    "../.venv/bin/python3" \
    ".venv/bin/python" \
    ".venv/bin/python3" \
    "python3" \
    "python"
  do
    if [[ "$candidate" == *"/"* ]]; then
      [[ -x "$candidate" ]] || continue
    else
      command -v "$candidate" >/dev/null 2>&1 || continue
    fi
    if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
print(sys.version)
PY
    then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

pid_matches_daemon() {
  local pid="${1:-}"
  [[ -n "$pid" ]] || return 1
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  local cmdline
  cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  [[ "$cmdline" == *"$ENTRY_SCRIPT"* || "$cmdline" == *"$LOCK_NAME"* ]]
}

# ── Single-instance guard ────────────────────────────────────────────────────
LOCK_FILE="${TMPDIR:-/tmp}/${LOCK_NAME}.lock"
if [[ -f "$LOCK_FILE" ]]; then
    EXISTING_PID=$(cat "$LOCK_FILE" 2>/dev/null || true)
    if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null && pid_matches_daemon "$EXISTING_PID"; then
        echo "[$LOG_LABEL] Already running as PID $EXISTING_PID - exiting."
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT HUP INT TERM

PYTHON_BIN="$(pick_python_bin || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[$LOG_LABEL] No usable Python runtime found."
  exit 1
fi

export CLAUDE_TTS_VOICE="${CLAUDE_TTS_VOICE:-en-GB-SoniaNeural}"

if [[ "$ALLOW_X_CLIENTS" =~ ^(1|true|yes|on)$ ]]; then
  if [[ -z "${XAUTHORITY:-}" ]]; then
    runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    xauth_candidate="$(find "$runtime_dir" -maxdepth 1 -name '.mutter-Xwaylandauth.*' 2>/dev/null | head -n 1)"
    if [[ -n "$xauth_candidate" ]]; then
      export XAUTHORITY="$xauth_candidate"
    elif [[ -f "$HOME/.Xauthority" ]]; then
      export XAUTHORITY="$HOME/.Xauthority"
    fi
  fi
else
  unset DISPLAY
  unset WAYLAND_DISPLAY
  unset XAUTHORITY
fi

if [[ -z "${PULSE_SERVER:-}" ]]; then
  runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  if [[ -S "$runtime_dir/pulse/native" ]]; then
    export PULSE_SERVER="unix:$runtime_dir/pulse/native"
  fi
fi

skip_dep_install="${AURORA_SKIP_DEP_INSTALL:-0}"
if [[ "$skip_dep_install" =~ ^(1|true|yes)$ ]]; then
  echo "[$LOG_LABEL] Skipping dependency installation (AURORA_SKIP_DEP_INSTALL=$skip_dep_install)."
else
  "$PYTHON_BIN" -m pip install --upgrade pip --quiet

  # Install missing deps silently during manual/bootstrap runs.
  "$PYTHON_BIN" - <<'PY'
import importlib.util
mods = {
    'numpy': 'numpy',
    'speech_recognition': 'SpeechRecognition',
    'sounddevice': 'sounddevice',
    'evdev': 'evdev',
    'pynput': 'pynput',
    'pocketsphinx': 'pocketsphinx',
    'edge_tts': 'edge-tts',
    'pyttsx3': 'pyttsx3',
    'PIL': 'Pillow',
    'soundfile': 'soundfile',
}
missing = [pkg for mod, pkg in mods.items() if importlib.util.find_spec(mod) is None]
if missing:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing, '--quiet'])
PY
fi

echo "[$LOG_LABEL] Starting $ENTRY_SCRIPT..."
exec "$PYTHON_BIN" -u "$ENTRY_SCRIPT"
