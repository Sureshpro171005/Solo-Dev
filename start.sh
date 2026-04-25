#!/bin/bash
# start.sh — Launch backend + frontend concurrently

echo "Starting FastAPI backend on :8000 …"
uvicorn backend:app --host 0.0.0.0 --port 8000 --workers 1 &

echo "Starting Streamlit frontend on :8501 …"
streamlit run frontend.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false

wait