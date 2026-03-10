# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Stage 1: build frontend
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: install Python runtime dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS python-deps

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir ".[ml]" uvicorn

# ---------------------------------------------------------------------------
# Stage 3: runtime image — non-root user, minimal surface
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ARG VERSION=0.1.2
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
ARG IMAGE_SOURCE=https://github.com/eputnam77/DocReview360
ARG IMAGE_URL=https://github.com/eputnam77/DocReview360

LABEL org.opencontainers.image.title="DocReview360" \
      org.opencontainers.image.description="DocReview360 document workflow and approval platform" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="${IMAGE_SOURCE}" \
      org.opencontainers.image.url="${IMAGE_URL}" \
      org.opencontainers.image.licenses="MIT"

# Create non-root user and writable data directory
RUN groupadd --gid 1001 docreview && \
    useradd --uid 1001 --gid 1001 --no-create-home --shell /bin/false docreview && \
    mkdir -p /app/data && \
    chown -R docreview:docreview /app

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

ARG PORT=8000
ENV PORT=${PORT}

# Copy installed packages and uvicorn binary from python-deps stage
COPY --from=python-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-deps /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application source
COPY --chown=docreview:docreview src ./src

# Copy compiled frontend assets from frontend-builder stage
COPY --from=frontend-builder --chown=docreview:docreview /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder --chown=docreview:docreview /app/frontend/public ./frontend/public

USER docreview

EXPOSE ${PORT}

# Lightweight liveness probe: hits /health/live without extra tools
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health/live')" || exit 1

CMD ["sh", "-c", "uvicorn docreview360.api:app --host 0.0.0.0 --port ${PORT} --workers 1"]
