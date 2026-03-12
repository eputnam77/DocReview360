#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deployment drift checker.

Compares Dockerfile, docker-compose*.yml, Helm values, Kubernetes manifests,
and docs/deployment.md for inconsistent ports, env vars, health checks, and
image tags.

Exit code is always 0 (informational only).

Usage:
    python scripts/check-deployment-drift.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKER_COMPOSE = REPO_ROOT / "docker-compose.yml"
DOCKER_COMPOSE_PROD = REPO_ROOT / "docker-compose.prod.yml"
DEPLOYMENT_DOCS = REPO_ROOT / "docs" / "deployment.md"
HELM_VALUES = REPO_ROOT / "helm" / "docreview360" / "values.yaml"
K8S_DIR = REPO_ROOT / "k8s"

findings: list[str] = []


def note(msg: str) -> None:
    findings.append(msg)
    print(f"  DRIFT: {msg}")


def ok(msg: str) -> None:
    print(f"  ok   : {msg}")


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# 1. Port consistency
# ---------------------------------------------------------------------------

def check_ports() -> None:
    section("Port consistency")

    # Expected ports
    BACKEND_PORT = "8000"
    FRONTEND_PORT = "3000"

    for label, path in [
        ("Dockerfile", DOCKERFILE),
        ("docker-compose.yml", DOCKER_COMPOSE),
        ("docker-compose.prod.yml", DOCKER_COMPOSE_PROD),
        ("docs/deployment.md", DEPLOYMENT_DOCS),
    ]:
        text = read_text(path)
        if not text:
            print(f"  skip : {label} not found")
            continue
        if BACKEND_PORT in text:
            ok(f"{label} references backend port {BACKEND_PORT}")
        else:
            note(f"{label} does not reference backend port {BACKEND_PORT}")
        if path == DOCKER_COMPOSE or path == DOCKER_COMPOSE_PROD:
            if FRONTEND_PORT in text:
                ok(f"{label} references frontend port {FRONTEND_PORT}")

    # Check Helm chart
    helm_text = read_text(HELM_VALUES)
    if helm_text:
        if BACKEND_PORT in helm_text:
            ok(f"Helm values.yaml references backend port {BACKEND_PORT}")
        else:
            note(f"Helm values.yaml does not reference backend port {BACKEND_PORT}")


# ---------------------------------------------------------------------------
# 2. Health check consistency
# ---------------------------------------------------------------------------

def check_healthchecks() -> None:
    section("Health check endpoints")

    HEALTH_ENDPOINT = "/health"

    for label, path in [
        ("Dockerfile", DOCKERFILE),
        ("docker-compose.prod.yml", DOCKER_COMPOSE_PROD),
        ("docs/deployment.md", DEPLOYMENT_DOCS),
    ]:
        text = read_text(path)
        if not text:
            print(f"  skip : {label} not found")
            continue
        if HEALTH_ENDPOINT in text:
            ok(f"{label} references health check endpoint")
        else:
            note(f"{label} does not reference health endpoint — HEALTHCHECK may be missing")

    # Check K8s manifests
    if K8S_DIR.exists():
        for manifest in K8S_DIR.glob("*.yaml"):
            text = manifest.read_text(encoding="utf-8", errors="replace")
            if "liveness" in text or "readiness" in text:
                ok(f"k8s/{manifest.name} has liveness/readiness probes")
                break
        else:
            note("No K8s manifest found with liveness/readiness probes")


# ---------------------------------------------------------------------------
# 3. Environment variable consistency
# ---------------------------------------------------------------------------

def check_env_vars() -> None:
    section("Critical environment variables")

    CRITICAL_ENV_VARS = [
        "DOCREVIEW360_ENV",
        "DOCREVIEW360_SECRET_KEY",
        "DATABASE_URL",
    ]

    env_example = REPO_ROOT / ".env.example"
    env_text = read_text(env_example)
    deployment_text = read_text(DEPLOYMENT_DOCS)
    compose_text = read_text(DOCKER_COMPOSE) + read_text(DOCKER_COMPOSE_PROD)

    for var in CRITICAL_ENV_VARS:
        sources = []
        if var in env_text:
            sources.append(".env.example")
        if var in deployment_text:
            sources.append("deployment.md")
        if var in compose_text:
            sources.append("docker-compose")

        if sources:
            ok(f"{var} documented in: {', '.join(sources)}")
        else:
            note(f"{var} not found in .env.example, deployment.md, or docker-compose files")


# ---------------------------------------------------------------------------
# 4. Image tag consistency
# ---------------------------------------------------------------------------

def check_image_tags() -> None:
    section("Image tag consistency")

    compose_text = read_text(DOCKER_COMPOSE_PROD) or read_text(DOCKER_COMPOSE)
    helm_text = read_text(HELM_VALUES)

    # Check for 'latest' tag (discouraged in prod)
    if ":latest" in compose_text:
        note("docker-compose uses ':latest' image tag — pin to a specific version for prod")
    else:
        ok("docker-compose does not use ':latest' tag")

    if helm_text and ":latest" in helm_text:
        note("Helm values.yaml uses ':latest' tag — pin to a specific version for prod")
    elif helm_text:
        ok("Helm values.yaml does not use ':latest' tag")


# ---------------------------------------------------------------------------
# 5. Non-root user in Dockerfile
# ---------------------------------------------------------------------------

def check_dockerfile_security() -> None:
    section("Dockerfile security posture")

    text = read_text(DOCKERFILE)
    if not text:
        print("  skip : Dockerfile not found")
        return

    if "USER" in text and ("docreview" in text or "1001" in text):
        ok("Dockerfile uses a non-root USER")
    else:
        note("Dockerfile may run as root — add USER directive for production security")

    if "HEALTHCHECK" in text:
        ok("Dockerfile defines a HEALTHCHECK")
    else:
        note("Dockerfile has no HEALTHCHECK directive")

    if "COPY --chown" in text or "--chown" in text:
        ok("Dockerfile uses --chown on COPY")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("DocReview360 Deployment Drift Checker")
    print(f"Repo root: {REPO_ROOT}")

    check_ports()
    check_healthchecks()
    check_env_vars()
    check_image_tags()
    check_dockerfile_security()

    print(f"\n{'='*60}")
    if findings:
        print(f"SUMMARY: {len(findings)} drift finding(s) detected.")
        for i, f in enumerate(findings, 1):
            print(f"  {i}. {f}")
    else:
        print("SUMMARY: No deployment drift detected.")
    print("=" * 60)

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
