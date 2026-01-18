from docreview360.workflow_components import StepInstance, StepStatusBadge


def test_step_status_badge_render():
    badge = StepStatusBadge()
    step = StepInstance(name="review", status="approved")
    html = badge.render(step)
    assert "<span" in html and "approved" in html
