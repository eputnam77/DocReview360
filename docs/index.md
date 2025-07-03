
# DocuFlow Documentation

Welcome to the DocuFlow project. This site contains a short overview of the
prototype and tips for local development.

For more details, see the [Developer Guide](developer.md).

## Getting started

1. Install the package with `pip install -e .`.
2. Run `python -m docuflow.cli init` to create a configuration file.
3. Launch the API with `uvicorn docuflow.api:app --reload` and open your browser
   to `http://127.0.0.1:8000/`.

## Project features

- In-memory project and document storage
- Minimal JWT authentication flow
- Placeholder React dashboard served from FastAPI

## Contributing

Pull requests are welcome! Please run the test suite with `pytest` and the
linters before submitting changes.

