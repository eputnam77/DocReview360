# DocReview360

Lightweight document workflows—CLI, API, and React UI in one repo.

**DocReview360** lets teams organise files, route them through quick approval steps, and track status at a glance. The prototype ships with:

* a FastAPI backend
* a minimal React/Next.js frontend
* a single‑command CLI wizard (`docreview360 init`)

so you can test everything locally and decide how it fits your process.

---

## ✨ Quick install (recommended)

We use **pipx** for global tool shims, **uv** for ultra‑fast Python/venv work, and **Poetry ≥ 1.8** for lock‑file sync.

```bash
# 0  One‑time per machine ───────────────────────────────────────────────
python3 -m pip install --user pipx
python3 -m pipx ensurepath                 # restart shell if PATH changed

pipx install uv                            # uv CLI & resolver :contentReference[oaicite:0]{index=0}
pipx install poetry                        # Poetry ≥1.8 (sync cmd) :contentReference[oaicite:1]{index=1}

# 1  Per project ────────────────────────────────────────────────────────
git clone https://github.com/eputnam77/DocReview360.git
cd DocReview360

# 2  Create & activate .venv (CPython 3.13) -----------------------------
uv python install 3.12.0                   # downloads if missing :contentReference[oaicite:2]{index=2}
uv venv --python 3.12.0                    # writes .venv/ by default
source .venv/bin/activate                  # Windows: .venv\Scripts\activate

# 3  Install deps at uv speed ------------------------------------------
poetry config installer.executable uv      # once per machine
poetry sync --with dev                     # mirrors poetry.lock (dev extras)

# 4  Dev helpers --------------------------------------------------------
pre-commit install                         # Git hooks
```

*(Need a plain‑Python fallback? See “🐍 Virtual‑env fallback” below.)*

---

## 🔑 Configure secrets

```bash
cp .env.example .env           # template included
# or export variables directly:
export DOCREVIEW360_SECRET_KEY=your-secret
export DOCREVIEW360_ALGORITHM=HS256
export DOCREVIEW360_ACCESS_EXPIRE_MINUTES=30
export DOCREVIEW360_OIDC_SECRET_KEY=your-oidc-secret
export DOCREVIEW360_OIDC_ALGORITHM=HS256
export DOCREVIEW360_OIDC_EXPIRE_MINUTES=30
# Optional:
# DOCREVIEW360_SIGNATURE_SECRET  (digital signatures)
# NEXT_PUBLIC_API_BASE=http://localhost:8000  (frontend → backend)
```

Run the CLI wizard to generate `docreview360.yml`:

```bash
docreview360 init
```

---

## 🚀 Run the backend API

```bash
uvicorn docreview360.api:app --reload --port 8000
# FastAPI auto‑generates interactive docs at /docs :contentReference[oaicite:3]{index=3}
```

The `--reload` flag auto‑reloads on code changes—handy in dev.

---

## 🖥️ Run the React frontend (Node 18+)

```bash
cd frontend
npm install --legacy-peer-deps
cp .env.example .env           # set NEXT_PUBLIC_API_BASE if backend separate
npm run dev
```

Open [http://localhost:3000/](http://localhost:3000/) and log in with **admin / admin**.

---

## 🧪 Quality checks

```bash
pre-commit run --all-files
pytest --cov=src
```

---

## 🐍 Virtual‑env fallback (no uv)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install poetry
poetry install --with dev --sync   # --sync flag still works but is deprecated :contentReference[oaicite:5]{index=5}
```

---

### About the requirements files

`requirements*.txt` are generated for legacy tooling; `poetry sync` (or `pip install -e ".[dev]"`) remains the canonical way to keep dependencies in lock‑step with **pyproject.toml**.

---

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
