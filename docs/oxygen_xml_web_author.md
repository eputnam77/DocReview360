# Oxygen XML Web Author Integration

This document describes how to add Oxygen XML Web Author as an optional document editor in DocReview360.

## Decision

Yes. DocReview360 can support Oxygen XML Web Author as a secondary editor.

Use Oxygen XML Web Author, or the Web Author Component, as the browser-based XML editor. The Oxygen documentation describes an embedded integration model where the editor front end is loaded in an `iframe` and the Java back end runs separately.

Do not treat the current `XML` label in **Configuration > Integrations** as working editor support. In the current codebase, it is only a UI option. The actual editor routing and rendering paths only support `ckeditor5`, `tiptap`, and `onlyoffice`.

## Current Gap in This Repo

These files show the current mismatch:

- `frontend/pages/configuration/integrations.tsx` lists `XML` in the editor selector.
- `frontend/lib/editorRouting.ts` only normalizes `ckeditor5`, `tiptap`, and `onlyoffice`.
- `src/docreview360/editor_switcher.py` only renders placeholders for `tiptap` and `ckeditor5`, and a plugin path for `onlyoffice`.
- `src/docreview360/cli.py` does not offer an Oxygen-specific editor option.

Result: selecting `XML` today does not give DocReview360 a working Oxygen editor route.

## Recommended Product Choice

Use one of these models:

1. `Oxygen XML Web Author`
   Best if DocReview360 will point to a separately deployed Oxygen server.
2. `Web Author Component`
   Best if DocReview360 will distribute Oxygen as an embedded part of the product with a tighter OEM-style integration.

For a first implementation, the simpler path is the standalone Web Author product behind a reverse proxy.

## Recommended Integration Shape

Keep `ckeditor5` as the default editor.

Add Oxygen as a selectable provider for XML-centric documents only. Use a real provider key such as `oxygen` or `oxygen-web-author`. Do not use the generic value `xml` as the runtime editor id.

Recommended flow:

1. DocReview360 stores the document and editor selection as usual.
2. When the selected editor is `oxygen`, the frontend opens `/editors/oxygen`.
3. That page renders an `iframe` pointed at the Oxygen editor URL.
4. DocReview360 passes the document URL and user display name to Oxygen.
5. Oxygen loads and saves the XML through its configured storage connector.

## Hosting Requirements

Oxygen recommends serving Web Author from the same origin as the host page when possible. Web Author relies on cookies for licensing and editor state, and some browsers block third-party cookies. In practice, this means:

- Prefer `https://app.example.gov/oxygen/...` proxied to the Oxygen server.
- Avoid cross-site `iframe` hosting if possible.
- Deploy the Oxygen back end separately from the main DocReview360 app.

## DocReview360 Changes

### 1. Add a real editor id

Update every editor enum or normalization path to support `oxygen`.

Files to update:

- `frontend/pages/configuration/integrations.tsx`
- `frontend/lib/editorRouting.ts`
- `src/docreview360/editor_switcher.py`
- `src/docreview360/cli.py`
- tests that assert the supported editor list

Suggested UI label:

- `Oxygen XML Web Author`

Suggested stored value:

- `oxygen`

### 2. Add an Oxygen editor route

Create a new frontend page:

- `frontend/pages/editors/oxygen.tsx`

This page should:

1. Read `id` or `projectId` from the query string.
2. Fetch the document metadata from DocReview360.
3. Resolve an Oxygen launch URL.
4. Render an `iframe` that fills the page.
5. Show a clear error state if the Oxygen integration is not configured.

The target URL will be the Oxygen entry page, typically `app/oxygen.html`, with query parameters for the document and editor behavior.

Useful parameters from Oxygen docs include:

- `url`
- `author`
- `trackChanges`
- `contentType=application/xml`
- `lang`
- `tags-mode`

### 3. Add an Oxygen launch endpoint

Do not build the Oxygen URL entirely in the browser if it requires secrets or signed URLs.

Add a backend endpoint that returns an embeddable launch descriptor, for example:

