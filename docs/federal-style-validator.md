# Federal Style Validator Integration — Pending Items

The FSV proxy layer, admin settings endpoints, on-save validation, quality badge,
per-check category configuration, and `pyproject.toml` optional extra are all
implemented and tested. This document tracks what remains.

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
