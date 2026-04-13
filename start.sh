#!/bin/bash

cd backend

echo "Starting backend FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "Waiting for backend..."
sleep 5

cd ..

echo "Starting frontend Streamlit..."
streamlit run frontend/app.py --server.port=8000 --server.address=0.0.0.0
