from docreview360.ai_balancer import (
    assign_job,
    complete_job,
    current_load,
    register_worker,
    reset,
)


def test_balancer_assigns_least_loaded() -> None:
    reset()
    register_worker("a")
    register_worker("b")
    assert assign_job() == "a"
    assert assign_job() == "b"
    assert current_load("a") == 1
    assert current_load("b") == 1
    complete_job("a")
    assert assign_job() == "a"
