#!/bin/bash

cd backend

echo "Starting backend FastAPI on port 8001..."
uvicorn main:app --host 127.0.0.1 --port 8001 &

echo "Waiting for backend..."
sleep 5

cd ..

echo "Starting frontend Streamlit on port 8000..."
streamlit run frontend/app.py --server.port=8000 --server.address=0.0.0.0
