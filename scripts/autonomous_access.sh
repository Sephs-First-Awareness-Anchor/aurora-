#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/aurora"
LEASE_FILE="$CONFIG_DIR/autonomous_access_lease"
mkdir -p "$CONFIG_DIR"

usage() {
  cat <<'EOF'
Usage:
  autonomous_access.sh grant [minutes]   Grant autonomous system access lease (default: 30m)
  autonomous_access.sh revoke            Revoke autonomous access immediately
  autonomous_access.sh status            Print lease status

This script controls time-scoped autonomous access for Aurora.
Aurora startup scripts can read this lease and set runtime flags.
EOF
}

now_epoch() {
  date +%s
}

format_ts() {
  date -d "@$1" '+%Y-%m-%d %H:%M:%S %Z'
}

cmd="${1:-status}"

case "$cmd" in
  grant)
    minutes="${2:-30}"
    if ! [[ "$minutes" =~ ^[0-9]+$ ]]; then
      echo "Minutes must be an integer" >&2
      exit 1
    fi
    expires=$(( $(now_epoch) + minutes * 60 ))
    printf '%s\n' "$expires" > "$LEASE_FILE"
    echo "Autonomous access GRANTED for ${minutes} minute(s), until $(format_ts "$expires")."
    ;;
  revoke)
    rm -f "$LEASE_FILE"
    echo "Autonomous access REVOKED."
    ;;
  status)
    if [[ -f "$LEASE_FILE" ]]; then
      expires="$(cat "$LEASE_FILE" 2>/dev/null || true)"
      if [[ "$expires" =~ ^[0-9]+$ ]] && (( expires > $(now_epoch) )); then
        remaining=$(( expires - $(now_epoch) ))
        echo "Autonomous access: ACTIVE (${remaining}s remaining, until $(format_ts "$expires"))."
        exit 0
      fi
    fi
    echo "Autonomous access: INACTIVE."
    exit 1
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
