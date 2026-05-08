#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${1:-$ROOT_DIR/aurora_state}"
OBSERVER_DIR="$STATE_DIR/quasiarch_observer"
BACKUP_DIR="$STATE_DIR/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [[ -d "$OBSERVER_DIR" ]]; then
  ARCHIVE_PATH="$BACKUP_DIR/quasiarch_observer_${STAMP}"
  mv "$OBSERVER_DIR" "$ARCHIVE_PATH"
  echo "[quasiarch-reset] Archived existing observer state to: $ARCHIVE_PATH"
else
  echo "[quasiarch-reset] No existing observer state found at: $OBSERVER_DIR"
fi

mkdir -p "$OBSERVER_DIR"
cat > "$OBSERVER_DIR/.reset_marker" <<EOF
reset_at=$STAMP
reason=lineage_alignment_refresh
EOF

echo "[quasiarch-reset] Fresh observer state directory ready at: $OBSERVER_DIR"
