# DocReview360

DocReview360 is a document review app with a FastAPI backend, a React frontend, and a CLI. It helps teams route documents through review, approvals, and audit logging.

## Alpha release

The current PyPI release is an alpha package. It includes the Python backend and the `docreview360` CLI. It does not include the Next.js frontend.

```bash
python -m pip install --pre docreview360
python -m pip install --pre "docreview360[fedstylevalidator]"
```

Use the `fedstylevalidator` extra when you want the published Federal Style Validator package from PyPI.

## Quick start

Requirements:

- Python 3.11 or 3.12
- Node 18+ for the frontend
- `uv` recommended for environment management

Backend:

```bash
git clone https://github.com/eputnam77/DocReview360.git
cd DocReview360
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev,test,security]"
DOCREVIEW360_ENV=dev python -m uvicorn docreview360.api:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install --legacy-peer-deps
printf "NEXT_PUBLIC_API_BASE=http://localhost:8000\n" > .env.local
npm run dev
```

Windows PowerShell:

```powershell
uv venv --python 3.12
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,test,security]"
$env:DOCREVIEW360_ENV="dev"
python -m uvicorn docreview360.api:app --reload --host 0.0.0.0 --port 8000
```

Log in with `alice` / `password` or `bob` / `password` in local development.

For the full setup flow, see [docs/getting_started.md](docs/getting_started.md).

## Install options

Install from source for full-stack development:

```bash
uv pip install -e ".[dev,test,security]"
```

Install the alpha backend package from PyPI:

```bash
python -m pip install --pre docreview360
```

Need a plain `venv` flow instead of `uv`? See [docs/getting_started.md](docs/getting_started.md).

## Configuration

Keep the README focused. Use the docs for configuration detail.

- Environment variables: [docs/environment_variables.md](docs/environment_variables.md)
- Settings reference: [docs/settings.md](docs/settings.md)
- Deployment guide: [docs/deployment.md](docs/deployment.md)
- CLI reference: [docs/cli.md](docs/cli.md)

Run the setup wizard to generate `docreview360.yaml`:

```bash
docreview360 init
```

## Testing and quality

Quality checks, security scans, and E2E commands now live in one place:

- [docs/testing_and_quality.md](docs/testing_and_quality.md)

## Product notes

- Existing endpoints remain available without a prefix.
- Versioned aliases are supported at `/api/v1/*`.
- AI assistance is optional.
- The app is not legal advice and is not positioned as a certified regulatory compliance system.

Performance baseline details live in [docs/performance_baseline.md](docs/performance_baseline.md).

## Packaging and release

Release packaging details live in [docs/release_packaging.md](docs/release_packaging.md).

## More docs

- API overview: [docs/api_overview.md](docs/api_overview.md)
- Developer guide: [docs/developer.md](docs/developer.md)
- E2E guide: [docs/e2e.md](docs/e2e.md)
- Federal Style Validator: [docs/federal-style-validator.md](docs/federal-style-validator.md)
- Operations and deployment: [docs/deployment.md](docs/deployment.md)

## Governance

- Terms: [TERMS.md](TERMS.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- License: [LICENSE](LICENSE)
