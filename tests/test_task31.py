from docuflow.notifications import add_template, send_email, sent_emails


def test_send_email() -> None:
    sent_emails.clear()
    add_template("welcome", "Hi {user}", "Hello {user}!")
    email = send_email("welcome", "alice@example.com", user="Alice")
    assert email["to"] == "alice@example.com"
    assert email["subject"] == "Hi Alice"
    assert sent_emails[-1] == email
