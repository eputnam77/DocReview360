from docreview360 import ai_balancer


def test_assign_job_breaks_ties_alphabetically() -> None:
    """Workers with equal loads are chosen in alphabetical order."""
    ai_balancer.reset()
    ai_balancer.register_worker("b")
    ai_balancer.register_worker("a")
    # Both workers have load 0; alphabetical order should prevail
    assert ai_balancer.assign_job() == "a"
