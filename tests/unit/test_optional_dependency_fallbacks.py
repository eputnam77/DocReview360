"""Unit tests for optional dependency fallbacks."""

from __future__ import annotations

import pytest
from docreview360 import auth, documents
from docreview360.ml import onnx_infer, routing_critic, signature_anomaly, torch_models


def test_auth_hash_password_fallback_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    monkeypatch.setattr(sys.modules["docreview360.auth._repository"], "bcrypt", None)
    password = "Valid-Pass123!"
    password_hash = auth.UserRepository.hash_password(password)
    assert password_hash.startswith("pbkdf2$")
    assert auth.UserRepository.verify_password(password, password_hash) is True
    assert auth.UserRepository.verify_password("wrong-password", password_hash) is False


def test_auth_verify_otp_fallback_when_pyotp_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys
    monkeypatch.setattr(sys.modules["docreview360.auth._repository"], "pyotp", None)
    assert auth.UserRepository.verify_otp("secret123", "secret123") is True
    assert auth.UserRepository.verify_otp("secret123", "000000") is False
    assert auth.UserRepository.verify_otp("123456", "123456") is True
    assert auth.UserRepository.verify_otp("123456", "654321") is False


def test_sanitize_content_without_bleach(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    monkeypatch.setattr(sys.modules["docreview360.documents._store"], "bleach", None)
    content = "<h1>Title</h1><script>alert(1)</script><p>Body</p>"
    sanitized = documents.sanitize_content(content)
    assert "script" not in sanitized.lower()
    assert "Title" in sanitized
    assert "Body" in sanitized


def test_onnx_infer_requires_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(onnx_infer, "ort", None)
    with pytest.raises(onnx_infer.OnnxRuntimeUnavailable, match="onnxruntime is not installed"):
        onnx_infer.get_session("model.onnx")


def test_routing_critic_export_requires_onnx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routing_critic, "helper", None)
    monkeypatch.setattr(routing_critic, "onnx", None)
    critic = routing_critic.RoutingCritic(["alice"])
    with pytest.raises(RuntimeError, match="onnx is not installed"):
        routing_critic.export_routing_critic_to_onnx(critic, "routing.onnx")


def test_torch_models_export_requires_onnx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch_models, "onnx", None)
    monkeypatch.setattr(torch_models, "onnx_helper", None)
    monkeypatch.setattr(torch_models, "onnx_numpy_helper", None)
    critic = torch_models.build_clarity_critic()
    with pytest.raises(RuntimeError, match="onnx is not installed"):
        torch_models.export_critic_to_onnx(critic, "critic.onnx")


def test_signature_anomaly_metadata_fallback_when_onnx_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(signature_anomaly, "helper", None)
    meta = signature_anomaly.get_signature_anomaly_metadata()
    assert meta.version == signature_anomaly.MODEL_VERSION
    assert meta.custom_metadata == {}
    assert meta.path == signature_anomaly.MODEL_PATH
