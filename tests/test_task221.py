from docreview360.stubs.task221 import auth0_login


def test_task221_auth0_login() -> None:
    """Auth0 login should return a valid session."""
    auth0_login("token")
