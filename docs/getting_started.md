# Getting Started

This short guide walks you through the first steps with DocReview360. It assumes Python and Git are already installed.

## 1. Install DocReview360

```bash
pip install -e .
pip install uvicorn
```
This installs the package in editable mode so local changes are picked up immediately and provides the web server used during development.

## 2. Configure the application

Run the interactive CLI wizard to generate a configuration file:
```bash
docreview360 init
```
Answer the prompts about your preferred database, editor and other options. The resulting `docreview360.yml` sits in your working directory.

## 3. Start the development servers

First start the FastAPI backend:
```bash
uvicorn docreview360.api:app --reload
```
Then in a separate terminal set up and start the React UI (Node 18+).
Change into the `frontend` directory before running the commands:
```bash
cd frontend
npm install --legacy-peer-deps  # install dependencies
npm run dev
```
If the second command reports `Cannot find module 'critters'`, run the install step again to rebuild the `node_modules` folder.
Open `http://localhost:3000/` and sign in with `admin/admin` to reach the projects page.

### GitHub Codespaces

Run these commands in a Codespace terminal. When the server starts, expose port
8000 in the **Ports** panel and click **Open in Browser** to reach the login
page.

## 4. Run the tests

Install the development dependencies and Playwright browsers, then execute the suite:

```bash
pip install -e .[dev]
playwright install
pre-commit run --all-files
pytest -m e2e
```
The last command launches a headless browser to verify the workflow.

## 5. Explore the projects page

After logging in you're taken straight to the projects page. It lists your projects in a sortable table and includes a **Create New Project** button. Links to the editors, review tracker and interactive dashboard remain available from the navigation.

## 6. Next steps

Try importing a Markdown file, run a search query and create a dummy approval via the API. These simple examples show how projects, documents and approvals interact.
