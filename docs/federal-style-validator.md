# Federal Style Validator (FSV) Integration

## Overview

DocReview360 integrates the Federal Style Validator (FSV) as an optional dependency for
government-document style checking. The FSV is accessed via `fsv_proxy.py` and surfaced
in the document-quality page as an embedded iframe.

## Phase 5 — Pending Items

The following cleanup tasks remain open under **Item 34 Phase 5**:

### Removing internal duplicates

`regulatory.py` contains style-check logic that duplicates FSV functionality.
Once the FSV TipTap plugin is live this file should be removed or reduced to a thin
shim. Until then both code paths coexist.

### TipTap plugin integration

The `tiptapFederalStyleLint.ts` extension provides in-editor FSV feedback via custom
Tiptap marks. It is slated for removal once the upstream FSV TipTap plugin ships
officially and is registered in `registry.ts`.

## Files Involved

| File | Purpose |
|---|---|
| `src/docreview360/fsv_proxy.py` | FSV integration adapter |
| `src/docreview360/regulatory.py` | Legacy style rules (pending removal) |
| `frontend/extensions/tiptapFederalStyleLint.ts` | In-editor lint marks (pending removal) |
| `frontend/extensions/registry.ts` | TipTap extension registry |

## Dependency

FSV is declared as an optional extra in `pyproject.toml`:

```toml
[project.optional-dependencies]
fedstylevalidator = ["fedstylevalidator>=0.1"]
```

Install with:

```bash
pip install "docreview360[fedstylevalidator]"
```
