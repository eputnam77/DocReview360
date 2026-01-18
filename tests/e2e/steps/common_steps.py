from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from docreview360.api import app

scenarios("../features")


@pytest.fixture
def context() -> Dict[str, Any]:
    return {}


@given("the system is running")
def system_running(context: Dict[str, Any]) -> None:
    context["client"] = TestClient(app)


@when("the feature is exercised")
def feature_exercised(context: Dict[str, Any]) -> None:
    resp = context["client"].get("/projects")
    context["result"] = resp


@then("the expected behavior occurs")
def expected_behavior(context: Dict[str, Any]) -> None:
    assert context["result"].status_code == 200
