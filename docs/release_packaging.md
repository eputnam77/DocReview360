# Release Packaging

This guide covers supply-chain packaging steps for DocReview360 release artifacts.

## Docker OCI metadata labels

The `Dockerfile` includes OCI labels using these build args:

- `VERSION`
- `VCS_REF`
- `BUILD_DATE`
- `IMAGE_SOURCE`
- `IMAGE_URL`

Example build:

```bash
docker build \
  --build-arg VERSION=0.1.2 \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t ghcr.io/<org>/docreview360:0.1.2 .
```

## Publish container digest in release notes

After pushing images, capture the immutable digest and generate release notes:

```bash
python scripts/generate_release_notes.py \
  --version 0.1.2 \
  --image-digest ghcr.io/<org>/docreview360@sha256:<digest>
```

The script writes `dist/release/RELEASE_NOTES.md` by default and includes each provided digest in the "Container Images" section.

## Sign and verify release tags

Create a signed annotated tag (GPG):

```bash
python scripts/sign_release_tag.py \
  --tag v0.1.2 \
  --message "DocReview360 v0.1.2"
```

(Optional) sign with an explicit key id:

```bash
python scripts/sign_release_tag.py \
  --tag v0.1.2 \
  --message "DocReview360 v0.1.2" \
  --key-id <GPG_KEY_ID>
```

Verify the signature before publishing release assets:

```bash
python scripts/verify_release_tag_signature.py --tag v0.1.2
```

Sigstore users can substitute an equivalent tag-signing + verification process, but signature verification must be run before publishing.

## PyPI Wheel and Sdist

### Frontend build assets are included in the wheel

The base PyPI wheel is the lightweight web app, not a frontend-source archive.
Release builds copy the first available built frontend artifact from
`frontend/out`, `frontend/.next/standalone`, or `frontend/.next` into
`docreview360/frontend_static`. The source distribution excludes the repository
`frontend/` tree. Build the frontend before creating release artifacts:

```bash
cd frontend
npm install --legacy-peer-deps
npm run build
cd ..
python -m build
```

`docreview360 frontend extract` is retained as an inspection/support command for
the packaged build asset. It is not the normal IT setup path.

### What IS included in the wheel and sdist

The PyPI distribution contains the core Python web app plus the packaged
frontend build asset:

| Content | Notes |
|---|---|
| `src/docreview360/**/*.py` | All Python source modules |
| `src/docreview360/**/*.json` | Runtime JSON assets such as quality terms and watchlists |
| `src/docreview360/**/*.html` | Jinja2 server-side templates |
| `src/docreview360/**/*.sql` | Schema migration scripts |
| `src/docreview360/**/*.tf` | IaC template assets packaged with the backend |
| `src/docreview360/py.typed` | PEP 561 type marker |
| `docreview360/frontend_static/**` | Bundled frontend build asset exposed via `docreview360 frontend extract` |
| `README.md`, `LICENSE`, `pyproject.toml` | Top-level release metadata (sdist only) |

**Excluded generated/runtime artefacts:**

- `tests/`, `docs/`, `scripts/`, `.claude/` — dev/CI-only
- `frontend/`, `frontend/node_modules/`, `frontend/.next/`, `frontend/.tmp/` - frontend source and generated caches in sdist
- `*.db`, `*.sqlite` — runtime state
- `*.log`, `*.tmp` — transient files
- `*.lock`, `.env`, `.env.*` — environment-specific secrets / lock files
- `node_modules/`, `__pycache__/`, `*.pyc` — generated artefacts
- `*.onnx`, `*.pt`, `*.pkl` - optional ML artifacts

### How to build and inspect artifacts

### Alpha release flow

Use a PEP 440 pre-release version for alpha uploads, for example `0.1.3a0`.
Users installing from PyPI will typically need `--pre` until the first stable
release is published.

```bash
python -m pip install ".[release]"
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python -m twine upload --repository testpypi dist/*.whl dist/*.tar.gz
```

After validating the TestPyPI install path, upload the same artifacts to PyPI:

```bash
python -m twine upload dist/*.whl dist/*.tar.gz
```

**Build:**

```bash
# Requires the `build` package: pip install build
python -m build             # produces dist/*.whl and dist/*.tar.gz
python -m build --sdist     # sdist only
python -m build --wheel     # wheel only
```

**Inspect wheel contents:**

```bash
python -c "
import zipfile, sys
with zipfile.ZipFile(sys.argv[1]) as zf:
    for name in sorted(zf.namelist()):
        print(name)
" dist/docreview360-*.whl
```

**Inspect sdist contents:**

```bash
tar -tvf dist/docreview360-*.tar.gz | sort
```

**Verify no junk files shipped:**

```bash
python -c "
import zipfile, sys
bad = [n for n in zipfile.ZipFile(sys.argv[1]).namelist()
       if any(n.endswith(e) for e in ('.db','.sqlite','.log','.tmp','.pyc'))]
print('Unexpected files:', bad or 'none')
" dist/docreview360-*.whl
```
