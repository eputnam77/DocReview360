# Latest Features

This guide introduces the most recent additions to DocuFlow and walks you through common tasks. It assumes you have already followed the [Getting Started](getting_started.md) steps.

## GraphQL Read Layer

DocuFlow now ships with a lightweight GraphQL API. You can query projects and documents using standard GraphQL syntax. The helper function `execute_query` lives in `docuflow.graphql_api` and provides read‑only access.

Example:

```python
from docuflow.graphql_api import execute_query

result = execute_query("{ projects { id name } }")
```

The API returns a dictionary with the requested fields.

## File Storage Plugin

A new object storage helper lets you store files on disk or in services like MinIO. Use `docuflow.object_storage.upload_file` to save data and receive a file path in return.

```python
from docuflow.object_storage import upload_file

path = upload_file("bucket", "example.txt", b"data")
```

This can be plugged into your own workflows for persistent storage.

