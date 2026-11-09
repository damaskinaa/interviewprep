FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Keep 1 worker: without REDIS_URL jobs run as in-process threads, and a restarted worker's
# startup sweep (fail_stale_jobs) would fail jobs still running in a sibling worker.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
