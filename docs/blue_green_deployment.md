# Blue-Green and Rolling Deployment Guide

This guide covers zero-downtime deployment strategies for DocReview360.

---

## Blue-Green Deployment (Docker Compose)

Blue-green runs two identical production stacks ("blue" and "green"). Traffic is switched at the load balancer after the new stack passes health checks.

### Step 1 — Deploy Green (new version)

```bash
# Set target version
export APP_VERSION=0.1.3

# Start green stack on alternate ports
APP_VERSION=$APP_VERSION docker compose \
  -f docker-compose.prod.yml \
  -p docreview360-green \
  up -d --no-deps web worker beat
```

### Step 2 — Run Health Checks

```bash
# Wait for green to become ready
until curl -sf http://localhost:8001/health/ready; do
  echo "Waiting for green..."
  sleep 5
done
echo "Green is ready"
```

### Step 3 — Switch Traffic (nginx)

Update upstream in nginx.conf to point to the green stack:

```nginx
upstream docreview360_api {
    server 127.0.0.1:8001;  # green
    # server 127.0.0.1:8000;  # blue (disabled)
}
```

```bash
nginx -s reload
```

### Step 4 — Verify and Retire Blue

```bash
# Smoke test through nginx
curl -sf https://docreview360.example.gov/health/ready

# Retire blue stack
docker compose -f docker-compose.prod.yml -p docreview360-blue down
```

### Rollback (if green fails health checks)

```bash
# Revert nginx upstream to blue, then:
nginx -s reload

# Stop green
docker compose -f docker-compose.prod.yml -p docreview360-green down
```

---

## Rolling Deployment (Kubernetes)

Kubernetes Deployments support rolling updates natively.

### Configure Rolling Strategy

```yaml
# In k8s/deployment.yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0     # never reduce capacity
      maxSurge: 1           # add one extra pod during update
```

### Perform a Rolling Update

```bash
# Update image tag
kubectl set image deployment/docreview360 \
  docreview360=ghcr.io/eputnam77/docreview360:0.1.3 \
  -n docreview360

# Watch rollout
kubectl rollout status deployment/docreview360 -n docreview360 --timeout=5m
```

### Monitor Progress

```bash
kubectl get pods -n docreview360 -w
kubectl describe deployment docreview360 -n docreview360
```

### Rollback

```bash
# Roll back to previous revision
kubectl rollout undo deployment/docreview360 -n docreview360

# Roll back to specific revision
kubectl rollout undo deployment/docreview360 -n docreview360 --to-revision=3

# View history
kubectl rollout history deployment/docreview360 -n docreview360
```

---

## Helm Rolling Upgrade

```bash
# Upgrade (performs rolling update automatically)
helm upgrade docreview360 ./helm/docreview360 \
  --namespace docreview360 \
  --set image.tag=0.1.3 \
  --wait --timeout 5m

# Rollback
helm rollback docreview360 -n docreview360
```

---

## Database Migration Safety

Before any deployment that includes schema changes:

1. **Export backup**: `BACKUP_PASSPHRASE=<secret> ./scripts/db_backup.sh`
2. **Run Alembic migration** (if applicable): `alembic upgrade head`
3. **Verify health**: `curl https://docreview360.example.gov/health/ready`

For backwards-incompatible schema changes, use expand-contract migration:
- **Expand**: Add new columns/tables (backward-compatible). Deploy new app.
- **Contract**: Remove old columns once all instances are running new code.
