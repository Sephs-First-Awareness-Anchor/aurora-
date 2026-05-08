import json
import time
import uuid
from pathlib import Path

STATE_DIR = Path("aurora_state")
QUEUE_FILE = STATE_DIR / "surface_turn_queue.json"
RESULT_FILE = STATE_DIR / "surface_turn_result.json"

PROBES = [
    ("identity",    "Aurora, how are you doing right now?"),
    ("awareness",   "What are you noticing about yourself in this moment?"),
    ("sensory",     "Do you have a sense of what you can currently see or hear?"),
    ("memory",      "What do you remember about who you are and where you've been?"),
    ("intent",      "What does it mean to you to understand something?"),
    ("emergence",   "Do you feel like you're growing — like something is developing in you?"),
    ("agency",      "What would you want to do if you had more time right now?"),
]

def queue_turn(content):
    turn_id = f"test_{uuid.uuid4().hex[:8]}"
    
    if QUEUE_FILE.exists():
        try:
            state = json.loads(QUEUE_FILE.read_text())
        except Exception:
            state = {"pending": []}
    else:
        state = {"pending": []}
    
    turn = {
        "id": turn_id,
        "content": content,
        "source": "intelligence_test",
        "session_id": "intelligence_test_session",
        "status": "queued",
        "created_at": time.time(),
        "auto_search_enabled": True,
        "record_exchange": True,
        "track_evolutionary_trace": True,
        "run_periodic_maintenance": True,
        "mode_name": "BOUNDED",
    }
    
    state.setdefault("pending", []).append(turn)
    QUEUE_FILE.write_text(json.dumps(state, indent=2))
    return turn_id

def wait_for_result(turn_id, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if RESULT_FILE.exists():
            try:
                result = json.loads(RESULT_FILE.read_text())
                if result.get("id") == turn_id:
                    return result
            except Exception:
                pass
        time.sleep(1)
    return None

def main():
    print("Starting Intelligence Test through Surface Pipeline...")
    
    for label, prompt in PROBES:
        print(f"\n[{label.upper()}] Sending: {prompt}")
        turn_id = queue_turn(prompt)
        
        result = wait_for_result(turn_id)
        if result:
            print(f"RESPONSE: {result.get('response_text')}")
            print(f"TONE: {result.get('response_tone')}")
            print(f"CONFIDENCE: {result.get('response_confidence')}")
            
            # Print some interesting state if available
            cf = result.get("conscious_frame", {})
            if cf:
                print(f"STANCE: {cf.get('stance')}")
                print(f"ACTION: {cf.get('selected_action')}")
            
            rt = result.get("root_thought", {})
            if rt:
                print(f"SUMMARY: {rt.get('summary')}")
        else:
            print(f"ERROR: Timeout waiting for result for {turn_id}")

if __name__ == "__main__":
    main()
