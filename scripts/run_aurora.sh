#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "[aurora] Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/aurora"
LEASE_FILE="$CONFIG_DIR/autonomous_access_lease"
mkdir -p "$CONFIG_DIR"

AUTONOMOUS_ACCESS=0
AUTONOMOUS_UNTIL=0
if [[ -f "$LEASE_FILE" ]]; then
  lease="$(cat "$LEASE_FILE" 2>/dev/null || true)"
  now="$(date +%s)"
  if [[ "$lease" =~ ^[0-9]+$ ]] && (( lease > now )); then
    AUTONOMOUS_ACCESS=1
    AUTONOMOUS_UNTIL="$lease"
  fi
fi

export AURORA_AUTONOMOUS_ACCESS="$AUTONOMOUS_ACCESS"
export AURORA_AUTONOMOUS_UNTIL="$AUTONOMOUS_UNTIL"

if [[ "$AUTONOMOUS_ACCESS" == "1" ]]; then
  echo "[aurora] Autonomous system access is ACTIVE until epoch $AUTONOMOUS_UNTIL"
else
  echo "[aurora] Autonomous system access is INACTIVE (conversation-only mode for system actions)"
fi

# Install only if missing to keep restart fast.
python - <<'PY'
import importlib.util
mods = {
    'numpy': 'numpy',
    'speech_recognition': 'SpeechRecognition',
    'sounddevice': 'sounddevice',
    'PIL': 'Pillow',
    'soundfile': 'soundfile',
    'librosa': 'librosa',
    'pydub': 'pydub',
}
missing = [pkg for mod, pkg in mods.items() if importlib.util.find_spec(mod) is None]
if missing:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
PY

exec python aurora.py
