# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install runtime dependencies
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip && \
    pip install . && \
    pip install uvicorn

# Copy the rest of the source
COPY . .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "docuflow.api:app", "--host", "0.0.0.0", "--port", "8000"]
