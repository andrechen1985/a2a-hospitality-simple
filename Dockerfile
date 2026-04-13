FROM python:3.11-slim-bookworm

WORKDIR /app

# 安裝後端依賴
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 安裝前端依賴
COPY frontend/requirements.txt ./frontend/requirements.txt
RUN pip install --no-cache-dir -r frontend/requirements.txt

# 複製所有程式碼與資料
COPY . .

# 暴露 Streamlit 端口
EXPOSE 8501

# 啟動 Streamlit 前端
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
