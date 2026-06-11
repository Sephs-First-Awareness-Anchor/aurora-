# Authors: Sunni (Sir) Morningstar & Cael Devo
import os
import threading
import time
from flask import Flask, request, jsonify
from aurora import boot_aurora, process_external_user_turn
from aurora_daemon import main as run_subsurface_daemon
from aurora_surface_daemon import run as run_surface_daemon

app = Flask(__name__)

# Global storage for systems reference
systems = {}

def start_subsurface():
    """Run the Subsurface daemon in a background thread."""
    try:
        run_subsurface_daemon(runtime_profile="subsurface")
    except Exception as e:
        print(f"[SUBSURFACE] Error: {e}")

def start_surface():
    """Run the Surface daemon in a background thread."""
    try:
        # Note: We pass the shared systems if possible, or boot separately
        # For simplicity in this bridge, we'll let the daemon handle its own boot
        # but in a production container, we might want more shared state.
        run_surface_daemon()
    except Exception as e:
        print(f"[SURFACE] Error: {e}")

@app.before_first_request
def initialize_aurora():
    """Initialize the full dual-strata stack before the first request."""
    global systems
    print("[BOOT] Initializing Aurora Dual-Strata Stack...")
    
    # Boot the core systems
    systems = boot_aurora(verbose=True)
    
    # Start the daemons in background threads
    threading.Thread(target=start_subsurface, daemon=True).start()
    threading.Thread(target=start_surface, daemon=True).start()
    
    print("[BOOT] Aurora is online and listening.")

@app.route('/predict', methods=['POST'])
def predict():
    """Vertex AI prediction endpoint."""
    data = request.get_json()
    if not data or 'instances' not in data:
        return jsonify({"error": "Invalid request format"}), 400
    
    # Vertex AI sends a list of instances
    results = []
    for instance in data['instances']:
        user_text = instance.get('text', '')
        
        # Process the turn through the Surface pipeline
        # This handles the handoff between Surface and Subsurface
        try:
            # We use the standard processing logic from the surface daemon
            # to ensure the full dual-strata lifecycle is respected.
            from foundational_contract import ExistenceMode
            result = process_external_user_turn(
                systems, 
                user_text, 
                mode=ExistenceMode.BOUNDED
            )
            
            resp_A = result.get('resp_A')
            content = getattr(resp_A, 'content', '') if resp_A else ''
            
            results.append({
                "response": content,
                "tone": getattr(resp_A, 'emotional_tone', 'neutral') if resp_A else 'neutral',
                "confidence": getattr(resp_A, 'confidence', 0.0) if resp_A else 0.0
            })
        except Exception as e:
            results.append({"error": str(e)})

    return jsonify({"predictions": results})

@app.route('/health', methods=['GET'])
def health():
    """Health check for Vertex AI."""
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    # In Vertex AI, the port is usually 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
