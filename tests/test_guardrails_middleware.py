import importlib

import pytest
from fastapi.testclient import TestClient


def test_guardrails_middleware_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_GUARDRAILS", "1")
    module = importlib.import_module("docreview360.api")
    importlib.reload(module)

    assert any(m.cls.__name__ == "GuardrailsMiddleware" for m in module.app.user_middleware)

    client = TestClient(module.app)
    resp = client.post("/ai/rewrite", json={"text": "SSN 123-45-6789"})
    assert resp.status_code == 400
