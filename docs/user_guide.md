# User Guide

This walkthrough helps you explore DocReview360 from the perspective of a new user. You will log in, open the editor, add reviewers and approve documents. The guide also explains how to configure the application for different environments.

## 1. Access the projects page

1. Start the server with `uvicorn docreview360.api:app --reload`.
2. Open `http://127.0.0.1:8000/` in your browser.
3. Sign in with the credentials from your `docreview360.yml` file (the defaults are `admin/admin`).
4. The projects page greets you and provides links to the editor and API docs.

## 2. Open the document editor

1. From the projects page click **Editor**.
2. A rich text field appears where you can type or paste content. This preview uses the Tiptap editor.
3. Edits are currently stored in memory to show how future versions might behave.

### Changing the editor

The configuration file contains an `editor` setting. Supported values include `tiptap`, `toast` and `word`.

1. Run `docreview360 init` to regenerate the file or edit it manually.
2. Set `editor: toast` (or another option) and restart the server.
3. The next time you open the editor the new tool loads.

Optional TipTap extensions can be discovered and managed at runtime. See
the [plugin guide](tiptap-plugins.md) for details on registering or disabling
wrappers.

## 3. Add a reviewer and request approval

1. Use the API endpoint `POST /approvals` to create an approval request. Provide the document ID and the reviewer name.
2. The reviewer can fetch requests with `GET /approvals`.
3. When they are satisfied they call `PUT /approvals/{approval_id}` with the new state `approved`.

## 4. Configure your environment

DocReview360 stores its settings in `docreview360.yml`. Run the `init` wizard or edit the file to change:

- `database`: `postgres`, `mysql` or `sqlite`
- `database_url`: SQLAlchemy connection string
- `storage`: path or bucket for the object storage plugin
- `cms`: enable integrations such as `local` or `none`

After modifying the file, restart the server so the changes take effect.

## 5. Explore the latest features

- **GraphQL read layer**: query projects and documents with `execute_query` in `docreview360.graphql_api`.
- **File storage plugin**: store files in any compatible object storage via `upload_file`.

Together these capabilities make it easier to integrate DocReview360 into your existing tools and workflows.

## 6. Example workflow

Below is a short end-to-end walkthrough using the CLI and projects page together:

1. Create a new project:
   ```bash
   docreview360 project create "Demo Project"
   ```
2. Upload a document and open it in the editor:
   ```bash
   docreview360 document add --project "Demo Project" docs/index.md
   ```
   Refresh your browser to see the file listed.
3. Request an approval from a team member:
   ```bash
   docreview360 approval request --project "Demo Project" --user alice
   ```
4. Once approved, export the document to PDF:
   ```bash
   docreview360 export pdf --project "Demo Project" --out demo.pdf
   ```
5. Check the projects page to download the generated PDF and confirm the project status.

