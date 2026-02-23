# ── Stage 1: deps ──────────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /app

# System libs needed by PaddleOCR / OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ───────────────────────────────────────────────────────────
FROM python:3.10-slim

WORKDIR /app

# Copy only the installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Runtime system libs (smaller set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy application source
COPY . .

EXPOSE 8000

# Render sets PORT env var; fall back to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
