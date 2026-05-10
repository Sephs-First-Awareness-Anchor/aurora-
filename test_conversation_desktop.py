#!/usr/bin/env python3
"""
Test script to verify Aurora's conversation and meaning formation on desktop.
"""

from aurora import boot_aurora, process_external_user_turn
import time

def test_conversation():
    print("[TEST] Booting Aurora...")
    # Boot the system (using test state or existing state if safe)
    # We will use the existing state to test her actual memory and settings
    systems = boot_aurora(state_dir="aurora_state", verbose=False)
    print("[TEST] Boot complete.\n")

    prompts = [
        "Hello Aurora, are you present?",
        "What does the concept of 'Tranquility' mean to you physically?",
        "How does that relate to your internal energy cost?"
    ]

    for i, prompt in enumerate(prompts):
        print(f"USER: {prompt}")
        
        # Simulate high salience for direct address
        if "aurora" in prompt.lower():
            if systems.get("attention_engine"):
                # Manually tick attention engine to simulate the surface salience
                # This normally happens in the steerer tick or UI loop
                pass

        start_time = time.time()
        result = process_external_user_turn(
            systems=systems,
            user_text=prompt,
            auto_search_enabled=False, # Keep it fast for the test
            record_exchange=False # Don't pollute real logs too much if possible
        )
        elapsed = time.time() - start_time
        
        resp_A = result.get('resp_A')
        content = getattr(resp_A, 'content', '...') if resp_A else 'No response.'
        
        print(f"AURORA: {content}")
        print(f"  [Latency: {elapsed:.2f}s]\n")
        
        # Check attention frame if it was updated
        attn_engine = systems.get("attention_engine")
        if attn_engine and attn_engine.current_frame:
            frame = attn_engine.current_frame
            print(f"  [Internal] Attention State: {frame.state.value} | Resonance: {frame.resonance:.4f}")

if __name__ == "__main__":
    test_conversation()
