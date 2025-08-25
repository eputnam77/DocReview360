# ruff: noqa: E402, I001
from pathlib import Path

import os
import docreview360.database as db_mod

from docreview360 import provider_store
from docreview360.integrations.signature import base

os.environ.setdefault("DOCREVIEW360_DATABASE_URL", "sqlite:///:memory:")
db_mod.Database.migrate = lambda self, *args, **kwargs: None  # type: ignore[misc]
import docreview360.logs as logs_mod
import docreview360.audit as audit_mod
from services.provider_health import check_provider_health  # noqa: E402


class GoodProvider:
    name = "good"

    def request_signature(self, *a, **k):  # pragma: no cover - stub
        return "id", "url", {}

    def process_webhook(self, data):  # pragma: no cover - stub
        pass

    def verify_signature(self, sid, doc):  # pragma: no cover - stub
        return True

    def validate_signature(self, b, c, m):  # pragma: no cover - stub
        return True

    def health_check(self) -> bool:
        return True


class BadProvider:
    name = "bad"

    def request_signature(self, *a, **k):  # pragma: no cover - stub
        raise RuntimeError

    def process_webhook(self, data):  # pragma: no cover - stub
        pass

    def verify_signature(self, sid, doc):  # pragma: no cover - stub
        return False

    def validate_signature(self, b, c, m):  # pragma: no cover - stub
        return False

    def health_check(self) -> bool:
        return False


def test_health_job_updates_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(logs_mod, "log_event", lambda *a, **k: None)
    monkeypatch.setattr(audit_mod, "log_audit_event", lambda *a, **k: None)
    path = tmp_path / "providers.yaml"
    monkeypatch.setattr(provider_store, "PROVIDERS_FILE", path)
    monkeypatch.setattr(provider_store, "DEFAULT_PROVIDERS", {})
    provider_store.save_providers(
        {
            "good": {"api_key": "", "priority": 1, "healthy": True},
            "bad": {"api_key": "", "priority": 2, "healthy": True},
        },
        path,
    )
    base.providers.clear()
    base.register_provider(GoodProvider())
    base.register_provider(BadProvider())
    result = check_provider_health()
    assert result == {"good": True, "bad": False}
    data = provider_store.load_providers(path)
    assert data["bad"]["healthy"] is False
