#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$REPO_ROOT/aurora_state"
STACK_DIR="$STATE_DIR/strata_stack"
PID_DIR="$STACK_DIR/pids"
LOG_DIR="$STACK_DIR/logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

ACTION="${1:-restart}"

ensure_runtime_env() {
  export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && -S "$XDG_RUNTIME_DIR/bus" ]]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
  fi
  if [[ -z "${PULSE_SERVER:-}" && -S "$XDG_RUNTIME_DIR/pulse/native" ]]; then
    export PULSE_SERVER="unix:$XDG_RUNTIME_DIR/pulse/native"
  fi
}

user_service_available() {
  local service_name="$1"
  [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]] || return 1
  local fragment_path
  fragment_path="$(systemctl --user show "$service_name" --property=FragmentPath --value 2>/dev/null || true)"
  [[ -n "$fragment_path" ]]
}

system_service_available() {
  local service_name="$1"
  local fragment_path
  fragment_path="$(systemctl show "$service_name" --property=FragmentPath --value 2>/dev/null || true)"
  [[ -n "$fragment_path" ]]
}

start_system_service() {
  local service_name="$1"
  systemctl restart "$service_name" >/dev/null 2>&1 || systemctl start "$service_name" >/dev/null 2>&1
}

stop_system_service() {
  local service_name="$1"
  systemctl stop "$service_name" >/dev/null 2>&1 || true
}

start_user_service() {
  local service_name="$1"
  systemctl --user restart "$service_name" >/dev/null 2>&1 || systemctl --user start "$service_name" >/dev/null 2>&1
}

stop_user_service() {
  local service_name="$1"
  [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]] || return 0
  systemctl --user stop "$service_name" >/dev/null 2>&1 || true
}

pidfile_for() {
  local name="$1"
  echo "$PID_DIR/$name.pid"
}

logfile_for() {
  local name="$1"
  echo "$LOG_DIR/$name.log"
}

is_pid_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

stop_by_pidfile() {
  local name="$1"
  local pidfile
  pidfile="$(pidfile_for "$name")"
  if [[ ! -f "$pidfile" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if is_pid_alive "$pid"; then
    kill "$pid" 2>/dev/null || true
    for _ in {1..30}; do
      if ! is_pid_alive "$pid"; then
        break
      fi
      sleep 0.2
    done
    if is_pid_alive "$pid"; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$pidfile"
}

stop_by_pattern() {
  local pattern="$1"
  pkill -f "$pattern" 2>/dev/null || true
}

launch_component() {
  local name="$1"
  shift

  local pidfile logfile
  pidfile="$(pidfile_for "$name")"
  logfile="$(logfile_for "$name")"

  : > "$logfile"
  (
    cd "$REPO_ROOT"
    nohup "$@" >>"$logfile" 2>&1 &
    echo $! > "$pidfile"
  )
  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  echo "[strata-stack] started $name (pid ${pid:-unknown})"
}

stop_stack() {
  echo "[strata-stack] stopping running strata components..."
  stop_user_service "aurora-strata-room.service"
  stop_user_service "aurora-strata-hub.service"
  if system_service_available "aurora-surface.service"; then
    stop_system_service "aurora-surface.service"
  fi
  if system_service_available "aurora-subsurface.service"; then
    stop_system_service "aurora-subsurface.service"
  fi
  stop_by_pidfile "room"
  stop_by_pidfile "hub"
  stop_by_pidfile "surface"
  stop_by_pidfile "subsurface"

  # Clean up older/manual launches too so a restart yields one coherent stack.
  stop_by_pattern "aurora_surface_daemon.py"
  stop_by_pattern "aurora_subsurface_daemon.py"
  stop_by_pattern "aurora_hub.py"
  stop_by_pattern "aurora_room.py"

  # Compress state at rest — rotate logs then pack cold dirs to .cz archives.
  echo "[strata-stack] compressing aurora state..."
  python3 "$SCRIPT_DIR/aurora_state_compress.py" pack 2>&1 | sed 's/^/  /' || true
}

start_stack() {
  ensure_runtime_env

  # Restore any cold-packed .cz archives before services need them.
  echo "[strata-stack] restoring compressed state..."
  python3 "$SCRIPT_DIR/aurora_state_compress.py" unpack 2>&1 | sed 's/^/  /' || true

  echo "[strata-stack] starting strata stack from $REPO_ROOT"
  if system_service_available "aurora-subsurface.service"; then
    start_system_service "aurora-subsurface.service"
    echo "[strata-stack] started subsurface via system service"
    rm -f "$(pidfile_for "subsurface")"
  else
    launch_component "subsurface" "$SCRIPT_DIR/run_subsurface_daemon.sh"
  fi
  sleep 2
  if system_service_available "aurora-surface.service"; then
    start_system_service "aurora-surface.service"
    echo "[strata-stack] started surface via system service"
    rm -f "$(pidfile_for "surface")"
  else
    launch_component "surface" "$SCRIPT_DIR/run_surface_daemon.sh"
  fi
  sleep 2
  if user_service_available "aurora-strata-hub.service"; then
    start_user_service "aurora-strata-hub.service"
    echo "[strata-stack] started hub via user service"
    rm -f "$(pidfile_for "hub")"
  else
    launch_component "hub" "$SCRIPT_DIR/run_hub.sh"
  fi
  sleep 1
  if user_service_available "aurora-strata-room.service"; then
    start_user_service "aurora-strata-room.service"
    echo "[strata-stack] started room via user service"
    rm -f "$(pidfile_for "room")"
  else
    launch_component "room" "$SCRIPT_DIR/run_room.sh"
  fi
  echo "[strata-stack] logs: $LOG_DIR"
}

status_component() {
  local name="$1"
  if [[ "$name" == "subsurface" ]] && system_service_available "aurora-subsurface.service"; then
    printf '%-12s %-8s %s\n' "$name" "service" "aurora-subsurface.service"
    return 0
  fi
  if [[ "$name" == "surface" ]] && system_service_available "aurora-surface.service"; then
    printf '%-12s %-8s %s\n' "$name" "service" "aurora-surface.service"
    return 0
  fi
  if [[ "$name" == "hub" ]] && user_service_available "aurora-strata-hub.service"; then
    printf '%-12s %-8s %s\n' "$name" "service" "aurora-strata-hub.service"
    return 0
  fi
  if [[ "$name" == "room" ]] && user_service_available "aurora-strata-room.service"; then
    printf '%-12s %-8s %s\n' "$name" "service" "aurora-strata-room.service"
    return 0
  fi
  local pidfile pid status
  pidfile="$(pidfile_for "$name")"
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if is_pid_alive "$pid"; then
    status="running"
  else
    status="stopped"
  fi
  printf '%-12s %-8s %s\n' "$name" "$status" "${pid:-no-pid}"
}

show_status() {
  echo "[strata-stack] component status"
  status_component "subsurface"
  status_component "surface"
  status_component "hub"
  status_component "room"
  echo "[strata-stack] logs: $LOG_DIR"
}

case "$ACTION" in
  start)
    start_stack
    ;;
  stop)
    stop_stack
    ;;
  restart)
    stop_stack
    sleep 1
    start_stack
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}" >&2
    exit 1
    ;;
esac
