# DocuFlow

DocuFlow helps you organise documents, run simple approval workflows and keep track of your projects. The prototype ships with a small web API, a tiny frontend and a one-command CLI wizard. It is intentionally lightweight so you can explore the features and decide how they fit your own process.

## Quick start

1. **Install the package**
   ```bash
   pip install -e .
   ```
2. **Create a configuration file**
   ```bash
   python -m docuflow.cli init
   ```
   The wizard asks for your preferred database, editor and other options then stores them in `docuflow.yml`.
3. **Run the development server**
   ```bash
   uvicorn docuflow.api:app --reload
   ```
4. **Open <http://127.0.0.1:8000/>** and sign in with `admin/admin`.
   You'll land on the dashboard where you can jump to the editor or explore the API docs.

A demo token is available with:
```bash
curl -X POST -d "username=alice&password=password" http://127.0.0.1:8000/oidc/token
```
Use the token in the `Authorization` header to call `/oidc/me`.

The API is a learning tool. Endpoints return dummy data but illustrate how projects, documents and approvals could work together. The frontend contains a login page, a dashboard, a project creation form and a basic editor shell.

## Features

- In-memory storage for projects and documents
- Import/export of Markdown and DOCX files
- Search with saved queries
- Simple plugin system for editors and exporters
- Minimal authentication flow with a login form, dashboard and project creation page

Head over to the [documentation](https://example.com/docuflow) for a full tour of the API, CLI options and UI navigation tips.
