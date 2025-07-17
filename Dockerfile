# syntax=docker/dockerfile:1
FROM python:3.12-slim

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
