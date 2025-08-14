"""Tests for template upload endpoint."""

import importlib.util
import json
import sys
import types
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.testclient import TestClient

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"
pkg = types.ModuleType("docreview360")
pkg.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("docreview360", pkg)

spec_tm = importlib.util.spec_from_file_location(
    "docreview360.template_manager", PACKAGE_DIR / "template_manager.py"
)
template_manager = importlib.util.module_from_spec(spec_tm)
sys.modules["docreview360.template_manager"] = template_manager
spec_tm.loader.exec_module(template_manager)

app = FastAPI()


@app.post("/templates", status_code=201)
async def upload_template_endpoint(
    name: str = Form(...),
    meta: str = Form("{}"),
    file: UploadFile = File(...),
) -> dict[str, int]:
    metadata = json.loads(meta)
    content = await file.read()
    version = template_manager.upload_template(name, content, metadata)
    return {"version": version.version}


def test_template_upload_creates_version() -> None:
    client = TestClient(app)
    resp = client.post(
        "/templates",
        data={"name": "policy", "meta": json.dumps({"desc": "test"})},
        files={"file": ("policy.md", b"# Policy")},
    )
    assert resp.status_code == 201
    assert resp.json()["version"] == 1
    versions = template_manager.list_template_versions("policy")
    assert len(versions) == 1
    assert versions[0].metadata == {"desc": "test"}

