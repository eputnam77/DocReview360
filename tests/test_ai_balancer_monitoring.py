from __future__ import annotations

from docreview360.ai_balancer import (
    JOB_ASSIGNMENTS,
    WORKER_DEREGISTRATIONS,
    WORKER_REGISTRATIONS,
    assign_job,
    deregister_worker,
    register_worker,
    reset,
)


def test_monitoring_counters_increment() -> None:
    reset()
    start_reg = WORKER_REGISTRATIONS._value.get()
    child = JOB_ASSIGNMENTS.labels(worker="alice")
    start_assign = child._value.get()
    start_dereg = WORKER_DEREGISTRATIONS._value.get()

    register_worker("alice")
    assign_job()
    deregister_worker("alice")

    assert WORKER_REGISTRATIONS._value.get() == start_reg + 1
    assert child._value.get() == start_assign + 1
    assert WORKER_DEREGISTRATIONS._value.get() == start_dereg + 1
