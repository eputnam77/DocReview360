# Latest Features

This page tracks implemented product work that was moved out of
`RELEASE_CHECKLIST.md` on 2026-03-10.

For open work, use `RELEASE_CHECKLIST.md`.

## Authoring and templates

- TipTap-based structured template authoring is in place.
- TipTap plugin safety and compatibility rules are documented in `docs/tiptap-plugins.md`.
- Content schema validation and CMS-safe persistence are in place.
- Template version history and phase-based locking are available.

## Workflow and project review

- Phase configuration now uses richer metadata and DB-backed APIs.
- Document types can define their own ordered workflow phases.
- Project review screens include workflow timeline, approvals grid, reviewer comments, and phase gating.
- Share links, viewer-only access, and branding controls shipped.

## Review and signature

- Documenso is available as the default e-signature provider.
- DocuSign is available as an optional enterprise provider.
- Signature activity is logged into the audit trail.
- Approval-by-initials support shipped.

## Review experience

- Threaded comments, structured comment tags, and comment dispositions shipped.
- Comment export to Word is available.
- Document conversion supports Word, Markdown, and PDF flows.
- Revision diff and version restore flows are available.

## Dashboards and AI review

- User, manager, admin, executive, reviewer workload, SLA, and document aging views shipped.
- The global footer now shows product and build metadata.
- AI-assisted review shipped for style validation, acronyms, headings, plain language, regulatory citation checks, and pre-flight validation.

## Enterprise readiness

- Organization support and per-organization settings shipped.
- API key management shipped.
- Notification integrations shipped for Slack, Teams, email, and webhooks.
- Project bundle export/import and backup/restore support shipped.

## Platform stability

- Health checks, deterministic migrations, demo data, and the dev Docker Compose stack shipped.
- Document version incrementing, history, restore, and freeze-at-approval shipped.
