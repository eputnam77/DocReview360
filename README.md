# DocReview360

Lightweight document workflows—CLI, API, and React UI in one repo.

**DocReview360** lets teams organize files, route them through quick approval steps, and track status at a glance. The prototype ships with:

* a FastAPI backend
* a minimal React/Next.js frontend
* a single‑command CLI wizard (`docreview360 init`)

so you can test everything locally and decide how it fits your process.

---

## ✨ Quick install (recommended)

We use **pipx** for global tool shims, **uv** for ultra‑fast Python/venv work, and **Poetry ≥ 1.8** for lock‑file sync.

```bash
# 0. One-time setup: Python & pipx -------------------------------------------------
python --version                # confirm Python ≥3.11

# Debian / Raspberry Pi OS
sudo apt update
sudo apt install pipx
pipx ensurepath                # add pipx to PATH
source ~/.bashrc               # reload sheel so PATH is updated

# Windows
python -m pip install --user pipx
python -m pipx ensurepath       # restart shell if PATH changes

# All platforms
pipx install uv                 # fast resolver, venv mgr, lockfile, tool runner

# 1. Clone project ---------------------------------------------------------------
git clone https://github.com/eputnam77/NovelScriptCLI.git
cd NovelScriptCLI

# 2. Create and activate venv (Python 3.13) --------------------------------------
uv python install 3.13.0        # Download if not present
uv venv --python 3.13.0

# Activate the venv:
#   On Mac/Linux:
source .venv/bin/activate
#   On Windows:
.venv\Scripts\activate

# 3. Install project + extras (dev, test, security) ------------------------------
uv pip install -e ".[dev,test,security]"
# (Optional) Allow prerelease dependencies if needed:
# uv pip install -e ".[dev,test,security]" --prerelease=allow

# 4. (Optional) Upgrade pip and pre-commit inside the venv -----------------------
uv pip install --upgrade pip pre-commit

# 5. Install Git hooks -----------------------------------------------------------
pre-commit install
```

DocReview360 ships with the built-in ``sandbox`` signature provider enabled for
local development. Set ``SIGNATURE_PROVIDER=documenso`` (or provide a fallback
list) when you want to use Documenso's hosted service—remember that Documenso
will deliver callbacks to ``POST /hooks/documenso``.

*(Need a plain‑Python fallback? See “🐍 Virtual‑env fallback” below.)*

---

## 🔑 Configure secrets

```bash
cp .env.example .env           # template included
# or export variables directly:

# Unix/Linux/macOS (bash/zsh):
export DOCREVIEW360_SECRET_KEY=your-secret
export DOCREVIEW360_ALGORITHM=HS256
export DOCREVIEW360_ACCESS_EXPIRE_MINUTES=30
export DOCREVIEW360_OIDC_SECRET_KEY=your-oidc-secret
export DOCREVIEW360_OIDC_ALGORITHM=HS256
export DOCREVIEW360_OIDC_EXPIRE_MINUTES=30

# Windows PowerShell:
$env:DOCREVIEW360_SECRET_KEY="your-secret"
$env:DOCREVIEW360_ALGORITHM="HS256"
$env:DOCREVIEW360_ACCESS_EXPIRE_MINUTES="30"
$env:DOCREVIEW360_OIDC_SECRET_KEY="your-oidc-secret"
$env:DOCREVIEW360_OIDC_ALGORITHM="HS256"
$env:DOCREVIEW360_OIDC_EXPIRE_MINUTES="30"

# Optional:
# DOCREVIEW360_SIGNATURE_SECRET  (digital signatures)
# SIGNATURE_PROVIDER=sandbox  (default order: sandbox → Documenso → local; Documenso will send webhooks to /hooks/documenso)
# NEXT_PUBLIC_API_BASE=http://localhost:8000  (frontend → backend, leave blank to use dashboard host)
# DOCREVIEW360_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000  (frontend host(s) allowed by CORS)
```

Run the CLI wizard to generate `docreview360.yml`:

```bash
docreview360 init
```

To copy data between environments use the migration command:

```bash
docreview360 migrate export backup.gz
docreview360 migrate import backup.gz
```

---

## 🚀 Run the backend API

