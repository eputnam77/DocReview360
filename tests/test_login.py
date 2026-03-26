from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient


def test_login_flow() -> None:
    client = TestClient(app)
    repo = auth._get_user_repository()
    password = "AdminPass123!"
    if repo.get_user("admin") is None:
        repo.create_user("admin", password)

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
        data={"username": "admin", "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/projects"
    cookie = resp.cookies.get("session")
    assert cookie is not None
    assert cookie != "admin"
    assert cookie.count(":") == 2

    # signed cookie grants dashboard access
    client.cookies.set("session", cookie)
    dashboard = client.get("/dashboard", follow_redirects=False)
    assert dashboard.status_code == 200

    # follow redirect should normally load the projects page
    # (omitted here as the frontend route is handled by Next.js)


def test_dashboard_rejects_tampered_session_cookie() -> None:
    client = TestClient(app)
    client.cookies.set("session", "admin:1:invalidsig")
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
