#!/bin/bash
echo "=== V.E.C.T.O.R. PRODUCT LAUNCH SEQUENCE ==="

# 1. Kill any existing instances
pkill -f "vector.service.api"
pkill -f "production_ingest.py"

# 2. Set Environment
export VECTOR_API_KEYS="vector-prod-primary-key"
export VECTOR_DATA_DIR="/home/king2morningstr/aurora/AuroraO/aurora_strata/vector_data"
mkdir -p $VECTOR_DATA_DIR

# 3. Start the API Service
echo "[*] Starting V.E.C.T.O.R. API on port 8080..."
cd /home/king2morningstr/.gemini/tmp/aurora-strata/vector_api_eval
source venv/bin/activate
nohup python3 -m vector.service.api > vector_api.log 2>&1 &

# 4. Start the Production Ingestor (Background)
echo "[*] Activating Real-World Intelligence Ingestor..."
source venv/bin/activate
nohup python3 -m vector.production_ingest > vector_ingest.log 2>&1 &

echo "[!] PRODUCT IS LIVE."
echo "    API Key: vector-prod-primary-key"
echo "    Endpoint: http://localhost:8080"
echo "    Logs: vector_api.log, vector_ingest.log"
