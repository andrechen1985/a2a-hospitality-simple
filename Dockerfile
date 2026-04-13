FROM python:3.11-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY frontend/requirements.txt ./frontend/requirements.txt
RUN pip install --no-cache-dir -r frontend/requirements.txt
COPY . .
COPY start.sh /start.sh
RUN chmod +x /start.sh
ENV PORT=8000
EXPOSE 8000
CMD ["/start.sh"]
