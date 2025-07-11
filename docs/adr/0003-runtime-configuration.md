# 0003 - Runtime Configuration

This short record mirrors ADR-0008 in `.dev/ADRs/`. DocReview360 reads `docuflow.yaml` from the project root to configure authentication, the database and optional services. The provided `docker-compose.yml` uses the same file so you can spin up the stack with a single command. Copy the YAML file to adjust settings without altering source code.
