# Usage Scenarios

The following examples show how DocReview360 could fit into day‑to‑day work. The prototype is intentionally small but these flows highlight what is possible.

## Collaborating on a draft
1. A user imports a Markdown file using `POST /documents/import`.
2. They edit the document in the web editor and save changes with `PUT /documents/{doc_id}`.
3. A search query helps them find similar documents for reference.
4. Once happy, they start a workflow and assign a reviewer.
5. The reviewer receives an approval request and updates the state through the API.

## Managing project priorities
1. Create a project with `POST /projects`.
2. Use `PUT /projects/{project_id}/priority` to set its priority.
3. Temporarily assign another user if someone is away.
4. Search for documents related to the project to track progress.

These scenarios illustrate the interplay between projects, documents and approvals. Even though the data lives in memory, the flow mirrors a real system and helps you understand how everything connects.
