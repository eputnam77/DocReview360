from docreview360.stubs.task86 import has_trivy_step


def test_has_trivy_step() -> None:
    workflow = """
    jobs:
      build:
        steps:
          - name: Run Trivy
            uses: aquasec/trivy@v1
    """
    assert has_trivy_step(workflow)
