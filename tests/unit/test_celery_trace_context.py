from docreview360.celery_app import echo
from docreview360.logs import TRACE_ID


def test_traced_task_restores_trace_context() -> None:
    token = TRACE_ID.set("seed")
    try:
        echo.apply(args=("value",), headers={"trace_id": "abc"})
        assert TRACE_ID.get(None) == "seed"
    finally:
        TRACE_ID.reset(token)

    token = TRACE_ID.set(None)
    try:
        echo.apply(args=("value",), headers={})
        assert TRACE_ID.get(None) is None
    finally:
        TRACE_ID.reset(token)
