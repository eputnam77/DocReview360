# /packaging-audit — Inspect Wheel/Sdist Contents

Audit the PyPI wheel, sdist, and Docker image contents to flag shipped tests,
placeholders, internal files, or runtime junk before release.

## Steps

### 1. Build wheel and sdist (dry run)

```bash
python -m build --no-isolation --outdir /tmp/dr360-build 2>&1 | tail -10
```

### 2. Inspect sdist contents

```bash
tar -tzf /tmp/dr360-build/docreview360-*.tar.gz | sort > /tmp/sdist-contents.txt
wc -l /tmp/sdist-contents.txt
grep -E '(test|_debug|\.pyc|audit\.log|\.db|\.lock|node_modules)' /tmp/sdist-contents.txt || echo "No junk found"
```

Flag any of the following as problems:
- `tests/` directory included in sdist (checklist 15a: exclude tests from sdist)
- `*.log`, `*.db`, `*.lock` files
- `node_modules/`, `.next/`, `frontend/pages__backup*`
- `_debug_test.py`, `ai-notes.md`, `push-after-fix.ps1`
- `artifacts/` directory

### 3. Inspect wheel contents

```bash
unzip -l /tmp/dr360-build/docreview360-*.whl | sort > /tmp/wheel-contents.txt
wc -l /tmp/wheel-contents.txt
grep -E '(test|_debug|\.pyc|node_modules|\.log|\.db)' /tmp/wheel-contents.txt || echo "No junk found"
```

### 4. Check package-data rules in pyproject.toml

Read `[tool.setuptools.package-data]` in `pyproject.toml`. The current wildcard
rule `"*" = ["*"]` is too broad (checklist 15a). It should be an explicit allowlist:
- `*.json` for schema/config files
- `*.html` for templates
- `*.onnx` for ML models (if bundled)
- `py.typed` marker

### 5. Docker image audit (if Docker is available)

```bash
docker build -t docreview360:audit-check . 2>&1 | tail -10
docker run --rm docreview360:audit-check find / -name "*.log" -o -name "*.db" 2>/dev/null | grep -v proc || true
docker run --rm docreview360:audit-check ls /app/tests 2>/dev/null && echo "WARN: tests/ present in image" || echo "ok: tests/ not in image"
```

### 6. Run placeholder scan

```bash
python scripts/check-placeholders.py 2>&1 | grep -E '(DRIFT|example\.com|GPL|TODO|FIXME)'
```

### 7. Report

Summarize:
- Sdist size and file count
- Wheel size and file count
- Any flagged junk files
- package-data rule assessment (wildcard vs explicit)
- Placeholder findings
- Recommended actions before release

## Key references

- `pyproject.toml` — `[tool.setuptools]` and `[tool.setuptools.package-data]`
- `MANIFEST.in` — sdist include/exclude rules (if present)
- `.dockerignore` — Docker build context exclusions
- Checklist item 15a — detailed packaging requirements
