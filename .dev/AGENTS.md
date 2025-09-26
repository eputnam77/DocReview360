# AGENTS.md

*Authoritative playbook for this repository’s **OpenAI Codex** workflow*

---

## 0 · Global Settings

| Key                       | Value                                                          |
| ------------------------- | -------------------------------------------------------------- |
| Default shell             | `bash` (Linux)                                                 |
| Supported Python versions | **3.12** (primary)                                             |
| Virtual-env manager       | `uv venv` *(falls back to `python -m venv`)*                   |
| Dependency manager        | `poetry install --with dev` → synced via `poetry sync`         |
| Package lock-source       | `poetry.lock`                                                  |
| Code formatter            | `ruff format`                                                  |
| Lint checker              | `ruff check`                                                   |
| Test runner               | `pytest`                                                       |
| Optional type checker     | `mypy --strict` *(when annotations are available)*             |
| Optional docs generator   | `mkdocs build --strict` *(run only when docs change)*          |
| Commit style              | Conventional Commits                                           |

> **Data flow** — Each agent works off the latest commit on its branch and acquires an
> `agent-running` lock-label to avoid concurrent pushes.

---

## 1 · Agents & Execution Order

| #  | Agent ID     | Purpose (one-liner)                                             | Auto-trigger condition    |
| -- | ------------ | --------------------------------------------------------------- | ------------------------- |
| 0  | `planner`    | Parse **PRD.md** → create **TASKS.md**.                         | manual                    |
| 1  | `architect`  | Design folder layout, write ADRs, bootstrap Poetry if missing.  | `planner` PR merged       |
| 2  | `builder`    | Implement code for `ready` issues and update/add tests.         | `architect` PR merged     |
| 3  | `linter`     | Run Ruff (`ruff format` if needed); open PR if diff.            | after `builder:success`   |
| 4  | `tester`     | Run `pytest`; optionally run MyPy when available.               | after `linter:success`    |
| 5  | `docwriter`  | Update README, API refs, examples, and changelog when needed.   | branch green              |
| 6  | `reviewer`   | Human-style review; request approvals.                          | after `docwriter:success` |
| 7  | `releasebot` | Bump version and draft release notes.                           | PR merged → `main`        |

### Agent-handoff rules

* Success → add `ready-for:<next-agent>` **and** remove `agent-running`.
* Gates focus on tooling we can execute inside this sandbox (see below).

---

## 2 · Quality Gates

### Dev Gate (feature branches)

```bash
ruff check src tests
pytest -q
```

Run `mypy --strict src tests` if the project already provides annotations and MyPy is installed.
Use `ruff format` to auto-format before re-running checks.

### Release Gate (main)

```bash
ruff check src tests
pytest -q --cov=src --cov-branch
mkdocs build --strict   # only when documentation changes
```

If a tool is unavailable in the sandbox, note it in the PR and proceed with the checks that are supported here.

---

## 3 · Documentation Standards

### Tone & Voice

* Friendly, conversational, inclusive.
* Active voice.
* Confident and helpful.
* Avoid unnecessary jargon.

### Structure & Formatting

* Clear, hierarchical headings (H1 → H2 → H3).
* Provide runnable code snippets where they add clarity.
* Use numbered, step-by-step instructions for complex flows.
* Cross-reference related docs when helpful.

### Content Guidelines

* Start with the problem a feature solves before explaining how.
* Provide real-world use-cases.
* Document common errors and fixes.
* Mention any performance implications or limitations.

### Technical Writing Standards

* Keep terminology consistent across docs.
* API docs include parameter types, return values, and examples.
* Changelog follows **Keep a Changelog**.
* README layout: Install → Quick-start → Features → Contributing → License.

### Templates

* `templates/README.md` — canonical README structure.
* `templates/API_DOCS.md` — API reference template.
* `templates/CHANGELOG.md` — release-notes skeleton.

---

## 4 · Branch & Commit Policy

* Branch prefixes: `plan/<slug>` · `feat/<slug>` · `fix/<issue>` · `docs/<topic>` · `test/<scope>`.
* Commits follow Conventional Commits, e.g. `feat/auth: add OAuth login flow`.
* Default merge strategy: squash-merge with required status checks on `main`.

---

## 5 · Environment Setup

```bash
# create & activate virtual-env
uv venv "3.12"

# install dependencies from the Poetry lock file
poetry install --with dev
poetry sync --with dev

# (optional) enable pre-commit hooks
pre-commit install
```

---

## 6 · Failure-Recovery Matrix

| Problem              | Responsible Agent | Remedy                                      |
| -------------------- | ----------------- | ------------------------------------------- |
| Lint error           | linter            | Auto-fix with Ruff and push                 |
| Type error           | tester → fixer    | Adjust types and/or code                    |
| Unit test failure    | fixer             | Add or adjust tests, then patch the code    |
| Coverage drop        | builder/tester    | Add tests or mark legitimate exclusions     |
| Docs build failure   | docwriter         | Regenerate or repair docs                   |

---

*End of AGENTS.md*
