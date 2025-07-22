# Getting Started

This short guide walks you through the first steps with DocReview360. It assumes Python and Git are already installed.

## Prerequisites

Install [`uv`](https://github.com/astral-sh/uv) and [`Poetry`](https://python-poetry.org/) with `pip` or `pipx`:

```bash
pip install --upgrade pip
pip install uv poetry
# or
pipx install uv poetry
```

1. **Create and activate a virtual environment**

   ```bash
   uv venv 3.12
   source 3.12/bin/activate
   ```

2. **Install the backend and web server**

   ```bash
   poetry install --with dev
   poetry sync --with dev
   uv pip install -r pyproject.toml --extra dev
   pre-commit install  # optional git hooks
   ```

3. **Configure the application**

   Export the authentication secrets before running the wizard:

   ```bash
   export DOCREVIEW360_SECRET_KEY=your-secret
   export DOCREVIEW360_ALGORITHM=HS256
   export DOCREVIEW360_ACCESS_EXPIRE_MINUTES=30
   export DOCREVIEW360_OIDC_SECRET_KEY=your-oidc-secret
   export DOCREVIEW360_OIDC_ALGORITHM=HS256
   export DOCREVIEW360_OIDC_EXPIRE_MINUTES=30
   # Optional: DOCREVIEW360_SIGNATURE_SECRET for digital signatures
   ```

   When testing, refer to secrets in `tests/conftest.py`.
   Run the CLI wizard to set up your config:

   ```bash
   docreview360 init
   ```

   * Answer the prompts about your preferred database, editor, and other options.
   * The config is saved as `docreview360.yml` in your current directory.

5. **Start the backend API server**

   ```bash
   uvicorn docreview360.api:app --reload
   ```

   This launches the FastAPI backend on port 8000.

6. **Set up and run the React frontend (Node.js 18+ required)**

   ```bash
   cd frontend
   npm install --legacy-peer-deps
   npm run dev
   ```

   If you see `Cannot find module 'critters'`, just run `npm install --legacy-peer-deps` again.

7. **Open the app**

   Go to [http://localhost:3000/](http://localhost:3000/) in your browser.
   Sign in with `admin/admin` (default login).
   The frontend runs on port 3000 and communicates with the API at port 8000.

## GitHub Codespaces

Run these commands in a Codespace terminal. When the server starts, expose port
8000 in the **Ports** panel and click **Open in Browser** to reach the login
page.

## Explore the projects page

After logging in you're taken straight to the projects page. It lists your projects in a sortable table and includes a **Create New Project** button. Links to the editors, review tracker and interactive dashboard remain available from the navigation.

## Next steps

Try importing a Markdown file, run a search query and create a dummy approval via the API. These simple examples show how projects, documents and approvals interact.
