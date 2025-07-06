# End-to-End Report

The BDD scenarios in `tests/e2e/features` execute using shared steps.
Each scenario starts the FastAPI test client and hits the `/projects`
endpoint to confirm the service responds successfully. All scenarios
passed which verifies the application boots and basic routing works.
