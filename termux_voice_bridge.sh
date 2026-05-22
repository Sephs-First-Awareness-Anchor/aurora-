#!/usr/bin/env bash
STATE_DIR="aurora_state"
TRIGGER_FILE="$STATE_DIR/voice_trigger.json"
RECORDING_PATH="/data/data/com.termux/files/usr/tmp/aurora_mic_capture.wav"
mkdir -p "$STATE_DIR"
while true; do
    if [[ -f "$TRIGGER_FILE" ]]; then
        TRIGGER=$(jq -r '.trigger' "$TRIGGER_FILE" 2>/dev/null)
        if [[ "$TRIGGER" == "true" ]]; then
            echo "[BRIDGE] Trigger detected. Starting Termux recording..."
            rm -f "$RECORDING_PATH"
            termux-microphone-record -f "$RECORDING_PATH" -l 10
            echo "[BRIDGE] Recording finished."
            TIMESTAMP=$(date +%s)
            echo "{"trigger": false, "state": "captured", "path": "$RECORDING_PATH", "timestamp": $TIMESTAMP}" > "$TRIGGER_FILE"
        fi
    fi
    sleep 0.5
done
