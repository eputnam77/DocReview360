# SharePoint Graph API for Revision History and Metadata Sync

This document lists Microsoft Graph endpoints and payload structures required to
connect `DocumentModel.history` to SharePoint's versioning system and to push
application metadata alongside uploaded documents.

## Revision linkage

### Upload or overwrite a file
`PUT /sites/{site-id}/drives/{drive-id}/root:/{path}:/content`

Headers:
- `Authorization: Bearer <token>`
- `If-Match: "{etag}"` *(optional conflict detection)*

Body: binary document bytes.

Response contains the drive item `id`. Re-uploading to the same path creates a
new SharePoint version automatically.

### List versions
`GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/versions`

Returns an array of version objects with fields such as `id`,
`lastModifiedBy`, and `lastModifiedDateTime`.

### Get a specific version
`GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/versions/{version-id}`

Retrieves metadata for one version.

### Download version content
`GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/versions/{version-id}/content`

Returns the file bytes for the selected version.

### Restore a version
`POST /sites/{site-id}/drives/{drive-id}/items/{item-id}/versions/{version-id}/restore`

Restores the specified version as the current file.

## Metadata synchronisation

After each save, custom document properties can be written via the item's
underlying list fields:

`PATCH /sites/{site-id}/drives/{drive-id}/items/{item-id}/listItem/fields`

Headers:
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

Example payload:
```json
{
  "DocID": "<uuid>",
  "WorkflowName": "Draft",
  "ApprovalStatus": "In Review",
  "VersionNumber": "5",
  "SHA256Hash": "<hash>",
  "ChangeSummary": "Updated introduction",
  "ModifiedBy": "<user>",
  "ModifiedAt": "2024-05-01T12:34:56Z"
}
```

The field names must exist on the target SharePoint list. Use
`GET /sites/{site-id}/drives/{drive-id}/items/{item-id}?select=id,name,webUrl,listItem`
if metadata retrieval is required.

### Integrity verification
To verify content integrity, compute a SHA-256 hash of the uploaded bytes and
store it in the `SHA256Hash` field. When downloading a version, recompute the
hash and compare it with the stored value.

## Conflict detection
When uploading new content, include the latest file `etag` in the `If-Match`
header. SharePoint will reject the upload with `412 Precondition Failed` if a
newer version exists, enabling the application to handle merge decisions.
