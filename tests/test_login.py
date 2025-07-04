from docuflow.api import app
from fastapi.testclient import TestClient


def test_login_flow() -> None:
    client = TestClient(app)

    # initial page should show login form
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Login to DocuFlow" in resp.text

    # invalid credentials stay on login page
    resp = client.post("/login", data={"username": "bad", "password": "bad"})
    assert resp.status_code == 400
    assert "Invalid credentials" in resp.text

    # valid login redirects and sets cookie
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
    cookie = resp.cookies.get("session")
    assert cookie == "admin"

    # follow redirect to dashboard
    resp = client.get("/dashboard", cookies={"session": cookie})
    assert resp.status_code == 200
    assert "Welcome to DocuFlow" in resp.text
