FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY worker ./worker
RUN pip install --no-cache-dir .

# SIGTERM triggers graceful shutdown in worker/main.py
CMD ["python", "-m", "worker.main"]
