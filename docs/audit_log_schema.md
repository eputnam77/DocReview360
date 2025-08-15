# Audit Event Schema

DocReview360 emits audit events as JSON objects that follow this schema:

```json
{
  "type": "object",
  "properties": {
    "timestamp": {"type": "string", "format": "date-time"},
    "actor": {"type": ["string", "null"]},
    "action": {"type": "string"},
    "context": {"type": "object"}
  },
  "required": ["timestamp", "action"],
  "additionalProperties": false
}
```

* ``timestamp`` – UTC time when the event occurred.
* ``actor`` – identifier of who triggered the event (if known).
* ``action`` – name of the activity that took place.
* ``context`` – free-form metadata providing additional detail, such as
  ``doc_id`` or ``project``.

Utilities such as `log_event` and `log_audit_event` return objects based on
this schema and can be serialized with ``model_dump()`` for exporting.

## Usage example

```python
from docreview360.logs import log_event

event = log_event(
    "document_created",
    actor="alice",
    doc_id="123",
    project="alpha",
)
print(event.model_dump(mode="json"))
```

Example output:

```json
{
  "timestamp": "2024-01-01T12:00:00+00:00",
  "actor": "alice",
  "action": "document_created",
  "context": {
    "doc_id": "123",
    "project": "alpha"
  }
}
```
