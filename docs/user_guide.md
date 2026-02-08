# User Guide

This walkthrough helps you explore DocReview360 from the perspective of a new user. You will log in, open the editor, add reviewers and approve documents. The guide also explains how to configure the application for different environments.

## 1. Access the projects page

1. Start the server with `uvicorn docreview360.api:app --reload --host 0.0.0.0` so remote browsers and Playwright tests can reach it.
2. Open `http://127.0.0.1:8000/` in your browser.
3. Sign in with the credentials from your `docreview360.yml` file (the defaults are `admin/admin`).
4. The projects page greets you and provides links to the editor and API docs.

## 2. Open the document editor

1. From the projects page click **Editor**.
2. A rich text field appears where you can type or paste content. This preview uses the Tiptap editor.
3. Start from a blank canvas or load a template from the sidebar. Templates can optionally lock some formatting controls while still allowing inline styling.
4. When a CMS is configured, TipTap revisions are automatically saved to the CMS in the background.
5. To enable AI rewrite suggestions, save an OpenAI API key in **Configuration → Integrations** under the AI Rewrite section.

### Changing the editor

The configuration file contains an `editor` setting. Supported values include `tiptap` and `word`.

1. Run `docreview360 init` to regenerate the file or edit it manually.
2. Set `editor: tiptap` (or another option) and restart the server.
3. The next time you open the editor the new tool loads.

Optional TipTap extensions can be discovered and managed at runtime. See
the [plugin guide](tiptap-plugins.md) for details on registering or disabling
wrappers.

## 3. Add a reviewer and request approval

1. Use the API endpoint `POST /approvals` to create an approval request. Provide the document ID and the reviewer name.
2. The reviewer can fetch requests with `GET /approvals`.
3. When they are satisfied they call `PUT /approvals/{approval_id}` with the new state `approved`.

## 4. Configure your environment

DocReview360 stores its settings in `docreview360.yml`. Before running the wizard or the server, export the authentication secrets:

```bash
export DOCREVIEW360_SECRET_KEY=your-secret
export DOCREVIEW360_ALGORITHM=HS256
export DOCREVIEW360_ACCESS_EXPIRE_MINUTES=30
export DOCREVIEW360_TOKEN_ISSUER=docreview360.local
export DOCREVIEW360_TOKEN_AUDIENCE=docreview360-users
export DOCREVIEW360_OIDC_SECRET_KEY=your-oidc-secret
export DOCREVIEW360_OIDC_ALGORITHM=HS256
export DOCREVIEW360_OIDC_EXPIRE_MINUTES=30
export DOCREVIEW360_OIDC_TOKEN_ISSUER=docreview360-oidc.local
export DOCREVIEW360_OIDC_TOKEN_AUDIENCE=docreview360-oidc
# Treat any non-dev/test value (for example "production") as production.
# When set, missing secrets trigger a startup failure instead of a warning.
export DOCREVIEW360_ENV=dev
# Optional: DOCREVIEW360_SIGNATURE_SECRET for digital signatures
# Cookie-based auth requires an X-CSRF-Token header that matches the csrf_token cookie.
```

Run the `init` wizard or edit the file to change:

- `database`: `postgres`, `mysql` or `sqlite`
- `database_url`: SQLAlchemy connection string. If omitted when running
  `docreview360 init`, a sensible default is used for the selected backend
  (`postgres`, `mysql` or `sqlite`).
- `storage`: path or bucket for the object storage plugin
- `cms`: enable integrations such as `local` or `none`

After modifying the file, restart the server so the changes take effect.

### Enable PDF ingestion

DocReview360 can now ingest PDF uploads by converting them to plain text during
import. The converter is behind an explicit feature flag so existing
deployments stay unchanged. Enable it in `docreview360.yml`:

```yaml
documents:
  enable_pdf_ingestion: true
  allowed_mime_types:
    - application/pdf
    - text/markdown
    - application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

Install either `pdfminer.six` or `pypdf` in your environment so the default
adapter can extract text from the uploaded file. Integrators can replace the
built-in adapter or add additional ones by calling
`docreview360.documents.register_ingestion_pipeline()` with a custom function.

## 5. Explore the latest features

- **GraphQL read layer**: query projects and documents with `execute_query` in `docreview360.graphql_api`.
- **File storage plugin**: store files in any compatible object storage via `upload_file`.

Together these capabilities make it easier to integrate DocReview360 into your existing tools and workflows.

## 6. Example workflow

Below is a short end-to-end walkthrough using the CLI and projects page together:

1. Create a new project:
   ```bash
   docreview360 project create "Sample Project"
   ```
2. Upload a document and open it in the editor:
   ```bash
   docreview360 document add --project "Sample Project" docs/index.md
   ```
   Refresh your browser to see the file listed.
3. Request an approval from a team member:
   ```bash
   docreview360 approval request --project "Sample Project" --user alice
   ```
4. Once approved, export the document to PDF:
   ```bash
   docreview360 export pdf --project "Sample Project" --out output.pdf
   ```
5. Check the projects page to download the generated PDF and confirm the project status.
