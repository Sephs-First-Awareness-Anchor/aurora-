import os
import json
import time
import subprocess
from pathlib import Path

# Configuration
BASE_DIR = Path("/storage/emulated/0/aurora_strata/aurora--main/aurora--main")
STATE_DIR = BASE_DIR / "aurora_state"
TRIGGER_FILE = STATE_DIR / "voice_trigger.json"
RECORDING_PATH = "/data/data/com.termux/files/usr/tmp/aurora_mic_capture.wav"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] [BRIDGE] {msg}", flush=True)

def run_bridge():
    if not STATE_DIR.exists():
        STATE_DIR.mkdir(parents=True, exist_ok=True)
    
    log("Termux Voice Bridge (Python) Started.")
    log(f"Watching {TRIGGER_FILE}")

    while True:
        try:
            if TRIGGER_FILE.exists():
                with open(TRIGGER_FILE, 'r') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}
                
                if data.get("trigger") is True:
                    log("Trigger detected! Preparing to record...")
                    
                    # 1. Reset trigger immediately to avoid loops
                    with open(TRIGGER_FILE, 'w') as f:
                        json.dump({"trigger": False, "state": "recording"}, f)
                    
                    # 2. Clear old recording
                    if os.path.exists(RECORDING_PATH):
                        os.remove(RECORDING_PATH)
                    
                    # 3. Start recording via Termux:API
                    # We'll record for 8 seconds (good balance)
                    log("Recording started (8 seconds)...")
                    subprocess.run(["termux-microphone-record", "-f", RECORDING_PATH, "-l", "8"], check=True)
                    
                    if os.path.exists(RECORDING_PATH) and os.path.getsize(RECORDING_PATH) > 0:
                        log("Recording finished successfully.")
                        # 4. Notify Aurora that audio is ready
                        with open(TRIGGER_FILE, 'w') as f:
                            json.dump({
                                "trigger": False,
                                "state": "captured",
                                "path": RECORDING_PATH,
                                "timestamp": time.time()
                            }, f)
                        log("Sent captured audio to Aurora.")
                    else:
                        log("Recording failed or file is empty.")
                        with open(TRIGGER_FILE, 'w') as f:
                            json.dump({"trigger": False, "state": "failed"}, f)

        except Exception as e:
            log(f"Error in bridge loop: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    run_bridge()
