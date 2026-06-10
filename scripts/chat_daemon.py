#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_STATE_DIR = ROOT / "aurora_state"
_QUEUE_FILE = _STATE_DIR / "surface_turn_queue.json"
_RESULT_FILE = _STATE_DIR / "surface_turn_result.json"

def queue_turn(text: str) -> str:
    turn_id = f"cli_{int(time.time() * 1000)}"
    
    state = {"pending": []}
    if _QUEUE_FILE.exists():
        try:
            state = json.loads(_QUEUE_FILE.read_text())
        except:
            pass
            
    pending = state.get("pending", [])
    pending.append({
        "id": turn_id,
        "content": text,
        "source": "cli_bridge",
        "status": "queued",
        "created_at": time.time(),
        "auto_search_enabled": True,
        "record_exchange": True,
        "mode_name": "BOUNDED",
    })
    state["pending"] = pending
    
    _QUEUE_FILE.write_text(json.dumps(state, indent=2))
    return turn_id

def wait_for_result(turn_id: str, timeout: int = 60):
    start = time.time()
    while time.time() - start < timeout:
        if _RESULT_FILE.exists():
            try:
                results = json.loads(_RESULT_FILE.read_text())
                if results.get("id") == turn_id:
                    return results
            except:
                pass
        time.sleep(0.5)
    return None

def main():
    print("--- Aurora CLI Daemon Bridge ---")
    print("Type /exit to quit.")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "/exit":
                break
                
            turn_id = queue_turn(user_input)
            print("  (sent to daemon...)")
            
            result = wait_for_result(turn_id)
            if result:
                if result.get("status") == "error":
                    print(f"\nAurora [ERROR]: {result.get('error')}")
                else:
                    resp_a = result.get("resp_A", {})
                    content = resp_a.get("content", "...")
                    tone = resp_a.get("emotional_tone", "neutral")
                    print(f"\nAurora [{tone}]: {content}")
            else:
                print("\n  [TIMEOUT] Daemon did not respond in time.")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
