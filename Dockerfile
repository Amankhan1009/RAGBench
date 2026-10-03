# Multi-stage production Dockerfile for RAGBench Backend
FROM python:3.13-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.13-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app/src

COPY --from=builder /root/.local /root/.local
COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

EXPOSE 8000

CMD ["uvicorn", "ragbench.main:app", "--host", "0.0.0.0", "--port", "8000"]