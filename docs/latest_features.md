# Latest Features

This guide introduces the most recent additions to DocReview360 and walks you through common tasks. It assumes you have already followed the [Getting Started](getting_started.md) steps.

## GraphQL Read Layer

DocReview360 now ships with a lightweight GraphQL API. You can query projects and documents using standard GraphQL syntax. The helper function `execute_query` lives in `docreview360.graphql_api` and provides read‑only access.

Example:

```python
from docreview360.graphql_api import execute_query

result = execute_query("{ projects { id name } }")
```

The API returns a dictionary with the requested fields.

## Special Conditions Doc Builder

The tools section now includes a **Special Conditions Doc Builder** interface.
Click the card on the tools page to launch `/tools/sc_converter`. The
implementation lives in a private repository and should be installed separately:
<https://github.com/eputnam77/SCDocBuilder.git>.

## File Storage Plugin

A new object storage helper lets you store files on disk or in services like MinIO. Use `docreview360.object_storage.upload_file` to save data and receive a file path in return.

```python
from docreview360.object_storage import upload_file

path = upload_file("bucket", "example.txt", b"data")
```

This can be plugged into your own workflows for persistent storage.

