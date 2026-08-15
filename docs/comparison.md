# SimpleDocReview vs DocReview360

Both tools review and approve documents without a cloud account. They are built for
different sizes of problem, and they are meant to be picked between rather than
compared feature-for-feature.

**SimpleDocReview** — lightweight, local-first document review and approval.

**DocReview360** — full document review, approval, governance, and audit workflow platform.

## At a glance

| | SimpleDocReview | DocReview360 |
| --- | --- | --- |
| Setup | Extremely simple; standard-library HTTP server | Full application (FastAPI + Next.js + CLI) |
| Cloud account required | No | No |
| Storage | JSON files on disk | SQLite by default; PostgreSQL, MySQL, SQL Server, Oracle |
| Formats | `.txt`, `.md`, `.docx` | DOCX, PDF, HTML, Markdown |
| Reviewer assignment | Yes | Yes, with parallel and sequential phases |
| Approvals | All assigned reviewers must approve | Configurable required approvals, reassignment, reminders, escalations, digital signatures |
| Revision history | Limited | Autosaved revisions with SHA-256 revision hashes |
| Inline review | Basic comments and change requests | Text-anchored inline comments in a rich-text editor |
| Audit record | Activity timeline | Hash-chained, tamper-evident audit log with CLI verification |
| Authentication | Minimal / local | JWT, TOTP MFA, RBAC; optional LDAP/AD, SAML 2.0, WebAuthn |
| Workflow stages | Fixed state machine | Configurable workflow phases |
| Document quality checks | Deterministic local checks | Federal writing-standards validation, optional ONNX critic models |
| Best for | An individual or a small team | Teams and organizations with review policy to enforce |

## Choose SimpleDocReview when

- You want review and sign-off on a handful of documents with near-zero setup.
- Everything should stay on one machine, with no database and minimal dependencies.
- An activity timeline is enough; you do not need to prove the record was not altered.

## Choose DocReview360 when

- Reviews follow a defined workflow with ordered phases and required approvers.
- You need version history, and need to show which revision was approved.
- You need a tamper-evident audit trail you can verify after the fact.
- You want document quality analysis in the same place as the review.
- You are deploying for a team: shared database, roles and permissions, enterprise sign-in.

## How DocReview360 compares to commercial systems

DocReview360 is an alpha, open-source project. Established document-control products
(SharePoint with Power Automate, M-Files, DocuWare, Box Relay, Ideagen PleaseReview,
Ziflow) carry years of production use, support organizations, and deployment
experience that a young project does not.

Where DocReview360 differs is scope: most products cover either document routing and
approval *or* collaborative review and annotation. DocReview360 covers the full path —
author, review, analyze quality, revise, approve, verify, publish, audit — and runs on
infrastructure you control, under the MIT license.

See [Supported platforms](supported-platforms.md) for what is tested, and the
[changelog](changelog.md) for release history.
