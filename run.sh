#!/bin/bash
set -e
pip install -r requirements.txt
echo "== MDM Orchestrator LLM-centric =="
echo "APP_PORT=${APP_PORT:-8001} LOG_LEVEL=${LOG_LEVEL:-INFO}"
echo "OLLAMA_ENDPOINTS=${OLLAMA_ENDPOINTS:-http://localhost:11434}"
echo "NUM_GPU=${NUM_GPU:-22} NUM_BATCH=${NUM_BATCH:-512} NUM_CTX=${NUM_CTX:-4096} NUM_THREAD=${NUM_THREAD:-16}"
echo "CONCURRENCY_NORMALIZE=${CONCURRENCY_NORMALIZE:-8} CONCURRENCY_ADDRESS=${CONCURRENCY_ADDRESS:-8}"
export PYTHONPATH=$(pwd)
uvicorn app:app --host 0.0.0.0 --port "${APP_PORT:-8001}" --workers 1
