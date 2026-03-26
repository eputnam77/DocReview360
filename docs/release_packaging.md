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

### Frontend assets are NOT included in the PyPI package

The Next.js application under `frontend/` is intentionally excluded from both the
wheel and the sdist. Operators who need the frontend must build and deploy it
separately:

```bash
cd frontend
npm install --legacy-peer-deps
npm run build
# Serve the static output or deploy to your CDN / container.
```

### What IS included in the wheel and sdist

The PyPI distribution contains only the Python backend package:

| Content | Notes |
|---|---|
| `src/docreview360/**/*.py` | All Python source modules |
| `src/docreview360/**/*.yaml` / `*.yml` | Configuration schemas and fixtures |
| `src/docreview360/**/*.json` | Feature-flag and quality-term data assets |
| `src/docreview360/**/*.html` | Jinja2 server-side templates |
| `src/docreview360/**/*.sql` | Schema migration scripts |
| `src/docreview360/**/*.md` | Embedded style guide text |
| `src/docreview360/py.typed` | PEP 561 type marker |
| `src/docreview360/ml/assets/*.onnx` | Packaged ONNX inference models |
| `README.md`, `LICENSE`, `pyproject.toml` | Top-level release metadata (sdist only) |

**Excluded from both artifacts:**

- `frontend/` — Next.js application (build separately)
- `tests/`, `docs/`, `scripts/`, `.dev/`, `.claude/` — dev/CI-only
- `*.db`, `*.sqlite` — runtime state
- `*.log`, `*.tmp` — transient files
- `*.lock`, `.env`, `.env.*` — environment-specific secrets / lock files
- `node_modules/`, `__pycache__/`, `*.pyc` — generated artefacts

### How to build and inspect artifacts

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
