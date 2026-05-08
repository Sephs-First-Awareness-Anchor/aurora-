#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo $0 [aurora-user]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBSURFACE_TEMPLATE="$REPO_ROOT/deploy/aurora-subsurface.service"
SURFACE_TEMPLATE="$REPO_ROOT/deploy/aurora-surface.service"
STRATA_HUB_TEMPLATE="$REPO_ROOT/deploy/aurora-strata-hub.service"
STRATA_ROOM_TEMPLATE="$REPO_ROOT/deploy/aurora-strata-room.service"
SUBSURFACE_DEST="/etc/systemd/system/aurora-subsurface.service"
SURFACE_DEST="/etc/systemd/system/aurora-surface.service"

AURORA_USER="${1:-${SUDO_USER:-}}"
if [[ -z "$AURORA_USER" || "$AURORA_USER" == "root" ]]; then
  echo "Pass the Aurora user explicitly when running as root without sudo." >&2
  exit 1
fi

AURORA_HOME="$(getent passwd "$AURORA_USER" | cut -d: -f6)"
if [[ -z "$AURORA_HOME" ]]; then
  echo "Unable to resolve home directory for user: $AURORA_USER" >&2
  exit 1
fi

AURORA_UID="$(id -u "$AURORA_USER")"
USER_SYSTEMD_DIR="$AURORA_HOME/.config/systemd/user"
USER_WANTS_DIR="$USER_SYSTEMD_DIR/default.target.wants"
HUB_WANTS_DIR="$USER_SYSTEMD_DIR/graphical-session.target.wants"
USER_AURORA_SERVICE="$USER_SYSTEMD_DIR/aurora.service"
USER_HUB_SERVICE="$USER_SYSTEMD_DIR/aurora-hub.service"
USER_ROOM_SERVICE="$USER_SYSTEMD_DIR/aurora-room.service"
USER_STRATA_HUB_SERVICE="$USER_SYSTEMD_DIR/aurora-strata-hub.service"
USER_STRATA_ROOM_SERVICE="$USER_SYSTEMD_DIR/aurora-strata-room.service"

render_template() {
  local template="$1"
  local dest="$2"
  local mode="${3:-0644}"
  sed \
    -e "s|__AURORA_USER__|$AURORA_USER|g" \
    -e "s|__AURORA_HOME__|$AURORA_HOME|g" \
    -e "s|__AURORA_ROOT__|$REPO_ROOT|g" \
    -e "s|__AURORA_UID__|$AURORA_UID|g" \
    "$template" > "$dest"
  chmod "$mode" "$dest"
}

install -d -m 0755 /etc/systemd/system
render_template "$SUBSURFACE_TEMPLATE" "$SUBSURFACE_DEST"
render_template "$SURFACE_TEMPLATE" "$SURFACE_DEST"

install -d -o "$AURORA_USER" -g "$AURORA_USER" -m 0755 "$USER_SYSTEMD_DIR" "$USER_WANTS_DIR" "$HUB_WANTS_DIR"
render_template "$STRATA_HUB_TEMPLATE" "$USER_STRATA_HUB_SERVICE" 0600
render_template "$STRATA_ROOM_TEMPLATE" "$USER_STRATA_ROOM_SERVICE" 0600
chown "$AURORA_USER:$AURORA_USER" "$USER_STRATA_HUB_SERVICE" "$USER_STRATA_ROOM_SERVICE"
ln -sfn "$USER_STRATA_HUB_SERVICE" "$HUB_WANTS_DIR/aurora-strata-hub.service"
ln -sfn "$USER_STRATA_ROOM_SERVICE" "$HUB_WANTS_DIR/aurora-strata-room.service"

if [[ -S "/run/user/$AURORA_UID/bus" ]]; then
  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user stop aurora.service || true

  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user disable aurora.service || true

  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user stop aurora-hub.service || true

  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user disable aurora-hub.service || true

  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user stop aurora-room.service || true

  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user disable aurora-room.service || true
fi

if [[ -e "$USER_WANTS_DIR/aurora.service" ]]; then
  rm -f "$USER_WANTS_DIR/aurora.service"
fi

if [[ -e "$HUB_WANTS_DIR/aurora-hub.service" ]]; then
  rm -f "$HUB_WANTS_DIR/aurora-hub.service"
fi

if [[ -e "$HUB_WANTS_DIR/aurora-room.service" ]]; then
  rm -f "$HUB_WANTS_DIR/aurora-room.service"
fi

if [[ -S "/run/user/$AURORA_UID/bus" ]]; then
  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user daemon-reload || true

  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user restart aurora-strata-hub.service || true

  runuser -u "$AURORA_USER" -- env \
    XDG_RUNTIME_DIR="/run/user/$AURORA_UID" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$AURORA_UID/bus" \
    systemctl --user restart aurora-strata-room.service || true
fi

systemctl daemon-reload
systemctl disable --now aurora.service || true
systemctl enable aurora-subsurface.service aurora-surface.service
systemctl restart aurora-subsurface.service
systemctl restart aurora-surface.service

echo "Installed $SUBSURFACE_DEST and $SURFACE_DEST for $AURORA_USER"
echo "Installed user services: aurora-strata-hub.service and aurora-strata-room.service"
echo "Classic aurora.service is disabled to avoid duplicate daemons."
echo "Check status with: systemctl status aurora-subsurface aurora-surface --no-pager"
echo "Follow logs with: journalctl -u aurora-subsurface -u aurora-surface -f"
