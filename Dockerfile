FROM python:3.12-slim

ARG UNSIGNED_TEST=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

LABEL org.opencontainers.image.title="SecureTask" \
      org.opencontainers.image.description="Secure task management application" \
      org.opencontainers.image.security-test="${UNSIGNED_TEST}"

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 appgroup \
    && useradd --system --uid 10001 --gid 10001 --create-home appuser \
    && mkdir -p /data \
    && chown -R 10001:10001 /data

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN chown -R 10001:10001 /app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]