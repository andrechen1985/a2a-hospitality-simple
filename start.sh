#!/bin/bash

# 啟動後端 FastAPI（背景執行）
uvicorn main:app --host 0.0.0.0 --port 8000 &

# 等待後端啟動
sleep 5

# 啟動前端 Streamlit
streamlit run frontend/app.py --server.port=8501 --server.address=0.0.0.0
