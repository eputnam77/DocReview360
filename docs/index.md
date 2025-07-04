# DocuFlow Documentation

Welcome to the DocuFlow project. This site collects guides and references for running the prototype and exploring its features.

- [Getting Started](getting_started.md)
- [CLI Reference](cli.md)
- [UI Guide](ui.md)
- [API Overview](api_overview.md)
- [Usage Scenarios](scenarios.md)
- [Developer Guide](developer.md)

## Project features

DocuFlow implements a small slice of the functionality described in the product requirements. The prototype demonstrates:

- In-memory project and document storage with sequential numbering
- Import and export of Markdown and DOCX files
- Basic search with saved queries
- Plugin registry for editors, exporters and validators
- Minimal authentication flow with login, dashboard and project creation page
- Built-in observability helpers exposing Prometheus metrics and optional Sentry reporting

Pull requests are welcome! Please run the test suite with `pytest` and the linters before submitting changes.
