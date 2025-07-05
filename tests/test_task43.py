from docuflow import auth


def test_authenticate_mfa() -> None:
    user = auth.authenticate_mfa("alice", "password", "123456")
    assert user and user.username == "alice"
    bad = auth.authenticate_mfa("alice", "password", "000000")
    assert bad is None
