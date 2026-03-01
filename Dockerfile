# syntax=docker/dockerfile:1
FROM python:3.12-slim

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
      org.opencontainers.image.licenses="GPL-3.0-only"
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

ARG PORT=8000
ENV PORT=${PORT}

# Install runtime dependencies
COPY pyproject.toml ./
COPY poetry.lock ./
COPY src ./src
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip && \
    pip install . && \
    pip install uvicorn && \
    npm ci --prefix frontend && npm run build --prefix frontend

# Copy the rest of the source
COPY . .
EXPOSE ${PORT}
CMD ["sh", "-c", "uvicorn docreview360.api:app --host 0.0.0.0 --port ${PORT}"]

