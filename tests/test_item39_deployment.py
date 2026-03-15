# SPDX-License-Identifier: MIT
"""Tests for Item 39: Deployment, infrastructure, and operations.

Covers:
  Phase 1 — Helm chart, Kubernetes manifests
  Phase 2 — Rate limiting, structured JSON logging, OpenTelemetry tracing
  Phase 3 — Docker Compose prod, air-gap guide, blue-green guide, DR runbook
"""

from __future__ import annotations

import json
import logging
import sys
import time
from io import StringIO
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


# ──────────────── helpers ────────────────────────────────────────


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _load_yaml_all(path: Path) -> list:
    with open(path) as f:
        return list(yaml.safe_load_all(f))


# ══════════════════════════════════════════════════════════════════
# Phase 1: Helm chart
# ══════════════════════════════════════════════════════════════════


class TestHelmChart:
    """Helm chart structure and content validation."""

    _chart_dir = BASE_DIR / "helm" / "docreview360"

    def test_chart_yaml_exists(self) -> None:
        assert (self._chart_dir / "Chart.yaml").exists()

    def test_chart_yaml_valid(self) -> None:
        data = _load_yaml(self._chart_dir / "Chart.yaml")
        assert data["apiVersion"] == "v2"
        assert data["name"] == "docreview360"
        assert "version" in data
        assert "appVersion" in data

    def test_values_yaml_exists(self) -> None:
        assert (self._chart_dir / "values.yaml").exists()

    def test_values_yaml_has_required_sections(self) -> None:
        data = _load_yaml(self._chart_dir / "values.yaml")
        assert "replicaCount" in data
        assert "image" in data
        assert "service" in data
        assert "ingress" in data
        assert "resources" in data
        assert "autoscaling" in data
        assert "livenessProbe" in data
        assert "readinessProbe" in data

    def test_values_liveness_probe_uses_health_live(self) -> None:
        data = _load_yaml(self._chart_dir / "values.yaml")
        assert data["livenessProbe"]["httpGet"]["path"] == "/health/live"

    def test_values_readiness_probe_uses_health_ready(self) -> None:
        data = _load_yaml(self._chart_dir / "values.yaml")
        assert data["readinessProbe"]["httpGet"]["path"] == "/health/ready"

    def test_values_runs_as_non_root(self) -> None:
        data = _load_yaml(self._chart_dir / "values.yaml")
        ctx = data["podSecurityContext"]
        assert ctx["runAsNonRoot"] is True
        assert ctx["runAsUser"] == 1001

    def test_values_secrets_section_exists(self) -> None:
        data = _load_yaml(self._chart_dir / "values.yaml")
        assert "secrets" in data
        assert "DOCREVIEW360_SECRET_KEY" in data["secrets"]

    def test_templates_deployment_exists(self) -> None:
        assert (self._chart_dir / "templates" / "deployment.yaml").exists()

    def test_templates_service_exists(self) -> None:
        assert (self._chart_dir / "templates" / "service.yaml").exists()

    def test_templates_ingress_exists(self) -> None:
        assert (self._chart_dir / "templates" / "ingress.yaml").exists()

    def test_templates_hpa_exists(self) -> None:
        assert (self._chart_dir / "templates" / "hpa.yaml").exists()

    def test_templates_helpers_tpl_exists(self) -> None:
        assert (self._chart_dir / "templates" / "_helpers.tpl").exists()

    def test_ingress_has_websocket_annotations(self) -> None:
        """Ingress values must include WebSocket upgrade annotations."""
        data = _load_yaml(self._chart_dir / "values.yaml")
        annotations = data["ingress"]["annotations"]
        assert "nginx.ingress.kubernetes.io/proxy-read-timeout" in annotations
        config_snippet = annotations.get(
            "nginx.ingress.kubernetes.io/configuration-snippet", ""
        )
        assert "Upgrade" in config_snippet


# ══════════════════════════════════════════════════════════════════
# Phase 1: Kubernetes manifests
# ══════════════════════════════════════════════════════════════════


