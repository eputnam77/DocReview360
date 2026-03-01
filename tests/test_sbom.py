import json
from pathlib import Path

from docreview360.sbom import generate_cyclonedx_sbom


def test_generate_cyclonedx_sbom(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "docreview360"
version = "0.1.2"
""".strip(),
        encoding="utf-8",
    )

    poetry_lock = tmp_path / "poetry.lock"
    poetry_lock.write_text(
        """
[[package]]
name = "requests"
version = "2.32.0"

[[package]]
name = "pydantic"
version = "2.11.7"
""".strip(),
        encoding="utf-8",
    )

    package_lock = tmp_path / "package-lock.json"
    package_lock.write_text(
        json.dumps(
            {
                "name": "frontend",
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "frontend", "version": "1.0.0"},
                    "node_modules/react": {"version": "18.2.0"},
                },
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "sbom" / "docreview360.cdx.json"
    generated = generate_cyclonedx_sbom(
        output,
        poetry_lock_path=poetry_lock,
        package_lock_path=package_lock,
        pyproject_path=pyproject,
    )

    payload = json.loads(generated.read_text(encoding="utf-8"))
    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.5"
    assert payload["metadata"]["component"]["version"] == "0.1.2"

    components = {(c["name"], c["version"]) for c in payload["components"]}
    assert ("requests", "2.32.0") in components
    assert ("pydantic", "2.11.7") in components
    assert ("react", "18.2.0") in components
