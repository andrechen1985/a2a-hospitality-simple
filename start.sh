#!/bin/bash

cd backend

echo "Starting backend FastAPI on port 8001..."
# 取消 PORT 環境變數，避免 uvicorn 讀取並覆蓋
( unset PORT && uvicorn main:app --host 127.0.0.1 --port 8001 ) &

echo "Waiting for backend..."
sleep 5

cd ..

echo "Starting frontend Streamlit on port ${PORT:-8000}..."
# Streamlit 使用 Render 分配的端口（預設 8000）
streamlit run frontend/app.py --server.port=${PORT:-8000} --server.address=0.0.0.0
