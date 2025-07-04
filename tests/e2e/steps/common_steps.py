import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from docuflow.api import app

scenarios("../features")


@pytest.fixture
def context():
    return {}


@given("the system is running")
def system_running(context):
    context["client"] = TestClient(app)


@when("the feature is exercised")
def feature_exercised(context):
    resp = context["client"].get("/projects")
    context["result"] = resp


@then("the expected behaviour occurs")
def expected_behaviour(context):
    assert context["result"].status_code == 200
