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
Then in a separate terminal set up and start the React UI (Node 18+):
```bash
npm install --legacy-peer-deps --prefix frontend  # install dependencies
npm run dev --prefix frontend
```
If the second command reports `Cannot find module 'critters'`, run the install step again to rebuild the `node_modules` folder.
Open `http://localhost:3000/` and sign in with `admin/admin` to reach the projects page.

### GitHub Codespaces

Run these commands in a Codespace terminal. When the server starts, expose port
8000 in the **Ports** panel and click **Open in Browser** to reach the login
page.

## 4. Explore the projects page

After logging in you're taken straight to the projects page. It lists your projects in a sortable table and includes a **Create New Project** button. Links to the editors, review tracker and interactive dashboard remain available from the navigation.

## 5. Next steps

Try importing a Markdown file, run a search query and create a dummy approval via the API. These simple examples show how projects, documents and approvals interact.
