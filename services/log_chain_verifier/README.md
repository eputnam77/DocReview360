# Log Chain Verifier

Celery-based service that periodically recomputes the audit log hash chain and
logs any integrity failures. Results are not written when the chain matches to
avoid altering the audit log.
