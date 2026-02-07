"""Tests for template upload endpoint."""

import json
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.testclient import TestClient


def test_template_upload_creates_version(tmp_path: Path) -> None:
    src_root = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src_root))
    try:
        from docreview360 import template_manager

        app = FastAPI()

        @app.post("/templates", status_code=201)
        async def _upload_template_endpoint(
            name: str = Form(...),
            meta: str = Form("{}"),
            file: UploadFile = File(...),
        ) -> dict[str, int]:
            metadata = json.loads(meta)
            content = await file.read()
            version = template_manager.upload_template(name, content, metadata)
            return {"version": version.version}

        client = TestClient(app)
        template_manager.reset_template_store(root=tmp_path / "template_store.json")
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
    finally:
        sys.path.remove(str(src_root))
        sys.modules.pop("docreview360", None)
        sys.modules.pop("docreview360.template_manager", None)
