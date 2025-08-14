# DocReview360 Documentation

Welcome to the DocReview360 project. This site collects guides and references for running the prototype and exploring its features.

- [Getting Started](getting_started.md)
- [CLI Reference](cli.md)
- [UI Guide](ui.md)
- [API Overview](api_overview.md)
- [Usage Scenarios](scenarios.md)
- [Developer Guide](developer.md)
- [Deployment](deployment.md)
- [AI Workflow](ai_workflow.md)

## Project features

DocReview360 implements a small slice of the functionality described in the product requirements. The prototype shows:

- In-memory project and document storage with sequential numbering
- Import and export of Markdown and DOCX files
- Basic search with saved queries
- Plugin registry for editors, exporters and validators
- Minimal authentication flow with login, projects page and project creation page
- Built-in observability helpers exposing Prometheus metrics and optional Sentry reporting

Pull requests are welcome! Please run the unit tests with `pytest` and the end-to-end suite with `pytest -m e2e` before submitting changes.

- [User Guide](user_guide.md)
- [Latest Features](latest_features.md)

## License

This project is released under the GNU General Public License v3.0. See the LICENSE file for details.
