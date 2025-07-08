# Getting Started

This short guide walks you through the first steps with DocuFlow. It assumes Python and Git are already installed.

## 1. Install DocuFlow

```bash
pip install -e .
pip install uvicorn
```
This installs the package in editable mode so local changes are picked up immediately and provides the web server used during development.

## 2. Configure the application

Run the interactive CLI wizard to generate a configuration file:
```bash
docuflow init
```
Answer the prompts about your preferred database, editor and other options. The resulting `docuflow.yml` sits in your working directory.

## 3. Start the development servers

First start the FastAPI backend:
```bash
uvicorn docuflow.api:app --reload
```
Then in a separate terminal start the React UI (Node 18+):
```bash
npm install --legacy-peer-deps --prefix frontend  # only once
npm run dev --prefix frontend
```
Open `http://localhost:3000/` and sign in with `admin/admin` to reach the React dashboard.

### GitHub Codespaces

Run these commands in a Codespace terminal. When the server starts, expose port
8000 in the **Ports** panel and click **Open in Browser** to reach the login
page.

## 4. Explore the dashboard

After logging in you land on a small dashboard. It lists links to the classic editor, the richer document editor, the review tracker and the project creation form. Widget counts and a compact project table give you a quick overview. The editors still do not save documents but show how future editing might look.

## 5. Next steps

Try importing a Markdown file, run a search query and create a dummy approval via the API. These simple examples show how projects, documents and approvals interact.
