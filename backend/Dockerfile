# Outreach Copilot API — Cloud Run image. Secrets come from Secret Manager as env vars at runtime, never baked in.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080 \
    APP_ENV=prod CACHE_DIR=/tmp/cache DATA_DIR=/tmp/data
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
RUN useradd --create-home --uid 10001 appuser
USER appuser
# One worker: RunManager keeps in-flight run state in this process (Cloud Run max-instances=1).
CMD ["sh", "-c", "exec uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers"]
