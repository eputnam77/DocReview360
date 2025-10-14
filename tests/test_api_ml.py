from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient


class _FakeSession:
    """Minimal ONNX Runtime session stub for deterministic testing."""

    def __init__(self, path: str | Path, providers: Any | None = None) -> None:  # noqa: D401
        self._model_path = str(Path(path))

    def run(self, _outputs: Any, inputs: dict[str, np.ndarray]) -> list[np.ndarray]:
        path = Path(self._model_path)
        if path.name == "quality_critic.onnx":
            score = np.array([[0.82]], dtype=np.float32)
            flags = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
            return [score, flags]
        if path.name == "routing_reviewer.onnx":
            approval = np.array([[0.75]], dtype=np.float32)
            logits = np.array([[0.3, 0.2, 0.1]], dtype=np.float32)
            return [approval, logits]
        if path.name == "signature_anomaly.onnx":
            return [np.array([[0.4]], dtype=np.float32)]
        if path.name == "compliance_mlp.onnx":
            return [np.array([[0.55]], dtype=np.float32)]
        return [np.array([[0.5]], dtype=np.float32)]

    def get_modelmeta(self) -> Any:
        path = Path(self._model_path)
        metadata_map: dict[str, str] = {}
        if path.name == "quality_critic.onnx":
            metadata_map = {"docreview360:flags": "clarity,accuracy,structure"}
        elif path.name == "routing_reviewer.onnx":
            metadata_map = {"docreview360:reviewers": "alice,bob,charlie"}
        elif path.name == "signature_anomaly.onnx":
            metadata_map = {"docreview360:model": "signature-anomaly"}
        return types.SimpleNamespace(
            graph_name=path.stem,
            version="1.0.0",
            custom_metadata_map=metadata_map,
        )


def _fake_get_session(path: str | Path, *, providers: Any | None = None) -> _FakeSession:
    return _FakeSession(path, providers)


_fake_ort = types.ModuleType("onnxruntime")
_fake_ort.get_available_providers = lambda: ["CPUExecutionProvider"]
_fake_ort.InferenceSession = _FakeSession
sys.modules["onnxruntime"] = _fake_ort

import docreview360.ml.onnx_infer as onnx_infer  # noqa: E402
import docreview360.auth as auth  # noqa: E402

onnx_infer.get_session = _fake_get_session


def _fake_get_model_metadata(session_or_path: Any) -> onnx_infer.ModelMetadata:
    if isinstance(session_or_path, _FakeSession):
        path = Path(session_or_path._model_path)
    else:
        path = Path(session_or_path)
    metadata_map: dict[str, str] = {}
    if path.name == "quality_critic.onnx":
        metadata_map = {"docreview360:flags": "clarity,accuracy,structure"}
    elif path.name == "routing_reviewer.onnx":
        metadata_map = {"docreview360:reviewers": "alice,bob,charlie"}
    elif path.name == "signature_anomaly.onnx":
        metadata_map = {"docreview360:model": "signature-anomaly"}
    return onnx_infer.ModelMetadata(
        path=path,
        sha256="stub",
        version="1.0.0",
        custom_metadata=metadata_map,
    )


onnx_infer.get_model_metadata = _fake_get_model_metadata


def _prefilled_current_user(request: Any = None, token: str | None = None) -> auth.User:
    return auth.User(username="alice", active=True)


auth.get_current_user = _prefilled_current_user

from docreview360.api import app  # noqa: E402
from docreview360.api import ml as ml_module  # noqa: E402
from docreview360.ml.features import SIGNATURE_ANOMALY_FEATURE_NAMES  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """Return a test client with deterministic rate limiting state."""

    ml_module.reset_rate_limiter_for_testing()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def audit_spy(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    """Capture audit log invocations."""

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def recorder(*args: Any, **kwargs: Any) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(ml_module, "log_audit_event", recorder)
    return calls


def test_quality_endpoint_returns_assessment(
    client: TestClient, audit_spy: list[tuple[tuple[Any, ...], dict[str, Any]]]
) -> None:
    payload = {
        "text": "This policy memo should be reviewed for clarity and compliance.",
        "doc_type": "policy_memo",
        "document_id": "doc-123",
    }

    response = client.post("/ml/quality", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "score" in data
    assert "raw_score" in data
    assert len(audit_spy) == 1
    assert audit_spy[0][0][0] == "doc-123"
    assert audit_spy[0][0][1] == "ml_quality_assessment"


def test_quality_endpoint_requires_text(client: TestClient) -> None:
    response = client.post("/ml/quality", json={"text": ""})
    assert response.status_code == 422


def test_quality_endpoint_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ml_module, "log_audit_event", lambda *args, **kwargs: None)

    for idx in range(ml_module._RATE_LIMIT_CALLS):
        response = client.post(
            "/ml/quality",
            json={"text": "Document text", "document_id": f"doc-{idx}"},
        )
        assert response.status_code == 200

    response = client.post(
        "/ml/quality",
        json={"text": "Another document", "document_id": "doc-over"},
    )
    assert response.status_code == 429


def test_compliance_endpoint_returns_result(
    client: TestClient, audit_spy: list[tuple[tuple[Any, ...], dict[str, Any]]]
) -> None:
    payload = {
        "text": "Ensure metadata completeness and readability meet standards.",
        "metadata": {"readability": 0.9, "structure": 0.8},
        "document_id": "compliance-1",
    }

    response = client.post("/ml/compliance", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "probability" in data
    assert len(audit_spy) == 1
    assert audit_spy[0][0][1] == "ml_compliance_evaluation"


def test_compliance_endpoint_requires_text(client: TestClient) -> None:
    response = client.post("/ml/compliance", json={"text": ""})
    assert response.status_code == 422


def test_routing_endpoint_returns_recommendations(
    client: TestClient, audit_spy: list[tuple[tuple[Any, ...], dict[str, Any]]]
) -> None:
    payload = {
        "text": "Draft requires specialist routing to reviewers familiar with safety.",
        "top_k": 2,
        "document_id": "routing-42",
    }

    response = client.post("/ml/routing", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["reviewers"]
    assert len(data["reviewers"]) <= payload["top_k"]
    assert len(audit_spy) == 1
    assert audit_spy[0][0][1] == "ml_routing_recommendation"


def test_routing_endpoint_validates_top_k(client: TestClient) -> None:
    response = client.post("/ml/routing", json={"text": "Needs routing", "top_k": 0})
    assert response.status_code == 422


def test_signature_endpoint_returns_score(
    client: TestClient, audit_spy: list[tuple[tuple[Any, ...], dict[str, Any]]]
) -> None:
    features = [0.1] * len(SIGNATURE_ANOMALY_FEATURE_NAMES)
    payload = {"features": features, "document_id": "signature-7"}

    response = client.post("/ml/signature", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "score" in data
    assert isinstance(data.get("metadata"), dict)
    assert len(audit_spy) == 1
    assert audit_spy[0][0][1] == "ml_signature_anomaly"


def test_signature_endpoint_validates_feature_length(client: TestClient) -> None:
    features = [0.0] * (len(SIGNATURE_ANOMALY_FEATURE_NAMES) - 1)
    response = client.post("/ml/signature", json={"features": features})
    assert response.status_code == 422


def test_lifespan_warmup_runs_once() -> None:
    ml_module.reset_warm_state_for_testing()

    with TestClient(app) as client:
        client.get("/ping")
    assert ml_module.warmup_count() == 1

    with TestClient(app) as client:
        client.get("/ping")
    assert ml_module.warmup_count() == 1