`GET /api/editors/oxygen-launch?id=<doc-id>`

Suggested response:

```json
{
  "provider": "oxygen",
  "iframe_url": "https://app.example.gov/oxygen/app/oxygen.html?url=...",
  "document_url": "https://app.example.gov/api/oxygen/documents/123/content",
  "readonly": false
}
```

This endpoint should:

- verify the current user can access the document
- verify the document is XML-compatible
- return a signed or otherwise scoped document URL
- return a meaningful error when Oxygen is disabled

### 4. Expose document content in an Oxygen-friendly way

Oxygen requires a file URL or connector-backed URL to open and save content. There are 3 viable options.

1. WebDAV
   Fastest to wire if DocReview360 is willing to expose XML documents through WebDAV.
2. Oxygen REST file storage integration
   Better fit if DocReview360 wants a controlled application API.
3. Custom Oxygen plugin
   Best for advanced permissions, metadata, check-in/check-out, or nonstandard save rules.

Recommended order:

1. Start with REST or WebDAV.
2. Move to a custom Oxygen plugin only if save semantics or permissions require it.

### 5. Add configuration

Add explicit Oxygen settings. Example names:

- `oxygen_enabled`
- `oxygen_base_url`
- `oxygen_same_origin_path`
- `oxygen_default_track_changes`
- `oxygen_timeout_seconds`

If authentication between DocReview360 and Oxygen needs a shared secret or token exchange, store that separately from the launch URL.

### 6. Limit Oxygen to XML-capable content

Do not make Oxygen the generic fallback editor.

Only offer Oxygen when the document format is one of these:

- XML
- DITA
- DocBook
- TEI
- XHTML

For HTML, Markdown, or rich text authored primarily in the existing editors, continue using `ckeditor5` or `tiptap`.

## Implementation Phases

### Phase 1

Wire the editor choice and route only.

- add `oxygen` to config and routing
- add `/editors/oxygen`
- add a placeholder page that reports configuration status

### Phase 2

Add launch endpoint and reverse proxy.

- add backend launch API
- proxy Oxygen under the same site origin
- open real XML documents in the iframe

### Phase 3

Add save integration.

- implement WebDAV or REST-backed open/save
- enforce per-document authorization
- log edit access

### Phase 4

Add XML-specific UX polish.

- track changes defaults
- reviewer vs author mode
- document-type specific frameworks
- error handling for invalid XML or unsupported schema

## Acceptance Criteria

The feature is complete when all of these are true:

1. Admins can select `Oxygen XML Web Author` in **Configuration > Integrations**.
2. `ckeditor5` remains the default editor.
3. A document configured with `oxygen` opens in `/editors/oxygen`.
4. The editor loads inside an `iframe` without cross-site cookie failures.
5. XML documents can open and save successfully.
6. Non-XML documents do not route to Oxygen by default.

## Risks

- Licensing and commercial terms differ between the Web Author product and the Web Author Component.
- Cross-site cookie restrictions will break embedded editing if Oxygen is hosted on another origin.
- Oxygen still needs a proper file storage integration. The `iframe` alone is not enough.
- The current `XML` option may create confusion because it suggests a working editor that does not yet exist.

## Recommendation

Proceed with an `oxygen` provider, not `xml`.

Treat this as a secondary XML editor path. Keep `ckeditor5` as the primary editor and expose Oxygen only for XML-centric document types or projects that explicitly opt in.

## References

- Oxygen XML Web Author overview: https://www.oxygenxml.com/xml_web_author.html
- Embedding Web Author in another app: https://www.oxygenxml.com/doc/ug-waCustom/topics/webauthor-integrate-with-another-app.html
- Launching Web Author with URL parameters: https://www.oxygenxml.com/doc/ug-waCustom/topics/webauthor-integrate-embedded-launch.html
- User management integration: https://www.oxygenxml.com/doc/ug-waCustom/topics/webauthor-user-management-integration.html
- Web Author vs. Web Author Component: https://www.oxygenxml.com/doc/ug-editor/topics/wa-product-vs-sdk.html
