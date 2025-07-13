from docreview360.workflows import (
    WorkflowModel,
    advance_workflow,
    create_workflow,
    register_bot,
)


def test_a2_bot_callback_called() -> None:
    events: list[str] = []

    def cb(wf: WorkflowModel) -> None:
        events.append(f"{wf.id}:{wf.phase}")

    register_bot(cb)
    wf = create_workflow("p1", ["draft", "review"])
    advance_workflow(wf.id)
    assert events == [f"{wf.id}:draft", f"{wf.id}:review"]
