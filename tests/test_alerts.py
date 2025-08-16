from docreview360 import alerts
from docreview360.logs import alerts as registered_alerts
from docreview360.logs import clear_logs, log_event, logs
from docreview360.notifications import sent_emails


def setup_function() -> None:
    sent_emails.clear()
    alerts.sent_slack_messages.clear()
    registered_alerts.clear()
    clear_logs()


def test_mass_approval_alert_triggers_notifications_and_log() -> None:
    alerts.register_mass_approval_alert(threshold=2, email="ops@example.com", slack="#ops")
    log_event("approval_granted", user_id="alice")
    assert not sent_emails
    log_event("approval_granted", user_id="alice")
    assert sent_emails[0]["to"] == "ops@example.com"
    assert alerts.sent_slack_messages[0]["channel"] == "#ops"
    assert logs[-1].action == "alert_mass_approval"


def test_failed_login_alert_triggers_notifications_and_log() -> None:
    alerts.register_failed_login_alert(threshold=2, email="sec@example.com")
    log_event("login_failed", user_id="bob")
    log_event("login_failed", user_id="bob")
    assert sent_emails[0]["to"] == "sec@example.com"
    assert logs[-1].action == "alert_failed_login"
