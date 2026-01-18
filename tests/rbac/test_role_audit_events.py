from __future__ import annotations

from pathlib import Path

from docreview360 import rbac


def test_role_mutations_emit_audit_events(tmp_path: Path, monkeypatch) -> None:
    events: list[dict[str, object]] = []

    def _capture_audit(
        document_id: str,
        event: str,
        *,
        actor: str | None = None,
        **context: object,
    ) -> object:
        events.append(
            {
                "document_id": document_id,
                "event": event,
                "actor": actor,
                "context": context,
            }
        )
        return object()

    monkeypatch.setattr(rbac, "log_audit_event", _capture_audit)

    rbac.configure_role_repository(tmp_path / "roles.db")
    rbac.reset_role_assignments(include_defaults=False)

    rbac.set_user_roles("bob", ["reviewer"], actor="auditor", context={"source": "seed"})
    rbac.set_user_roles("bob", ["admin"], actor="auditor", context={"source": "seed"})
    rbac.remove_role("bob", "admin", actor="auditor")
    rbac.reset_role_assignments(
        include_defaults=False,
        actor="scheduler",
        context={"ticket": "ops-42"},
    )

    added_events = [evt for evt in events if evt["event"] == "role_added"]
    removed_events = [evt for evt in events if evt["event"] == "role_removed"]
    reset_events = [evt for evt in events if evt["event"] == "roles_reset"]

    assert added_events
    assert removed_events
    assert reset_events and reset_events[0]["document_id"] == "rbac::global"

    first_add = next(evt for evt in added_events if evt["context"]["role"] == "reviewer")
    assert first_add["actor"] == "auditor"
    assert first_add["document_id"] == "rbac::bob"
    assert first_add["context"]["target_user"] == "bob"
    assert first_add["context"]["roles_after"] == ["reviewer"]
    assert first_add["context"]["roles_before"] == []
    assert first_add["context"]["source"] == "seed"

    admin_removed = next(evt for evt in removed_events if evt["context"]["role"] == "admin")
    assert admin_removed["context"]["roles_after"] == []
    assert admin_removed["actor"] == "auditor"

    reset_context = reset_events[-1]["context"]
    assert reset_context["include_defaults"] is False
    assert reset_context["ticket"] == "ops-42"