```bash
# Ensure you're in the project root and virtual environment is activated
cd DocReview360
# source .venv/bin/activate  # On Mac/Linux
# .venv\Scripts\activate     # On Windows

# Start the backend server on macOS/Linux
uvicorn docreview360.api:app --reload --port 8000
```

```powershell
# Start the backend server on Windows PowerShell (auto-loads .env when present)
pwsh -File scripts/windows/start-backend.ps1
```

**Important:** The backend server must be running for the frontend to work properly, especially the document checker that integrates with GovDocVerify.

**Prerequisites:** Ensure you've configured the environment variables (see "🔑 Configure secrets" section above) or have a `.env` file in the project root.

- **API Documentation:** FastAPI auto‑generates interactive docs at http://localhost:8000/docs
- **Health Check:** Test the server at http://localhost:8000/health
- **GovDocVerify Integration:** The document checker requires this backend to process files

Pass secrets on the command line when you do not want to persist them:

```powershell
pwsh -File scripts/windows/start-backend.ps1 `
  -SecretKey "your-secret" `
  -AccessExpireMinutes 60
```

The script falls back to the development defaults from `src/docreview360/auth.py` when
variables are absent and automatically reads overrides from a `.env` file in the project
root. The `--reload` flag auto‑reloads on code changes—handy in development.

---

## 🖥️ Run the React frontend (Node 18+)

```bash
# Ensure you are at DocReview360/DocReview360/frontend
cd frontend
npm install --legacy-peer-deps

# Create environment file for frontend-backend communication
# Choose the command for your operating system:

# Windows PowerShell (recommended for Windows):
Set-Content -Path .env.local -Value "NEXT_PUBLIC_API_BASE=http://localhost:8000"

# Windows Command Prompt:
# echo NEXT_PUBLIC_API_BASE=http://localhost:8000 > .env.local

# Unix/Linux/macOS (bash/zsh):
# cat > .env.local << 'EOF'
# # Backend API base URL (required for GovDocVerify integration)
# NEXT_PUBLIC_API_BASE=http://localhost:8000
# EOF

# Universal alternative (works on all platforms):
# echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local

npm run dev
```

