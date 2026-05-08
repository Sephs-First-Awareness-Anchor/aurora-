
import sys, os, json, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aurora import boot_aurora, _run_live_response_turn

def run_test():
    print("Booting Aurora for constraint round test...")
    STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")
    try:
        systems = boot_aurora(state_dir=STATE_DIR, verbose=False)
        print("Boot OK. Starting exploration session.\n")
    except Exception as e:
        print(f"Boot failed: {e}")
        traceback.print_exc()
        return

    questions = [
        ("X (Existence)", "Hey. How are you doing right now?"),
        ("T (Time)",      "Do you have a sense of what has carried forward from the start of our talk?"),
        ("N (Purpose)",   "What does it cost you, in terms of focus, to process what I say?"),
        ("B (Meaning)",   "If you had to describe the boundary of your own mind, what would you say?"),
        ("A (Agency)",    "What does it mean to you to exist?")
    ]
    
    # Mode setup
    ExistenceMode = systems.get('ExistenceMode')
    mode = ExistenceMode.BOUNDED if ExistenceMode is not None else None

    for i, (axis, q) in enumerate(questions):
        print(f"\n[Axis: {axis}]")
        print(f"User: {q}")
        start = time.time()
        
        result = _run_live_response_turn(
            systems, q, mode,
            auto_search_enabled=True,
            session_id="test_round_session",
            turn_tick=i+1,
            record_exchange=True,
            update_interactive_state=False,
            track_evolutionary_trace=False,
            run_periodic_maintenance=False,
        )
        
        end = time.time()
        
        resp_A = result.get('resp_A')
        text = str(getattr(resp_A, 'content', '') or '').strip()
        src = result.get('src', '?')
        tone = getattr(resp_A, 'emotional_tone', '?')
        conf = round(float(getattr(resp_A, 'confidence', 0.0) or 0.0), 2)

        print(f"Aurora: {text}")
        print(f"(Elapsed: {end-start:.2f}s, Source: {src}, Tone: {tone}, Conf: {conf})")

if __name__ == "__main__":
    run_test()
