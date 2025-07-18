# DocReview360

DocReview360 helps you organise documents, run simple approval workflows and keep track of your projects. The prototype ships with a small web API, a tiny frontend and a one-command CLI wizard. It is intentionally lightweight so you can explore the features and decide how they fit your own process.

## Prerequisites

Install [`uv`](https://github.com/astral-sh/uv) and [`Poetry`](https://python-poetry.org/) first:

```bash
pip install uv poetry
# or
pipx install uv poetry
```

## Quick start

1. **Create and activate a virtual environment**

   ```bash
   uv venv 3.12
   source 3.12/bin/activate
   ```

2. **Install dependencies**

   ```bash
   poetry install --with dev
   poetry sync --with dev
   uv pip install -r pyproject.toml --extra dev
   pre-commit install  # optional git hooks
   ```

3. **Configure the application**

   Define a few authentication secrets before running the wizard or the server:

   ```bash
   export DOCREVIEW360_SECRET_KEY=your-secret
   export DOCREVIEW360_ALGORITHM=HS256
   export DOCREVIEW360_ACCESS_EXPIRE_MINUTES=30
   export DOCREVIEW360_OIDC_SECRET_KEY=your-oidc-secret
   export DOCREVIEW360_OIDC_ALGORITHM=HS256
   export DOCREVIEW360_OIDC_EXPIRE_MINUTES=30
   # Optional: DOCREVIEW360_SIGNATURE_SECRET for digital signatures
   ```

   Then run the CLI wizard to set up your config:

   ```bash
   docreview360 init
   ```

   * Answer the prompts about your preferred database, editor, and other options.
   * The config is saved as `docreview360.yml` in your current directory.

4. **Start the backend API server**

   ```bash
   uvicorn docreview360.api:app --reload
   ```

   This launches the FastAPI backend on port 8000.

5. **Set up and run the React frontend (Node.js 18+ required)**

   ```bash
   cd frontend
   npm install --legacy-peer-deps
   npm run dev
   ```

   If you see `Cannot find module 'critters'`, just run `npm install --legacy-peer-deps` again.

6. **Open the app**

   Go to [http://localhost:3000/](http://localhost:3000/) in your browser.
   Sign in with `admin/admin` (default login).
   The frontend runs on port 3000 and communicates with the API at port 8000.

### GitHub Codespaces

Run the commands above from your Codespace terminal. When `uvicorn` is running,
forward port 8000 in the **Ports** panel and choose **Open in Browser** to access the login page.

A demo token is available with:
```bash
curl -X POST -d "username=alice&password=password" http://127.0.0.1:8000/oidc/token
```
Use the token in the `Authorization` header to call `/oidc/me`.

The API is a learning tool. Endpoints return dummy data but illustrate how projects, documents and approvals could work together. The frontend contains a login page, dashboard, project creation form, two editor pages and a review tracker table.

## Features

- In-memory storage for projects and documents
- Import/export of Markdown and DOCX files
- Search with saved queries
- Simple plugin system for editors and exporters
- Minimal authentication flow with a login form, dashboard and project creation page

Head over to the [documentation](https://example.com/docreview360) for a full tour of the API, CLI options and UI navigation tips. The
[architecture overview](docs/adr/0001-core-architecture.md) describes how the backend, frontend and future services fit together.

## Usage example

The following short session shows how a new user might work with DocReview360. After
starting the server open a second terminal and run:

```bash
# create a project and upload a document
docreview360 project create "My first project"
docreview360 document add --project "My first project" README.md

# request approval from a team member
docreview360 approval request --project "My first project" --user bob

# export the document to PDF using the default plugin
docreview360 export pdf --project "My first project" --out build/project.pdf
```

Reload the projects page and you will see the document listed with its approval
status. The quick turnaround gives a fresh-doc scent that highlights how light
the workflow can be.

## Deploy with Docker

Running the app inside containers is a handy way to share it on a server or your favourite cloud provider. The repository already contains a `Dockerfile` and a `docker-compose.yml` so you can start quickly.

See `docs/deployment.md` for platform-specific notes about environment variables and database setup on Render, Heroku, Fly.io and Railway.

1. **Build the image**
   ```bash
   docker build -t docreview360:latest .
   ```
2. **Launch the container on its own**
   ```bash
   docker run -d -p 8000:8000 docreview360:latest
   ```
   Visit <http://localhost:8000/> to confirm everything works.
3. **Run the full stack**
   ```bash
   docker compose up
   ```
   This command starts Postgres, OpenSearch, Redis and the DocReview360 services.

If you need to deploy on a remote host, tag the image with your registry name and push it:

```bash
docker tag docreview360:latest registry.example.com/docreview360:1.0.0
docker push registry.example.com/docreview360:1.0.0
```

Update your server or container orchestration tool to pull the new image and your DocReview360 instance will be online.

## Running Tests

1. **Install development dependencies and browsers**
   ```bash
   poetry install --with dev
   poetry sync --with dev
   uv pip install -r pyproject.toml --extra dev
   playwright install
   ```
2. **Run the full test suite**
   ```bash
   pre-commit run --all-files
   ```
   This runs Ruff, Black, MyPy and the unit tests.
3. **Run end-to-end tests only**
   ```bash
  pytest -m e2e
   ```
   The tests start a local server and drive a headless browser via Playwright.

## Git send-email hook

If you contribute via `git send-email` you can enable an optional validation
hook. Copy `scripts/sendemail-validate.sample` (also mirrored under
`.git/hooks/sendemail-validate.sample`) to `.git/hooks/sendemail-validate` and
make it executable:

```bash
cp scripts/sendemail-validate.sample .git/hooks/sendemail-validate
chmod +x .git/hooks/sendemail-validate
```

The hook relies on `codespell` and `gitlint` to check spelling and patch style before invoking a light-weight validator in `docreview360.git_hooks`. It also runs `gitlint --staged` to validate a patch series. Install these tools with `poetry install --with dev && poetry sync --with dev && uv pip install -r pyproject.toml --extra dev`.
