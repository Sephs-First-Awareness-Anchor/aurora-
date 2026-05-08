#!/data/data/com.termux/files/usr/bin/sh
set -eu

cd /storage/emulated/0/aurora_strata

MODEL="${AURORA_LOCAL_LLM_MODEL:-Models/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
HOST="${AURORA_LOCAL_LLM_HOST:-127.0.0.1}"
PORT="${AURORA_LOCAL_LLM_PORT:-8080}"
CTX="${AURORA_LOCAL_LLM_CTX:-512}"
THREADS="${AURORA_LOCAL_LLM_THREADS:-1}"

exec llama-server \
  -m "$MODEL" \
  --host "$HOST" \
  --port "$PORT" \
  -c "$CTX" \
  -t "$THREADS" \
  -np 1 \
  -to 600
