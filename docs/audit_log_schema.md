# Audit Event Schema

DocReview360 emits audit events as JSON objects that follow this schema:

```json
{
  "type": "object",
  "properties": {
    "timestamp": {"type": "string", "format": "date-time"},
    "event": {"type": "string"},
    "user": {"type": ["string", "null"]},
    "doc_id": {"type": ["string", "null"]},
    "details": {"type": "object"}
  },
  "required": ["timestamp", "event"],
  "additionalProperties": false
}
```

* ``timestamp`` – UTC time when the event occurred.
* ``event`` – name of the action that took place.
* ``user`` – identifier of the user who triggered the event (if known).
* ``doc_id`` – associated document identifier, when applicable.
* ``details`` – free-form metadata providing additional context.

Utilities such as `log_event` and `log_audit_event` return objects based on
this schema and can be serialized with ``model_dump()`` for exporting.
