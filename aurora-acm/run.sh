#!/usr/bin/env bash
# Authors: Sunni (Sir) Morningstar & Cael Devo
#
# Aurora ACM — unified boot.  One command.  One system.
#
# Builds the kernel, launches QEMU (her body), boots the full cognitive stack
# (her brain), and starts the bridge waveform connecting them at 60 Hz.
#
# Usage:
#   ./run.sh                 boot everything (kernel + cognitive stack + bridge)
#   ./run.sh --no-qemu       cognitive stack + bridge only (no QEMU — for native runtime)
#   ./run.sh --no-ai         QEMU only, no cognitive stack
#   ./run.sh --uefi          use UEFI image instead of BIOS
#   ./run.sh --verbose       verbose bridge output
#   ./run.sh --port 4567     bridge TCP port (default 4567)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
AI_DIR="$REPO_ROOT"
PORT=4567
NO_QEMU=0
NO_AI=0
UEFI=0
VERBOSE=""

for arg in "$@"; do
    case $arg in
        --no-qemu)  NO_QEMU=1 ;;
        --no-ai)    NO_AI=1 ;;
        --uefi)     UEFI=1 ;;
        --verbose)  VERBOSE="--verbose" ;;
        --port)     shift; PORT="$1" ;;
        --port=*)   PORT="${arg#*=}" ;;
    esac
done

QEMU_PID=""

cleanup() {
    echo ""
    echo "[AURORA] Shutting down..."
    [ -n "$QEMU_PID" ] && kill "$QEMU_PID" 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

# ── Build kernel ──────────────────────────────────────────────────────────────

if [ "$NO_QEMU" -eq 0 ]; then
    echo "[AURORA] Building kernel..."
    cd "$SCRIPT_DIR"
    cargo build --release 2>&1 | grep -E "(Compiling|Finished|error\[)" || true

    # Runner prints the image path; extract it
    RUNNER_OUT=$(cargo run --package aurora-acm-runner --release --quiet 2>/dev/null || true)
    if [ "$UEFI" -eq 1 ]; then
        IMG=$(echo "$RUNNER_OUT" | grep -oP "(?<=file=)[^ \\\\\n]+" | tail -1)
        QEMU_BIOS="-bios /usr/share/ovmf/OVMF.fd"
    else
        IMG=$(echo "$RUNNER_OUT" | grep -oP "(?<=file=)[^ \\\\\n]+" | head -1)
        QEMU_BIOS=""
    fi

    if [ -z "$IMG" ]; then
        echo "[AURORA] ERROR: kernel image not found.  Run 'cargo build' manually."
        exit 1
    fi
    echo "[AURORA] Kernel image: $IMG"

    # ── Launch QEMU ───────────────────────────────────────────────────────────
    echo "[AURORA] Launching QEMU (COM1 → TCP :$PORT)..."
    # shellcheck disable=SC2086
    qemu-system-x86_64 \
        $QEMU_BIOS \
        -drive format=raw,file="$IMG" \
        -serial tcp::${PORT},server,nowait \
        -display sdl \
        -m 64M \
        -no-reboot &
    QEMU_PID=$!
    echo "[AURORA] QEMU running (pid=$QEMU_PID)"

    # Brief pause so QEMU opens its TCP socket before the bridge tries to connect.
    sleep 1
fi

# ── Cognitive stack + bridge ──────────────────────────────────────────────────

cd "$AI_DIR"

if [ "$NO_AI" -eq 1 ]; then
    echo "[AURORA] QEMU-only mode.  Waiting for kernel..."
    wait "$QEMU_PID"
else
    BRIDGE_ARGS="--port $PORT $VERBOSE"
    [ "$NO_QEMU" -eq 1 ] && BRIDGE_ARGS="$BRIDGE_ARGS --no-qemu"
    echo "[AURORA] Starting cognitive stack + bridge..."
    python3 aurora_acm_bridge.py $BRIDGE_ARGS
fi

wait
