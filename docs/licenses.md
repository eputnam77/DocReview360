# Third-Party Licenses

DocReview360 is licensed under the [MIT License](../LICENSE).

This file documents the licenses of third-party dependencies bundled with or
required by DocReview360. It is informational, not legally authoritative. Review
each package's official license for the full terms.

---

## Python Dependencies

| Package | License | Notes |
|---|---|---|
| FastAPI | MIT | Web framework |
| Starlette | BSD-3-Clause | ASGI toolkit (FastAPI dependency) |
| Pydantic | MIT | Data validation |
| SQLAlchemy | MIT | ORM and database abstraction |
| uvicorn | BSD-3-Clause | ASGI server |
| python-jose | MIT | JWT encoding/decoding |
| bcrypt | Apache-2.0 | Password hashing |
| pyotp | MIT | TOTP/MFA |
| click | BSD-3-Clause | CLI framework |
| Jinja2 | BSD-3-Clause | Templating |
| python-docx | MIT | Word document import/export |
| reportlab | BSD-3-Clause | PDF generation |
| bleach | Apache-2.0 | HTML sanitization |
| markdown-it-py | MIT | Markdown rendering |
| Pillow | HPND | Image processing |
| matplotlib | PSF/BSD-compatible | Charts and visualizations |
| PyYAML | MIT | YAML config parsing |
| python-multipart | Apache-2.0 | Form and file upload parsing |
| httpx | BSD-3-Clause | HTTP client |
| celery | BSD-3-Clause | Async task queue |
| redis | MIT | Redis client (Celery broker) |
| graphene | MIT | GraphQL API |
| prometheus-client | Apache-2.0 | Metrics instrumentation |
| psycopg | LGPL-3.0 | PostgreSQL adapter |
| pymysql | MIT | MySQL adapter |
| python-dotenv | BSD-3-Clause | `.env` file loading |
| textstat | MIT | Readability scoring |
| textblob | MIT | NLP utilities |
| wikipedia | MIT | Wikipedia API client |
| zipp | MIT | Zip file utilities |
| fonttools | MIT | Font file utilities |
| python-magic / python-magic-bin | MIT | MIME type detection |

### Optional ML Dependencies

| Package | License | Notes |
|---|---|---|
| torch | BSD-3-Clause | PyTorch deep learning framework |
| onnx | Apache-2.0 | Open Neural Network Exchange format |
| onnxruntime | MIT | ONNX inference runtime |
| tiktoken | MIT | OpenAI tokenizer |

### Development-Only Dependencies

| Package | License | Notes |
|---|---|---|
| pytest | MIT | Test runner |
| pytest-cov | MIT | Coverage reporting |
| pytest-asyncio | Apache-2.0 | Async test support |
| pytest-playwright | Apache-2.0 | Browser E2E tests |
| playwright | Apache-2.0 | Browser automation |
| hypothesis | MPL-2.0 | Property-based testing |
| ruff | MIT | Linting and formatting |
| black | MIT | Code formatter |
| mypy | MIT | Static type checker |
| bandit | Apache-2.0 | Security linting |
| semgrep | LGPL-2.1 | Static analysis |
| pip-audit | Apache-2.0 | Dependency vulnerability scanning |
| pre-commit | MIT | Git hook management |
| mutmut | MIT | Mutation testing |
| uvicorn | BSD-3-Clause | Dev server for E2E tests |

---

## Frontend Dependencies

| Package | License | Notes |
|---|---|---|
| Next.js | MIT | React framework |
| React | MIT | UI library |
| React DOM | MIT | DOM rendering |
| TypeScript | Apache-2.0 | Type-safe JavaScript |
| Tailwind CSS | MIT | Utility-first CSS framework |
| TipTap (all `@tiptap/*` packages) | MIT | Rich-text editor framework |
| Hocuspocus (`@hocuspocus/provider`) | MIT | Collaborative editing provider |
| @tanstack/react-query | MIT | Server state management |
| @headlessui/react | MIT | Accessible UI primitives |
| @radix-ui/react-dialog | MIT | Dialog primitives |
| @radix-ui/react-select | MIT | Select primitives |
| Editor.js (`@editorjs/*`) | Apache-2.0 | Alternative block editor |
| vitest | MIT | Unit test runner |
| PostCSS | MIT | CSS transformation |

---

## Data and Asset Licenses

- Sample documents in `samples/` are provided for demonstration only and carry
  no additional license restrictions beyond the project's MIT license.
- Golden template files in `templates/golden/` are original works licensed
  under the MIT License.

---

## License Compatibility

DocReview360 uses the MIT License. All core runtime dependencies are MIT,
BSD-compatible, or Apache-2.0, which are all compatible with MIT distribution.

Notable optional/dev-only exceptions:
- **psycopg** (LGPL-3.0) — optional extra (`[postgres]`); not required for MIT-clean installs.
- **semgrep** (LGPL-2.1) — dev/security tooling only; not a runtime dependency.
- **hypothesis** (MPL-2.0) — test tooling only; not a runtime dependency.
- **govdocverify / FedStyleValidator** (GPL-3.0, optional `[fedstylevalidator]` extra) — same
  author; not installed by default; evaluate license terms when enabling this extra.

The MIT License allows embedding DocReview360 in proprietary products without
copyleft obligations, provided the MIT license notice is retained.
