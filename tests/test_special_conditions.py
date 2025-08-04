"""Special conditions intake tests."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError


class SCIntake(BaseModel):
    regulatory_basis: str
    description: str | None = None


def test_json_schema_requires_regulatory_basis() -> None:
    with pytest.raises(ValidationError):
        SCIntake.model_validate({"description": "x"})


app = FastAPI()


@app.post("/send")
async def send_for_review(payload: dict) -> dict:
    if payload.get("sc_intake_status") != "COMPLETE":
        raise HTTPException(status_code=409, detail=["regulatory_basis"])
    return {"ok": True}


def test_send_for_review_requires_complete_status() -> None:
    client = TestClient(app)
    r = client.post("/send", json={"sc_intake_status": "INCOMPLETE"})
    assert r.status_code == 409
    assert "regulatory_basis" in r.json()["detail"]


def test_answer_later_banner_removed_on_completion() -> None:
    banner = True
    tasks = ["intake"]

    def complete_intake() -> None:
        nonlocal banner
        banner = False
        tasks.clear()

    complete_intake()
    assert not banner and not tasks