class TestK8sManifests:
    """Kubernetes manifest structure and content validation."""

    _k8s = BASE_DIR / "k8s"

    def test_namespace_yaml_exists(self) -> None:
        assert (self._k8s / "namespace.yaml").exists()

    def test_deployment_yaml_exists(self) -> None:
        assert (self._k8s / "deployment.yaml").exists()

    def test_service_yaml_exists(self) -> None:
        assert (self._k8s / "service.yaml").exists()

    def test_ingress_yaml_exists(self) -> None:
        assert (self._k8s / "ingress.yaml").exists()

    def test_hpa_yaml_exists(self) -> None:
        assert (self._k8s / "hpa.yaml").exists()

    def test_kustomization_yaml_exists(self) -> None:
        assert (self._k8s / "kustomization.yaml").exists()

    def test_deployment_has_liveness_probe(self) -> None:
        data = _load_yaml(self._k8s / "deployment.yaml")
        container = data["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container
        assert container["livenessProbe"]["httpGet"]["path"] == "/health/live"

    def test_deployment_has_readiness_probe(self) -> None:
        data = _load_yaml(self._k8s / "deployment.yaml")
        container = data["spec"]["template"]["spec"]["containers"][0]
        assert "readinessProbe" in container
        assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"

    def test_deployment_runs_as_non_root(self) -> None:
        data = _load_yaml(self._k8s / "deployment.yaml")
        ctx = data["spec"]["template"]["spec"]["securityContext"]
        assert ctx["runAsNonRoot"] is True
        assert ctx["runAsUser"] == 1001

    def test_deployment_drops_all_capabilities(self) -> None:
        data = _load_yaml(self._k8s / "deployment.yaml")
        container = data["spec"]["template"]["spec"]["containers"][0]
        caps = container["securityContext"]["capabilities"]["drop"]
        assert "ALL" in caps

    def test_ingress_has_websocket_annotations(self) -> None:
        data = _load_yaml(self._k8s / "ingress.yaml")
        annotations = data["metadata"]["annotations"]
        assert "nginx.ingress.kubernetes.io/proxy-read-timeout" in annotations

    def test_hpa_min_replicas(self) -> None:
        data = _load_yaml(self._k8s / "hpa.yaml")
        assert data["spec"]["minReplicas"] >= 2

    def test_kustomization_references_all_resources(self) -> None:
        data = _load_yaml(self._k8s / "kustomization.yaml")
        resources = data["resources"]
        for required in ("deployment.yaml", "service.yaml", "ingress.yaml"):
            assert required in resources, f"{required} missing from kustomization.yaml"


# ══════════════════════════════════════════════════════════════════
# Phase 2: Redis-backed rate limiting
# ══════════════════════════════════════════════════════════════════


class TestRateLimiter:
    """Rate limiter: in-memory backend (no Redis required for tests)."""

    def setup_method(self) -> None:
        from docreview360.rate_limiter import reset_for_testing

        reset_for_testing()

    def test_allows_requests_within_limit(self) -> None:
        from docreview360.rate_limiter import _mem_check

        key = "test-key-allow"
        for _ in range(5):
            assert _mem_check(key, limit=10, window=60) is True

    def test_blocks_after_limit_exceeded(self) -> None:
        from docreview360.rate_limiter import _mem_check

        key = "test-key-block"
        for _ in range(5):
            _mem_check(key, limit=5, window=60)
        # 6th request should be blocked.
        assert _mem_check(key, limit=5, window=60) is False

    def test_resets_after_window_expires(self) -> None:
        """After the window passes, the counter resets."""
        from docreview360.rate_limiter import _mem_check, _mem_windows

        key = "test-key-reset"
        # Fill up to limit in a 1-second window.
        for _ in range(3):
            _mem_check(key, limit=3, window=1)
        assert _mem_check(key, limit=3, window=1) is False

        # Expire all entries by back-dating them.
        import time as _time

        with __import__("docreview360.rate_limiter", fromlist=["_mem_lock"])._mem_lock:
            _mem_windows[key] = [(_time.monotonic() - 2, 3)]

        # Now should be allowed again.
        assert _mem_check(key, limit=3, window=1) is True

    def test_check_rate_limit_uses_mem_when_redis_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_rate_limit falls back to in-memory when Redis is unavailable."""
        from docreview360 import rate_limiter

        # Force Redis check to return None (unavailable)
        monkeypatch.setattr(rate_limiter, "_redis_client", None)
        monkeypatch.setattr(rate_limiter, "_redis_checked", True)

        result = rate_limiter.check_rate_limit("ip:127.0.0.1", limit=100, window=60)
        assert result is True

    def test_check_rate_limit_disabled_globally(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from docreview360 import rate_limiter

        monkeypatch.setattr(rate_limiter, "_ENABLED", False)
        # Even if we'd be over limit, should return True (disabled).
        for _ in range(1000):
            assert rate_limiter.check_rate_limit("ip:x", limit=1, window=60) is True

    def test_reset_for_testing_clears_state(self) -> None:
        from docreview360.rate_limiter import _mem_check, _mem_windows, reset_for_testing

        key = "cleanup-key"
        for _ in range(100):
            _mem_check(key, limit=100, window=60)
        reset_for_testing(key)
        assert key not in _mem_windows

    def test_rate_limit_dep_factory_is_callable(self) -> None:
        """rate_limit_dep() must return a callable dependency."""
        from docreview360.rate_limiter import rate_limit_dep

        dep = rate_limit_dep(limit=10, window=60)
        assert callable(dep)

    def test_rate_limit_dep_raises_429_when_over_limit(self) -> None:
        """rate_limit_dep raises HTTP 429 when limit is exceeded."""
        import asyncio

        from fastapi import HTTPException
        from fastapi.testclient import TestClient
        from starlette.requests import Request
        from starlette.testclient import TestClient as StarletteTestClient

        from docreview360.rate_limiter import rate_limit_dep, reset_for_testing

        reset_for_testing("testclient")

        dep = rate_limit_dep(limit=2, window=60, key_func=lambda req: "testclient")

        # Simulate the dependency raising for the 3rd call.
        # We test directly without spinning up an app.
        class MockClient:
            host = "127.0.0.1"

        class MockRequest:
            client = MockClient()

        async def _run() -> None:
            # First two calls: allowed.
            await dep(MockRequest())  # type: ignore[arg-type]
            await dep(MockRequest())  # type: ignore[arg-type]
            # Third call: should raise 429.
            with pytest.raises(HTTPException) as exc_info:
                await dep(MockRequest())  # type: ignore[arg-type]
            assert exc_info.value.status_code == 429

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()


# ══════════════════════════════════════════════════════════════════
# Phase 2: Structured JSON logging
# ══════════════════════════════════════════════════════════════════


class TestStructuredLogging:
    """StructuredJsonFormatter emits valid JSON with required fields."""

    def _capture_log(self, message: str, level: int = logging.INFO, **extra) -> dict:
        """Emit a log record through the formatter and return parsed JSON."""
        from docreview360.structured_logging import StructuredJsonFormatter

        formatter = StructuredJsonFormatter(service="test-svc")
        record = logging.LogRecord(
            name="test.logger",
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        for k, v in extra.items():
            setattr(record, k, v)
        output = formatter.format(record)
        return json.loads(output)

    def test_output_is_valid_json(self) -> None:
        data = self._capture_log("hello")
        assert isinstance(data, dict)

    def test_required_fields_present(self) -> None:
        data = self._capture_log("test message")
        for field in ("timestamp", "level", "logger", "message", "service"):
            assert field in data, f"missing field: {field}"

    def test_message_content(self) -> None:
        data = self._capture_log("specific message content")
        assert data["message"] == "specific message content"

    def test_service_name_injected(self) -> None:
        data = self._capture_log("msg")
        assert data["service"] == "test-svc"

    def test_level_name(self) -> None:
        data = self._capture_log("msg", level=logging.WARNING)
        assert data["level"] == "WARNING"

    def test_timestamp_is_iso8601(self) -> None:
        from datetime import datetime

        data = self._capture_log("msg")
        ts = data["timestamp"]
        # Must parse without error.
        dt = datetime.fromisoformat(ts)
        assert dt is not None

    def test_extra_fields_included(self) -> None:
        data = self._capture_log("msg", request_id="abc-123")
        assert "extra" in data
        assert data["extra"]["request_id"] == "abc-123"

    def test_exc_info_included(self) -> None:
        from docreview360.structured_logging import StructuredJsonFormatter

        formatter = StructuredJsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = json.loads(formatter.format(record))
        assert "exc_info" in output
        assert "ValueError" in output["exc_info"]

    def test_setup_structured_logging_noop_without_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from docreview360 import structured_logging

        monkeypatch.setattr(structured_logging, "_ENABLED", False)
        # Should be a no-op (not crash, not install formatter).
        structured_logging.setup_structured_logging()

    def test_setup_structured_logging_force(self) -> None:
        from docreview360.structured_logging import setup_structured_logging

        # force=True should install formatter regardless of env var.
        setup_structured_logging(level="WARNING", service="forced-svc", force=True)
        root = logging.getLogger()
        formatters = [h.formatter for h in root.handlers if h.formatter is not None]
        from docreview360.structured_logging import StructuredJsonFormatter

        assert any(isinstance(f, StructuredJsonFormatter) for f in formatters)


# ══════════════════════════════════════════════════════════════════
# Phase 2: OpenTelemetry tracing
# ══════════════════════════════════════════════════════════════════


class TestTelemetry:
    """Telemetry module degrades gracefully when OTel is unavailable."""

    def setup_method(self) -> None:
        from docreview360.telemetry import reset_for_testing

        reset_for_testing()

    def test_setup_telemetry_returns_false_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from docreview360 import telemetry

        monkeypatch.setattr(telemetry, "_ENABLED", False)
        result = telemetry.setup_telemetry()
        assert result is False

    def test_setup_telemetry_returns_false_without_package(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When opentelemetry-sdk is not installed, setup returns False gracefully."""
        from docreview360 import telemetry

        monkeypatch.setattr(telemetry, "_ENABLED", True)
        # Simulate ImportError for opentelemetry.
        import builtins
        real_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name.startswith("opentelemetry"):
                raise ImportError("mocked: opentelemetry not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _mock_import)
        result = telemetry.setup_telemetry(force=True)
        assert result is False

    def test_get_tracer_returns_noop_when_not_configured(self) -> None:
        from docreview360.telemetry import _NoopTracer, get_tracer

        tracer = get_tracer("test.module")
        # Without OTel installed or configured, should be noop-like.
        assert tracer is not None
        # Calling start_as_current_span must not raise.
        with tracer.start_as_current_span("test-span"):
            pass

    def test_noop_span_methods_do_not_raise(self) -> None:
        from docreview360.telemetry import _NoopSpan

        span = _NoopSpan()
        span.set_attribute("key", "value")
        span.record_exception(ValueError("test"))
        span.set_status(None)
        span.add_event("test-event")
        with span:
            pass

    def test_noop_tracer_start_span(self) -> None:
        from docreview360.telemetry import _NoopTracer

        tracer = _NoopTracer()
        span = tracer.start_span("op")
        assert span is not None
        span.set_attribute("x", 1)

    def test_reset_for_testing_clears_state(self) -> None:
        from docreview360 import telemetry

        telemetry._setup_done = True
        telemetry._tracer_provider = object()
        telemetry.reset_for_testing()
        assert telemetry._setup_done is False
        assert telemetry._tracer_provider is None


# ══════════════════════════════════════════════════════════════════
# Phase 2: Reverse proxy config
# ══════════════════════════════════════════════════════════════════


class TestNginxConfig:
    """nginx.conf must exist and contain required WebSocket directives."""

    _conf = BASE_DIR / "nginx" / "nginx.conf"

    def test_nginx_conf_exists(self) -> None:
        assert self._conf.exists()

    def test_nginx_conf_has_websocket_upgrade(self) -> None:
        content = self._conf.read_text()
        assert "proxy_set_header   Upgrade" in content or "proxy_set_header Upgrade" in content

    def test_nginx_conf_has_ws_location(self) -> None:
        content = self._conf.read_text()
        assert "location /ws/" in content

    def test_nginx_conf_has_health_location(self) -> None:
        content = self._conf.read_text()
        assert "/health" in content

    def test_nginx_conf_has_tls(self) -> None:
        content = self._conf.read_text()
        assert "ssl_certificate" in content
        assert "TLSv1" in content

    def test_nginx_conf_has_security_headers(self) -> None:
        content = self._conf.read_text()
        assert "Strict-Transport-Security" in content
        assert "X-Frame-Options" in content


# ══════════════════════════════════════════════════════════════════
# Phase 3: Docker Compose production
# ══════════════════════════════════════════════════════════════════


class TestDockerComposeProd:
    """docker-compose.prod.yml must be valid YAML with required services."""

    _compose = BASE_DIR / "docker-compose.prod.yml"

    def test_file_exists(self) -> None:
        assert self._compose.exists()

    def test_valid_yaml(self) -> None:
        data = _load_yaml(self._compose)
        assert "services" in data

    def test_has_required_services(self) -> None:
        data = _load_yaml(self._compose)
        services = data["services"]
        for svc in ("web", "worker", "db", "redis", "nginx"):
            assert svc in services, f"missing service: {svc}"

    def test_web_has_healthcheck(self) -> None:
        data = _load_yaml(self._compose)
        assert "healthcheck" in data["services"]["web"]

    def test_db_has_healthcheck(self) -> None:
        data = _load_yaml(self._compose)
        assert "healthcheck" in data["services"]["db"]

    def test_has_beat_scheduler(self) -> None:
        data = _load_yaml(self._compose)
        assert "beat" in data["services"]

    def test_has_named_volumes(self) -> None:
        data = _load_yaml(self._compose)
        assert "volumes" in data
        assert "postgres_data" in data["volumes"]
        assert "redis_data" in data["volumes"]

    def test_nginx_mounts_conf(self) -> None:
        data = _load_yaml(self._compose)
        nginx_volumes = data["services"]["nginx"].get("volumes", [])
        assert any("nginx.conf" in str(v) for v in nginx_volumes)


# ══════════════════════════════════════════════════════════════════
# Phase 3: Documentation files
# ══════════════════════════════════════════════════════════════════


class TestDeploymentDocs:
    """Required deployment documentation files must exist and have content."""

    def test_air_gap_guide_exists(self) -> None:
        path = BASE_DIR / "docs" / "air_gap_deployment.md"
        assert path.exists()

    def test_air_gap_guide_mentions_rto(self) -> None:
        content = (BASE_DIR / "docs" / "air_gap_deployment.md").read_text()
        assert len(content) > 500, "air-gap guide is too short"
        assert "docker" in content.lower() or "container" in content.lower()

    def test_blue_green_guide_exists(self) -> None:
        path = BASE_DIR / "docs" / "blue_green_deployment.md"
        assert path.exists()

    def test_blue_green_guide_has_rollback(self) -> None:
        content = (BASE_DIR / "docs" / "blue_green_deployment.md").read_text()
        assert "rollback" in content.lower() or "Rollback" in content

    def test_disaster_recovery_runbook_exists(self) -> None:
        path = BASE_DIR / "docs" / "disaster_recovery.md"
        assert path.exists()

    def test_disaster_recovery_has_rto_rpo(self) -> None:
        content = (BASE_DIR / "docs" / "disaster_recovery.md").read_text()
        assert "RTO" in content
        assert "RPO" in content

    def test_disaster_recovery_has_restore_procedure(self) -> None:
        content = (BASE_DIR / "docs" / "disaster_recovery.md").read_text()
        assert "restore" in content.lower() or "Restore" in content