Open [http://localhost:3000/](http://localhost:3000/) and log in with one of the test accounts:

**Admin Access:**
- Username: `alice`
- Password: `password`
- Roles: user, admin (Full administrative access)

**Non-Admin Access:**
- Username: `bob`
- Password: `password`
- Roles: auditor (Limited access, no admin privileges)

**Note:** The frontend requires the backend server to be running for full functionality (especially the document checker). Ensure the backend is started first.

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

## 🧪 Quality Checks & Testing Guide

This project uses a multi-tool testing pipeline to ensure code quality, formatting, type safety, security, and robustness. Below is the full suite of commands and best practices for local development and CI validation.

---

### 1. ✅ Lint, Format, and Static Type Checks

**Defined in `.pre-commit-config.yaml`** and run automatically before every commit (after running `pre-commit install`):

* **Ruff:** Linting and formatting for Python code (also handles import sorting)
* **Black:** Auto-formats Python code to a consistent style
* **Mypy:** Static type checking
* **Bandit:** Python code security scanning (see below for details)
* **mdformat:** Markdown linting and formatting, with Ruff rules
* **Codespell:** Checks for common spelling mistakes in code, comments, and docs

**To run all checks across the codebase:**

```bash
pre-commit install           # (First time only) Installs pre-commit hooks
pre-commit run --all-files   # Run all checks across the codebase
```

> **Tip:** This is the recommended first step before committing or pushing code.

---

### 2. ✅ Unit Tests with Coverage

Run the full test suite with code coverage reporting using pytest:

```bash
pytest --cov=src
```

* Replace `src` with your module's directory if different.
* Coverage results can be uploaded to Codecov or other CI tools.

---

### 3. 🔡 Spellchecking

Run [Codespell](https://github.com/codespell-project/codespell) to catch common typos in code, comments, and documentation:

```bash
codespell src tests docs
```

> **Note:** Codespell is also included in pre-commit, so this check runs automatically before each commit.

---

### 4. 📚 Docstring Formatting (Optional)

[docformatter](https://github.com/PyCQA/docformatter) ensures all Python docstrings follow [PEP 257](https://peps.python.org/pep-0257/) conventions.

```bash
docformatter -r src/
```

* Recommended for teams/projects that enforce strict docstring style.

---

### 5. 🛡️ Security Scanning

Run security scanners to identify vulnerabilities:

* **Bandit:** Scans Python source code for security issues

  ```bash
  bandit -r src -lll --skip B101
  ```

  * `-r src`: Recursively scans the `src` directory
  * `-lll`: Only high-severity issues
  * `--skip B101`: Skip assert statement warnings

* **pip-audit:** Checks installed dependencies for known security vulnerabilities

  ```bash
  pip-audit
  pip-audit -r requirements.txt
  ```

* **Safety (Optional):** Another dependency vulnerability scanner

  ```bash
  safety check
  ```

  * Not required if using pip-audit, but can be added for redundancy.

---

### 6. 🧬 Mutation Testing (Optional)

[Mutmut](https://mutmut.readthedocs.io/en/latest/) tests your suite’s effectiveness by making small code changes ("mutations") and checking if your tests catch them.

```bash
mutmut run --paths-to-mutate src
mutmut results
```

* Use this occasionally or in CI for robust projects.
* Mutation testing can be time-consuming.

---

### 7. 📦 Suggested Workflow

```bash
pre-commit run --all-files        # Lint, format, type check, spellcheck, markdown, security
pytest --cov=src                  # Unit tests with coverage
bandit -r src -lll --skip B101    # Security scan (code)
python scripts/run-pip-audit.py   # Security scan (dependencies) - handles local packages
codespell src tests docs          # Spell check (if not running in pre-commit)
docformatter -r src/              # (Optional) Docstring formatting
mutmut run --paths-to-mutate src  # (Optional) Mutation testing
mutmut results
```

---

### 8. 📋 Quick Reference Table

| Tool         | Purpose                     | Command Example                               |
| ------------ | --------------------------- | --------------------------------------------- |
| Ruff         | Lint/format Python code     | `pre-commit run --all-files`                  |
| Black        | Code formatter              | `pre-commit run --all-files`                  |
| Mypy         | Static type checking        | `pre-commit run --all-files`                  |
| Bandit       | Security (code)             | `bandit -r src -lll --skip B101`              |
| pip-audit    | Security (dependencies)     | `python scripts/run-pip-audit.py` / `pip-audit -r requirements.txt` |
| Codespell    | Spell check                 | `codespell src tests docs`                    |
| mdformat     | Markdown formatting/linting | `pre-commit run --all-files`                  |
| docformatter | Docstring style (optional)  | `docformatter -r src/`                        |
| Mutmut       | Mutation test (optional)    | `mutmut run --paths-to-mutate src`            |
| Pytest       | Unit tests/coverage         | `pytest --cov=src`                            |
| Safety       | Security (deps, optional)   | `safety check`                                |

---

### About the requirements files

`requirements*.txt` are generated for legacy tooling; `poetry sync` (or `pip install -e ".[dev]"`) remains the canonical way to keep dependencies in lock‑step with **pyproject.toml**.

---

### GitHub Codespaces

Run the commands above from your Codespace terminal. When `uvicorn` is running,
forward port 8000 in the **Ports** panel and choose **Open in Browser** to access the login page.

A test token is available with:
```bash
curl -X POST -d "username=alice&password=password" http://127.0.0.1:8000/oidc/token
```
Use the token in the `Authorization` header to call `/oidc/me`.

**Test Users:**
- **Admin:** `alice` / `password` (Has admin privileges)
- **Non-Admin:** `bob` / `password` (Has auditor role with limited access)

The API is a learning tool. Endpoints return dummy data but illustrate how projects, documents and approvals could work together. The frontend contains a login page, dashboard, project creation form, two editor pages and a review tracker table.

## Features

- In-memory storage for projects and documents
- Import/export of Markdown and DOCX files
- Search with saved queries
- Simple plugin system for editors and exporters
- Minimal authentication flow with a login form, dashboard and project creation page

**Test Users:**
The system comes with two predefined test users for development and testing:

1. **Alice** (`alice` / `password`) - Has admin privileges with full access to all features
2. **Bob** (`bob` / `password`) - Has auditor role with limited access for testing role-based permissions

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

Running the app inside containers is a handy way to share it on a server or your favorite cloud provider. The repository already contains a `Dockerfile` and a `docker-compose.yml` so you can start quickly.

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

## License

DocReview360 is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html). See the LICENSE file for full details.
