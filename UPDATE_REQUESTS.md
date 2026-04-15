# UPDATES

These are a list of updates to make. Ensure full test coverage.

## PRIORITY:

[done] In Project view, I want to make the Approvals table for those who are REQUIRED to approve, and Reviewers and Concurrence table for those who are optional. 
   - Move the "Approvals" table/section above "Reviewers Sign-off & Concurrence" table/section
   - Both the Approvals section and Reviewers Sign-off & Concurrence sections are collapsable/expandable so users don't need to see everything if they don't want to. For example, a required approver (someone in Approvals table), might not want to see who approved in Reviewers Sign-off & Concurrence section and vice versa. Let's show the basics (collapsed) and let them decide what to see. This applies only to Approvals section, Reviewers Sign-off & Concurrence Section, and Comments section. All other content is viewable always
   - Approvals table is fed by Workflow (requires the user to select a workflow). Reviewers sign off & concurrence, however, is added manually--meaning if we want a reviewer by someone who is not required, we'd go to the Reviewers Sign-off & Concurrence table, and add the user directly/manually.
   - For both "Approvals" and "Reviewers Sign-off & Concurrence", you can add the user (type User name to choose, which is fed from DocReview360 User management) to add to table. No extra steps besides typing their name in the search 
   - Approvals requires Documenso, Docusign, or Initial to concur (or non-concur). Reviewers sign off & concurrence is only click to concur (or non-concur) 
   - DO NOT CHANGE ANYTHING ELSE. I like the format/structure of Projects view. We just need to clean up the Approvals and Reviewer Sign-off & Concurrence sections for now.

## Items to Resolve

1. [done] Investigate the following. This was on strting the backend. Is this expected when using the "dev" ENV? Plus, is the Federal Style Validator expected to run on startup? We're starting the backend, so i'm not sure what it's validating--FSV is a document validator.

(DocReview360) PS C:\dev\DocReview360> $env:DOCREVIEW360_ENV=""dev""
(DocReview360) PS C:\dev\DocReview360> python -m uvicorn docreview360.api:app --reload --host 0.0.0.0 --port 8000
INFO:     Will watch for changes in these directories: ['C:\\dev\\DocReview360']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [29500] using StatReload
C:\dev\DocReview360\src\docreview360\auth\__init__.py:73: RuntimeWarning: DOCREVIEW360_SECRET_KEY environment variable not set; using development default
  SECRET_KEY = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:77: RuntimeWarning: DOCREVIEW360_ALGORITHM environment variable not set; using development default
  ALGORITHM = _env_or_default(""DOCREVIEW360_ALGORITHM"", default=DEFAULT_ALGORITHM)
C:\dev\DocReview360\src\docreview360\auth\__init__.py:78: RuntimeWarning: DOCREVIEW360_ACCESS_EXPIRE_MINUTES environment variable not set; using development default
  ACCESS_TOKEN_EXPIRE_MINUTES = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:83: RuntimeWarning: DOCREVIEW360_REFRESH_EXPIRE_DAYS environment variable not set; using development default
  REFRESH_TOKEN_EXPIRE_DAYS = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:88: RuntimeWarning: DOCREVIEW360_TOKEN_ISSUER environment variable not set; using development default
  TOKEN_ISSUER = _env_or_default(""DOCREVIEW360_TOKEN_ISSUER"", default=DEFAULT_TOKEN_ISSUER)
C:\dev\DocReview360\src\docreview360\auth\__init__.py:89: RuntimeWarning: DOCREVIEW360_TOKEN_AUDIENCE environment variable not set; using development default
  TOKEN_AUDIENCE = _env_or_default(""DOCREVIEW360_TOKEN_AUDIENCE"", default=DEFAULT_TOKEN_AUDIENCE)
C:\dev\DocReview360\src\docreview360\auth\__init__.py:97: RuntimeWarning: DOCREVIEW360_OIDC_SECRET_KEY environment variable not set; using development default
  OIDC_SECRET_KEY = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:101: RuntimeWarning: DOCREVIEW360_OIDC_ALGORITHM environment variable not set; using development default
  OIDC_ALGORITHM = _env_or_default(""DOCREVIEW360_OIDC_ALGORITHM"", default=DEFAULT_ALGORITHM)
C:\dev\DocReview360\src\docreview360\auth\__init__.py:102: RuntimeWarning: DOCREVIEW360_OIDC_EXPIRE_MINUTES environment variable not set; using development default
  OIDC_TOKEN_EXPIRE_MINUTES = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:107: RuntimeWarning: DOCREVIEW360_OIDC_TOKEN_ISSUER environment variable not set; using development default
  OIDC_TOKEN_ISSUER = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:110: RuntimeWarning: DOCREVIEW360_OIDC_TOKEN_AUDIENCE environment variable not set; using development default
  OIDC_TOKEN_AUDIENCE = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:120: RuntimeWarning: DOCREVIEW360_REQUIRE_MFA environment variable not set; using development default
  REQUIRE_MFA = _env_or_default(""DOCREVIEW360_REQUIRE_MFA"", default=""false"", cast=_as_bool)
