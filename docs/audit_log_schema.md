# Audit Log Schema

Audit entries are emitted as JSON objects with the following structure:

```json
{
  "type": "object",
  "properties": {
    "event": {"type": "string"},
    "document_id": {"type": "string"},
    "approval_id": {"type": ["string", "null"]},
    "status": {"type": "string"},
    "hash": {"type": "string", "description": "SHA256 or HMAC of the entry"},
    "certificate_url": {"type": ["string", "null"], "format": "uri"},
    "verified_at": {"type": "string", "format": "date-time"},
    "verifier": {"type": ["string", "null"]},
    "context": {"type": "object"}
  },
  "required": ["event", "document_id", "status", "hash", "verified_at"],
  "additionalProperties": true
}
```

* `event` – description of what occurred.
* `document_id` – identifier of the document involved.
* `approval_id` – related approval identifier, when applicable.
* `status` – outcome of the event (e.g., `valid`, `invalid`).
* `hash` – cryptographic digest used to detect tampering. When a secret is
  supplied, the hash becomes an HMAC signature.
* `certificate_url` – link to the certificate associated with the action.
* `verified_at` – UTC timestamp when the event was verified.
* `verifier` – identifier for who performed the verification.
* `context` – optional object containing additional metadata.

Each entry is appended to an immutable log file. The `hash` field is computed
from the remaining properties to provide tamper evidence.

Segments of the log file are also hashed in batches (default 100 entries). A
background task computes a SHA256 digest for each new segment and stores the
digest in an append-only bucket at `tamper_proof_store/audit_anchors` using S3
Object Lock. These external anchors allow later verification that the log file
was not tampered with.

## Example

```python
from docreview360.audit import log_audit_event

entry = log_audit_event(
    "doc-123",
    "signature_validation",
    approval_id="appr-1",
    status="valid",
    verifier="alice",
    certificate_url="https://example.com/cert",
    secret="s3cr3t",
)
print(entry.model_dump(mode="json"))
```
