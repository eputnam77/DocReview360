# /docs-drift — Documentation Drift Check

Check README.md, docs/, pyproject.toml, env var docs, and Docker docs for
mismatched commands, versions, URLs, and undocumented environment variables.

## Steps

1. **Run the drift checker script:**
   ```bash
   python scripts/check-docs-drift.py
   ```
   Review the output. Each `DRIFT:` line is a potential inconsistency.

2. **Check version consistency.** The authoritative version is in `pyproject.toml`.
   Confirm it appears consistently in:
   - `README.md` (release notes, version badge, or Quick Start)
   - `CHANGELOG.md` (if it exists)
   - Helm `Chart.yaml` and `values.yaml`

3. **Check env var coverage.** For each `DOCREVIEW360_*` variable in
   `src/docreview360/config.py` and `environment.py`, confirm it appears in at
   least one of: `README.md`, `docs/deployment.md`, `docs/configuration.md`, or
   `CLAUDE.md`.

4. **Check port references.** Backend must use port 8000; frontend port 3000.
   Look for stray port references in `docs/`, `nginx/nginx.conf`,
   `docker-compose.prod.yml`, and Helm `values.yaml`.

5. **Check Docker consistency.** The Python version in `Dockerfile` must match
   `requires-python` in `pyproject.toml` (currently `>=3.11,<3.13`).

6. **Check install command consistency.** `CLAUDE.md` is the authoritative source
   for local dev setup. Verify `README.md` Quick Start section matches.

7. **Report findings.** List each discrepancy with file path and recommended fix.
   Do not auto-fix — present findings for human review.

## Key files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Authoritative version + Python constraint |
| `README.md` | User-facing quick start |
| `CLAUDE.md` | Dev setup (authoritative for local commands) |
| `docs/deployment.md` | Deployment guide |
| `docs/air_gap_deployment.md` | Air-gap guide |
| `src/docreview360/config.py` | All env vars with `_ENV_OVERRIDES` |
| `Dockerfile` | Python base image version |
| `docker-compose.prod.yml` | Production stack ports and env vars |