C:\dev\DocReview360\src\docreview360\auth\__init__.py:121: RuntimeWarning: DOCREVIEW360_SEED_DEMO_USERS environment variable not set; using development default
  SEED_DEMO_USERS = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:160: RuntimeWarning: DOCREVIEW360_MAX_FAILED_ATTEMPTS environment variable not set; using development default
  MAX_FAILED_ATTEMPTS = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:165: RuntimeWarning: DOCREVIEW360_LOCKOUT_SECONDS environment variable not set; using development default
  LOCKOUT_SECONDS = _env_or_default(
C:\dev\DocReview360\src\docreview360\auth\__init__.py:178: RuntimeWarning: DOCREVIEW360_USER_DB environment variable not set; using development default
  USER_DB_PATH = _env_or_default(
INFO:     Started server process [7556]
INFO:     Waiting for application startup.
INFO:docreview360.config_validator:Startup configuration validation passed
INFO:fedstylevalidator.core.cli:Processing document of type: Other, group_by: category
INFO:fedstylevalidator.core.utils.terminology_utils:Initialized TerminologyManager
INFO:fedstylevalidator.core.checks.heading_checks:Initialized HeadingChecks with pattern cache
INFO:fedstylevalidator.core.checks.terminology_checks:Initialized TerminologyChecks with terminology manager
INFO:fedstylevalidator.core.checks.readability_checks:Initialized ReadabilityChecks with terminology manager
INFO:fedstylevalidator.core.checks.acronym_checks:Initialized AcronymChecker
INFO:fedstylevalidator.core.checks.accessibility_checks:Initialized AccessibilityChecks
INFO:fedstylevalidator.core.checks.reference_checks:Initialized TableFigureReferenceCheck
INFO:fedstylevalidator.core.checks.reference_checks:Initialized DocumentTitleFormatCheck
INFO:fedstylevalidator.core.checks.heading_checks:Initialized HeadingChecks with pattern cache
INFO:fedstylevalidator.core.checks.terminology_checks:Initialized TerminologyChecks with terminology manager
INFO:fedstylevalidator.core.checks.terminology_checks:Initialized TerminologyChecks with terminology manager
INFO:fedstylevalidator.core.checks.acronym_checks:Initialized AcronymChecker
INFO:fedstylevalidator.core.checks.accessibility_checks:Initialized AccessibilityChecks
INFO:fedstylevalidator.core.checks.accessibility_checks:Initialized AccessibilityChecks
INFO:fedstylevalidator.core.checks.reference_checks:Initialized DocumentTitleFormatCheck
INFO:fedstylevalidator.core.checks.reference_checks:Initialized DocumentTitleFormatCheck
INFO:fedstylevalidator.core.checks.reference_checks:Initialized TableFigureReferenceCheck
INFO:fedstylevalidator.core.checks.reference_checks:Initialized TableFigureReferenceCheck
INFO:fedstylevalidator.processing:Detected MIME type: text/plain
INFO:fedstylevalidator.core.processing:Reading file: C:\Users\ericp\AppData\Local\Temp\tmp23nvhv5y.txt
INFO:fedstylevalidator.processing:Running document checks (text file)
INFO:fedstylevalidator.core.document_checker:Running heading checks...
INFO:fedstylevalidator.core.checks.heading_checks:Running heading checks for document type: Other
ERROR:fedstylevalidator.core.document_checker:Error in heading checks: 'types.SimpleNamespace' object has no attribute 'style'
INFO:fedstylevalidator.core.document_checker:Running accessibility checks...
INFO:fedstylevalidator.core.checks.accessibility_checks:Running accessibility checks for document type: Other
ERROR:fedstylevalidator.core.document_checker:Error in accessibility checks: 'types.SimpleNamespace' object has no attribute 'runs'
INFO:fedstylevalidator.core.document_checker:Running format checks...
INFO:fedstylevalidator.core.checks.format_checks:Running format checks for document type: Other
INFO:fedstylevalidator.core.document_checker:Running structure checks...
INFO:fedstylevalidator.core.checks.structure_checks:[StructureChecks] check_document called
INFO:fedstylevalidator.core.checks.structure_checks:Running structure checks for document type: Other
INFO:fedstylevalidator.core.checks.structure_checks:[StructureChecks] check_document completed
INFO:fedstylevalidator.core.document_checker:Running terminology checks...
INFO:fedstylevalidator.core.checks.terminology_checks:Running terminology checks for document type: Other
INFO:fedstylevalidator.core.document_checker:Running readability checks...
INFO:fedstylevalidator.core.checks.readability_checks:Running readability checks for document type: Other
INFO:fedstylevalidator.core.document_checker:Running style checks...
INFO:fedstylevalidator.core.checks.style_checks:Running style checks for document type: Other
INFO:fedstylevalidator.core.document_checker:Running acronym checks...
INFO:fedstylevalidator.core.document_checker:Running formatting checks...
INFO:fedstylevalidator.core.document_checker:Running formatting checks...
INFO:fedstylevalidator.core.document_checker:Completed all checks. Found 0 issues.
INFO:fedstylevalidator.core.cli:Formatting results
ERROR:fedstylevalidator.core.cli:ERROR: Error processing document: 'list' object has no attribute 'values'
WARNING:docreview360.ml.compliance_classifier:ONNX model inference failed: onnxruntime is not installed; install it to enable ML inference features.
INFO:     Application startup complete."

2. [done] Investigate the following and resolve package messages and vulnerabilities.

(DocReview360) PS C:\dev\DocReview360\frontend> npm install --legacy-peer-deps

up to date, audited 439 packages in 2s

111 packages are looking for funding
  run `npm fund` for details

4 high severity vulnerabilities

To address issues that do not require attention, run:
  npm audit fix

To address all issues, run:
  npm audit fix --force

Run `npm audit` for details."

3. [done] Investigate the following error message when strting the frontend (internationalization)

(DocReview360) PS C:\dev\DocReview360\frontend> npm run dev

> docreview360-frontend@0.1.0 dev
> next dev

⚠ Invalid next.config.js options detected: 
⚠     Invalid literal value, expected false at ""i18n.localeDetection""
⚠ See more info here: https://nextjs.org/docs/messages/invalid-next-config
▲ Next.js 16.1.7 (Turbopack)
- Local:         http://localhost:3000
- Network:       http://10.2.0.2:3000
- Environments: .env.local
- Experiments (use with caution):
  ✓ optimizeCss"

4. [done] Investigate the following. I keep getting similar errors in the frontend UI. We make a change, and the frontend crashes. Happens frequently. Is there a way to prevent this from continuing to happen? Should we update AGENTS.md or CLAUDE.md to always check that we didn't break the frontend after every change via some test mechanism?

Tools > Document Quality:

Runtime TypeError


Failed to fetch
lib/api.ts (109:18) @ authenticatedFetch


  107 |
  108 |   try {
> 109 |     return await fetch(fullUrl, {
      |                  ^
  110 |       ...options,
  111 |       headers,
  112 |       credentials: ""include"",
Call Stack
17

Show 15 ignore-listed frame(s)
authenticatedFetch
lib/api.ts (109:18)
handleSubmit
pages/tools/document-quality.tsx (586:49)"

5. [done] In Tools, Document Quality Checker, I want to simplify this page. All we need is to pull in and use Federal Style Validator (FSV). This app is vailable on PyPI. We don't need to code any validation checkboxes or anything directly into DocReview360. Only pull in the FSV frontend as is and display the FSV findings. We don't need to repeat or duplicate what FSV is already doing. You can view FSV on this machine at C:\dev.

Document Quality Checker
Powered by Federal Style Validator
Validate documents against federal style guidelines (FAA/DoD), plain language standards, acronym compliance, and regulatory requirements. Additional validation engines can be configured below.


Federal Style Validator

Additional Engines
Federal Style Validator — checks FAA/DoD style, plain language, acronyms, regulatory references, readability, and accessibility compliance.

Backend connection failed — check configuration

Upload File

System Document
Upload a document
DOC / DOCX only. The Federal Style Validator checks headings, accessibility, FAA/DoD style rules, plain language, and undefined acronyms.

test_document.docxRun FSV checks
Error
Backend error: HTTP 503: Service Unavailable

Troubleshooting:

Ensure the backend server is running on port 8000
Check that Federal Style Validator is properly installed
Verify NEXT_PUBLIC_API_BASE environment variable is set
Check browser console for detailed error information"

6. [done] Simliar to earlier. The frontend pages keep breaking. From Projects view, I click to Edit the document and it crashed. I can get into TipTap without it crashing.

### Failure

Failed to fetch
lib/api.ts (109:18) @ authenticatedFetch


  107 |
  108 |   try {
> 109 |     return await fetch(fullUrl, {
      |                  ^
  110 |       ...options,
  111 |       headers,
  112 |       credentials: ""include"",
Call Stack
17

Show 15 ignore-listed frame(s)
authenticatedFetch
lib/api.ts (109:18)
EditProjectPage.useEffect
pages/projects/[id]/edit.tsx (213:23)"

### API

 GET /editors/tiptap?projectId=demo&readonly=1 500 in 468ms (compile: 373ms, render: 94ms)
https://nextjs.org/docs/messages/module-not-found"

7. [done] In projects, I edited the project to add a workflow. In Approvals table, I added an Assignee. It worked, but the table columns are not aligned. If we're using table formatting, ensure all columns and rows are aligned
8. [done] I added user "bob" as an approver. I logged in as "bob", clicked Approve button for a project, and received a 404 This page could not be found. It works in Reviewer Sign-off & Concurrence but not Approvals table
9. [done] I added user "bob" as both a reviewer and approver. The audit history shows that "bob" started review and concurred--The Reviewer Sign-off & Concurrence shows that bob concurred, which is correct. However, the Project Lifecycle section indicates we're still in draft (in review and reviewed are not marked as complete). 
