from docuflow.workflows import advance_workflow, create_workflow, register_bot


def test_a2_bot_callback_called() -> None:
    events: list[str] = []

    def cb(wf):
        events.append(f"{wf.id}:{wf.phase}")

    register_bot(cb)
    wf = create_workflow("p1", ["draft", "review"])
    advance_workflow(wf.id)
    assert events == [f"{wf.id}:draft", f"{wf.id}:review"]
