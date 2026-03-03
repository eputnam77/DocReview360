from docreview360.api import app

# Snapshot of selected public contract surface for v0.1.
EXPECTED_PATH_METHODS = {
    "/ping": ["get"],
    "/token": ["post"],
    "/login": ["post"],
    "/projects": ["get", "post"],
    "/approvals": ["get", "post"],
    "/config": ["get", "put"],
    "/branding": ["get"],
}


def test_openapi_selected_path_method_snapshot() -> None:
    schema = app.openapi()
    paths = schema.get("paths", {})

    for path, expected_methods in EXPECTED_PATH_METHODS.items():
        assert path in paths, f"Missing path in OpenAPI schema: {path}"
        methods = sorted(paths[path].keys())
        assert methods == expected_methods, f"OpenAPI method mismatch for {path}: {methods}"


