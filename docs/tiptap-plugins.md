# TipTap Plugin Development

This short guide explains how DocuFlow's editor wrappers work.

Plugins export a loader function that registers toolbar actions or text
transformations. Frontend code calls the REST endpoint `/api/plugins`
to discover available wrappers and then loads each script. See the
`editor_loader.load_plugins` helper for unit tests.
