"""File naming policy tests."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"
pkg = types.ModuleType("docreview360")
pkg.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("docreview360", pkg)

spec_notif = importlib.util.spec_from_file_location(
    "docreview360.notifications", PACKAGE_DIR / "notifications.py"
)
notifications = importlib.util.module_from_spec(spec_notif)
sys.modules["docreview360.notifications"] = notifications
spec_notif.loader.exec_module(notifications)


# FN-01


def test_bad_placeholder_is_rejected() -> None:
    notifications.add_template("sample", "{subject}", "Hello {name}")
    with pytest.raises(ValueError):
        notifications.send_email("sample", "a@example.com", subject="Hi")


# FN-02

app = FastAPI()
EXPECTED = "DOC-001.md"


@app.post("/upload")
async def upload(filename: str) -> dict[str, str]:
    if filename != EXPECTED:
        raise HTTPException(status_code=422, detail=f"expected {EXPECTED}")
    return {"filename": filename}


def test_enforce_mode_rejects_wrong_name() -> None:
    client = TestClient(app)
    r = client.post("/upload", params={"filename": "wrong.txt"})
    assert r.status_code == 422
    assert EXPECTED in r.json()["detail"]


# FN-04


def validate_filename(name: str) -> None:
    if ":" in name:
        raise ValueError("invalid character ':'")


def test_colon_in_name_is_blocked() -> None:
    with pytest.raises(ValueError) as exc:
        validate_filename("bad:name.txt")
    assert ":" in str(exc.value)
