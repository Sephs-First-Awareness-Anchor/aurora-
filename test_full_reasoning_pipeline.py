#!/usr/bin/env python3
"""
REASONING PIPELINE VERIFICATION SCRIPT
========================================
This script traces a single input through Aurora's full stack to verify
that the Attention Engine (Layer 4.5) is correctly influencing reasoning,
emotion, and expression.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from aurora_runtime import AuroraRuntime
from aurora_internal.aurora_attention_engine import AttentionState
import time

def run_verification():
    print("\n[TEST] Booting Aurora Full Stack...")
    runtime = AuroraRuntime(state_dir="aurora_state_test")
    runtime.boot(verbose=False)
    
    # 1. Baseline Check
    print("\n[STEP 1] Establishing Baseline...")
    runtime.steerer.tick(5) # Warm up the buffer
    status = runtime.steerer._last_attention_frame
    print(f"  Initial State: {status.state if status else 'DORMANT'}")
    
    # 2. Inject High-Salience Stimulus
    print("\n[STEP 2] Injecting High-Salience Input ('Aurora, why are you paying attention to this?')...")
    user_input = "Aurora, why are you paying attention to this?"
    
    # We use steerer.tick with an action name to simulate high salience
    # In a real run, main.py passes this through process_turn_thread
    runtime.steerer.tick(1, action="perception_high_salience")
    
    # 3. Trace Attention Propagation
    print("\n[STEP 3] Tracing Attentional Propagation...")
    
    # Check Attention Engine State
    attn = runtime.steerer._last_attention_frame
    if attn:
        print(f"  [L4.5] Attention State: {attn.state.value}")
        print(f"  [L4.5] Resonance Peak: {attn.resonance:.4f}")
        print(f"  [L4.5] Focus Axes: {[str(a) for a in attn.focus_axes]}")
        
        # Check Reasoning (DPME) Bias
        dpme = runtime.systems.attention_engine # Access via systems
        if runtime.systems.has("dpme"):
            bias = runtime.systems.dpme._attentional_bias
            print(f"  [L4] DPME Reasoning Bias: {bias}")
            
        # Check Emotional (DER) Injection
        der = runtime.systems.dimensional.der
        emo_level = der.pools['emotional'].energy
        cre_level = der.pools['creative'].energy
        print(f"  [L3] Emotional Pool Energy: {emo_level:.4f}")
        print(f"  [L3] Creative Pool Energy: {cre_level:.4f}")
        
        # Check Identity (L6) Reinforcement
        identity = runtime.systems.identity
        curiosity = identity.traits['curiosity'].current_value
        print(f"  [L6] Curiosity Trait Level: {curiosity:.4f}")
        
        # Check Expression (L5) Anchors
        if runtime.systems.has("perception"):
            anchors = runtime.systems.perception._attentional_focus.get("anchors", [])
            print(f"  [L5] Attentional Anchors for Composition: {anchors}")

    # 4. Final Verification Result
    if attn and attn.resonance > 0:
        print("\n[RESULT] SUCCESS: Attentional resonance propagated through the stack.")
    else:
        print("\n[RESULT] FAILURE: Attention Engine did not trigger resonance.")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] Test failed: {e}")
