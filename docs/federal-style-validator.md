# Federal Style Validator Integration

Federal Style Validator (FSV) is a separate MIT-licensed package that provides
authoritative plain-language, readability, regulatory-compliance, and style
validation for U.S. Federal documents. DocReview360 is an **integration host**:
it proxies requests to FSV, caches results in its database, and renders FSV
output in its UI.

## Architecture

```
FSV service (separate process / container)
  └── POST /validate
  └── POST /quality
  └── POST /regulatory-check
  └── GET  /health

DocReview360 backend
  └── POST /documents/validate     → asyncio.gather over preflight + quality + regulatory
  └── POST /documents/preflight    → proxies to FSV /validate, falls back to internal
  └── POST /ml/quality             → proxies to FSV /quality, falls back to internal
  └── POST /ai/regulatory-check   → proxies to FSV /regulatory-check, falls back to internal
  └── GET  /fsv/status             → health probe (2-second timeout)
  └── GET  /admin/settings/fsv-url → returns configured URL
  └── PUT  /admin/settings/fsv-url → set/clear URL (admin only)

DocReview360 frontend
  └── TipTap editor (on-save validation pill + sidebar summary)
  └── Tools → Checker page
  └── Project view (quality badge, document scores table)
```

## Configuration

### Option 1 — Environment variable (recommended for production)

```bash
FEDERAL_STYLE_VALIDATOR_URL=http://fsv-service:8080
```

Set this in your `.env`, `docker-compose.yml`, or deployment environment. The
environment variable takes precedence over the UI-configured URL.

### Option 2 — Admin UI

1. Log in as an admin and go to **Tools**.
2. Expand **Federal Style Validator — Service URL**.
3. Enter the FSV base URL (e.g. `http://localhost:8080`) and click **Save**.

The URL is stored in `settings.yaml` and read by `fsv_proxy.get_fsv_url()`.
The environment variable always overrides the settings-file value.

### Fallback behaviour

When no FSV URL is configured (neither env var nor settings), all proxy
endpoints fall back to DocReview360's built-in implementations:

| Endpoint | Internal fallback |
|----------|------------------|
| `/documents/preflight` | `doc_validation.run_preflight_checks()` |
| `/ml/quality` | `ml/onnx_infer.py` ONNX quality model |
| `/ai/regulatory-check` | `regulatory.run_regulatory_check()` |

The response always includes `"source": "fsv"` or `"source": "internal"` so
callers can distinguish.

## Check categories

Administrators can enable or disable individual FSV check categories via:

```
GET  /admin/settings/fsv-checks   → returns {checks: {...}, categories: [...]}
PUT  /admin/settings/fsv-checks   → body: {checks: {"passive_voice": false, ...}}
```

Supported categories:

| ID | Description |
|----|-------------|
| `passive_voice` | Passive voice detection |
| `acronym_validation` | Undefined acronym detection |
| `heading_structure` | Heading hierarchy validation |
| `readability` | Readability / plain-language scoring |
| `regulatory` | Regulatory clause matching (21 CFR, ISO, IEC, EU MDR/IVDR) |
| `plain_language` | Plain language grade scoring |

Disabled categories are skipped even when on-save validation is active. The
settings UI is on the Tools page (admin only, visible when FSV is enabled).

## On-save auto-validation

The TipTap editor calls `POST /documents/preflight` after each successful save
(fire-and-forget, non-blocking). The result is stored in the
`DocumentQualityScore` table and displayed as a green/amber/red pill in the
editor toolbar and in the sidebar **Validation Summary** section.

Toggle on/off via:
- **UI**: Tools page → Federal Style Validator — On-Save Validation
- **API**: `GET/PUT /admin/settings/auto-validation`
- **Code**: `settings_manager.update_setting("auto_save_validation", bool)`

## Installing FSV as a dependency

FSV is optional. To install it alongside DocReview360:

```bash
# Using the optional extras group (recommended)
uv pip install -e ".[fedstylevalidator]"

# Or install separately
pip install govdocverify
```

The optional extra is defined in `pyproject.toml`:

```toml
[project.optional-dependencies]
fedstylevalidator = ["govdocverify>=0.1"]
```

> **Note:** `govdocverify` is the published package name for the Federal Style
> Validator. It is authored by the same team as DocReview360 and licensed MIT.

## Removing internal duplicates (once FSV is live)

Once FSV integration is confirmed working in production, the following internal
implementations should be removed:

- `src/docreview360/regulatory.py` — pattern-matching re-implementation of FSV
- `frontend/extensions/tiptapFederalStyleLint.ts` — local regex/rule lint extension
- Local readability scoring inside `doc_validation.py`

Track removal behind `RELEASE_CHECKLIST.md` Item 34 Phase 5.

## TipTap plugin integration

FSV will publish its own TipTap plugin. When available:

1. Install the FSV TipTap plugin package.
2. Register it in `frontend/extensions/registry.ts`.
3. Remove `tiptapFederalStyleLint.ts`.
4. Configure the FSV endpoint URL via `GET /admin/settings/fsv-url` in the
   plugin's constructor options.

## Version compatibility

| DocReview360 | FSV (govdocverify) | Notes |
|---|---|---|
| 0.1.x | ≥ 0.1 | Initial integration; proxy endpoints only |

Pin the FSV version in `pyproject.toml` to a tested minor version range.
Upgrade only after running the full FSV integration test suite.
