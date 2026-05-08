import os
import json
from flask import Flask, request, jsonify
from google.cloud import secretmanager, aiplatform
import psycopg2

app = Flask(__name__)

# Config from environment variables
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
LOCATION = os.environ.get('REGION', 'us-central1')
ENDPOINT_ID = os.environ.get('VERTEX_AI_ENDPOINT_ID')

# Initialize clients
secret_manager_client = secretmanager.SecretManagerServiceClient()
aiplatform.init(project=PROJECT_ID, location=LOCATION)

def get_db_connection():
    """Establish a connection to Cloud SQL."""
    # Assuming secret manager holds the DB password
    # This is a placeholder for actual secret retrieval and connection logic
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASS')
        )
        return conn
    except Exception as e:
        print(f"[DB] Error: {e}")
        return None

@app.route('/ask', methods=['POST'])
def ask_aurora():
    """External API endpoint to interact with Aurora."""
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing prompt"}), 400
    
    prompt = data['prompt']
    
    # 1. (Optional) Log the request to Cloud SQL
    # conn = get_db_connection()
    # ...
    
    # 2. Call Aurora's Vertex AI Endpoint
    try:
        endpoint = aiplatform.Endpoint(ENDPOINT_ID)
        prediction = endpoint.predict(instances=[{"text": prompt}])
        
        # Vertex AI returns a list of results
        aurora_response = prediction.predictions[0]
        
        return jsonify({
            "status": "success",
            "aurora_said": aurora_response.get("response", ""),
            "metadata": {
                "tone": aurora_response.get("tone", "neutral"),
                "confidence": aurora_response.get("confidence", 0.0)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({"service": "aurora-api-gateway", "status": "online"}), 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
