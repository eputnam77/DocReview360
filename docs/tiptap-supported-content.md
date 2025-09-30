# TipTap Content Support

DocReview360 converts TipTap JSON payloads into Markdown before storing a
revision. The converter understands a curated set of nodes and marks that map
cleanly to Markdown or HTML constructs.

## Supported block nodes

The backend recognises the following node types:

| Node type       | Notes |
| --------------- | ----- |
| `paragraph`     | Standard text paragraphs. |
| `heading`       | Levels 1–6 are mapped to Markdown `#` prefixes. |
| `bulletList`    | Nested unordered lists are preserved. |
| `orderedList`   | Supports custom `start` attributes. |
| `blockquote`    | Emits Markdown `>` prefixes for each nested line. |
| `codeBlock`     | Wrapped in fenced code blocks; the `language` attribute carries through to the fence. |
| `hardBreak`     | Rendered as blank lines. |
| `horizontalRule`| Rendered as `---`. |
| `table`         | Converted to GitHub‑style Markdown tables with optional header rows. |

## Supported marks

| Mark type   | Output |
| ----------- | ------ |
| `bold`      | `**text**` |
| `italic`    | `*text*` |
| `strike`    | `~~text~~` |
| `code`      | `` `text` `` |
| `underline` | `<u>text</u>` |
| `link`      | `[text](href "title")` |

Marks are applied in the order received, so combinations such as bold+underline
or italics inside links render predictably.

## Extending the converter

Use the `tiptap` section of `settings.yaml` to register additional wrappers for
marks or to provide lightweight block wrappers without touching the codebase.
The settings are optional; omit the section to rely on the defaults.

```yaml
# settings.yaml
tiptap:
  extra_mark_wrappers:
    highlight: ["==", "=="]
  extra_block_wrappers:
    callout: {prefix: ">>", suffix: ""}
```

* `extra_mark_wrappers` accepts either two-item lists/tuples or dictionaries
  with `prefix`/`suffix` keys.
* `extra_block_wrappers` can wrap custom block content by applying the provided
  prefix and suffix to each rendered line.

If a workflow needs richer handling than simple wrappers (for example custom
HTML output), implement it in code and expose it through the same configuration
hook for a clean upgrade path.

## Duplicate detection

When importing via `POST /documents/tiptap` the service calculates a SHA-256
ingestion hash for the Markdown payload. If an identical document already
exists the request fails with a 400 response instead of creating a duplicate.
Callers that want to re-use the existing record can pass
`link_duplicates=true` at the API layer, which instructs the backend to return
the existing document rather than raising an error.
