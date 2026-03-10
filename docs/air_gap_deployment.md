# Air-Gap Deployment Guide

This guide covers deploying DocReview360 in networks with no outbound internet access.

## Prerequisites

- Docker Engine 24+ or containerd runtime
- Helm 3.12+ (for Kubernetes deployments)
- Access to an internal container registry (e.g., Harbor, ECR, or Docker Registry)
- Python 3.12 wheel archive if building from source

---

## 1. Build and Export Container Image

On an internet-connected build host:

```bash
# Build the production image
docker build -t docreview360:0.1.2 .

# Export to archive
docker save docreview360:0.1.2 | gzip > docreview360-0.1.2.tar.gz

# Verify
sha256sum docreview360-0.1.2.tar.gz > docreview360-0.1.2.tar.gz.sha256
```

Transfer `docreview360-0.1.2.tar.gz` and its `.sha256` to the air-gapped network via approved media.

---

## 2. Load Image on Air-Gapped Host

```bash
# Verify integrity
sha256sum -c docreview360-0.1.2.tar.gz.sha256

# Load image
gunzip -c docreview360-0.1.2.tar.gz | docker load

# Tag and push to internal registry
docker tag docreview360:0.1.2 registry.internal.example.gov/docreview360/docreview360:0.1.2
docker push registry.internal.example.gov/docreview360/docreview360:0.1.2
```

---

## 3. Python Dependency Wheel Bundle

For deployments that build images inside the air-gap:

```bash
# On internet-connected host:
pip download -r requirements.txt -d wheels/ --platform manylinux2014_x86_64 --python-version 312 --only-binary=:all:
tar czf wheels.tar.gz wheels/

# On air-gapped host:
tar xzf wheels.tar.gz
pip install --no-index --find-links=./wheels docreview360[postgres]
```

---

## 4. Docker Compose Air-Gap Deployment

Update `docker-compose.prod.yml` to reference the internal registry:

```yaml
# docker-compose.airgap.yml
services:
  web:
    image: registry.internal.example.gov/docreview360/docreview360:0.1.2
  worker:
    image: registry.internal.example.gov/docreview360/docreview360:0.1.2
  beat:
    image: registry.internal.example.gov/docreview360/docreview360:0.1.2
  db:
    image: registry.internal.example.gov/mirror/postgres:16-alpine
  redis:
    image: registry.internal.example.gov/mirror/redis:7-alpine
  nginx:
    image: registry.internal.example.gov/mirror/nginx:1.27-alpine
```

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.airgap.yml up -d
```

---

## 5. Kubernetes / Helm Air-Gap Deployment

```bash
# Pull and save all required images
for img in \
  ghcr.io/eputnam77/docreview360:0.1.2 \
  postgres:16-alpine \
  redis:7-alpine \
  nginx:1.27-alpine; do
  docker pull $img
  docker save $img | gzip >> k8s-images.tar.gz
done

# Load on cluster nodes (repeat for each node)
gunzip -c k8s-images.tar.gz | docker load

# Update Helm values to point to internal registry
helm install docreview360 ./helm/docreview360 \
  --namespace docreview360 --create-namespace \
  -f values.airgap.yaml \
  --set image.repository=registry.internal.example.gov/docreview360/docreview360 \
  --set image.pullPolicy=Never
```

---

## 6. Environment Variables Required

| Variable | Description |
|---|---|
| `DOCREVIEW360_DATABASE_URL` | PostgreSQL connection string |
| `DOCREVIEW360_SECRET_KEY` | JWT signing secret (minimum 32 chars) |
| `DOCREVIEW360_REDIS_URL` | Redis connection string |
| `DOCREVIEW360_ENV` | Set to `production` |
| `DOCREVIEW360_SEED_DEMO_USERS` | Set to `0` in production |

---

## 7. Disable External Dependency Calls

In air-gapped environments, set the following to disable any remaining external calls:

```bash
DOCREVIEW360_OTEL_ENABLED=0            # disable OpenTelemetry OTLP export
DOCREVIEW360_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.internal:4317
FEDERAL_STYLE_VALIDATOR_URL=http://fsv.internal:8080
```

---

## 8. Ongoing Updates

1. Download new image + wheel bundle on an internet-connected host.
2. Verify SHA-256 checksums.
3. Transfer via approved media (encrypted USB, one-way data diode, etc.).
4. Reload image, update Helm/Compose version tag, and rolling-restart.
