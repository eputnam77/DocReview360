from fastapi.testclient import TestClient

from docreview360.api import app


def test_login_flow() -> None:
    client = TestClient(app)

    # initial page should show login form
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Login to DocReview360" in resp.text

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
    assert resp.headers["location"] == "/projects"
    cookie = resp.cookies.get("session")
    assert cookie == "admin"

    # follow redirect should normally load the projects page
    # (omitted here as the frontend route is handled by Next.js)
