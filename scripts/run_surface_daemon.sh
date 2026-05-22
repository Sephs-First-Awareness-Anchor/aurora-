#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AURORA_DAEMON_ENTRY="aurora_surface_daemon.py"
export AURORA_DAEMON_LOCK_NAME="aurora_surface_daemon"
export AURORA_DAEMON_LABEL="aurora-surface"
export AURORA_KEYBOARD_BACKEND="${AURORA_KEYBOARD_BACKEND:-evdev}"
export AURORA_ALLOW_X_CLIENTS="${AURORA_ALLOW_X_CLIENTS:-0}"
export AURORA_ENABLE_ROOM_OPERATOR="${AURORA_ENABLE_ROOM_OPERATOR:-0}"
export AURORA_ENABLE_QUIET_WINDOW="${AURORA_ENABLE_QUIET_WINDOW:-0}"
export AURORA_TTS_ROUTE="${AURORA_TTS_ROUTE:-simple_first}"
export AURORA_SKIP_HARDWARE_IMPORTS=0

bash "$SCRIPT_DIR/run_daemon.sh"
