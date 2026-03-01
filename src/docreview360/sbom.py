"""CycloneDX SBOM generation helpers for DocReview360."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class SBOMComponent:
    """Dependency component included in the SBOM."""

    ecosystem: str
    name: str
    version: str


def _read_project_version(pyproject_path: Path) -> str:
    if not pyproject_path.exists():
        return "unknown"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    if isinstance(project, dict):
        version = project.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    return "unknown"


def _load_python_components(poetry_lock_path: Path) -> list[SBOMComponent]:
    if not poetry_lock_path.exists():
        return []
    data = tomllib.loads(poetry_lock_path.read_text(encoding="utf-8"))
    packages = data.get("package", [])
    components: list[SBOMComponent] = []
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        name = str(pkg.get("name", "")).strip()
        version = str(pkg.get("version", "")).strip()
        if not name or not version:
            continue
        components.append(SBOMComponent(ecosystem="pypi", name=name, version=version))
    return components


def _load_frontend_components(package_lock_path: Path) -> list[SBOMComponent]:
    if not package_lock_path.exists():
        return []
    data = json.loads(package_lock_path.read_text(encoding="utf-8"))
    packages = data.get("packages", {})
    if not isinstance(packages, dict):
        return []

    components: list[SBOMComponent] = []
    for key, value in packages.items():
        if not isinstance(value, dict):
            continue
        if key == "":
            continue
        version = str(value.get("version", "")).strip()
        if not version:
            continue

        name = str(value.get("name", "")).strip()
        if not name and isinstance(key, str) and key.startswith("node_modules/"):
            name = key.split("node_modules/", 1)[1]
        if not name:
            continue

        components.append(SBOMComponent(ecosystem="npm", name=name, version=version))

    return components


def _component_to_cyclonedx(component: SBOMComponent) -> dict[str, Any]:
    safe_name = component.name.replace(" ", "-")
    return {
        "type": "library",
        "name": component.name,
        "version": component.version,
        "bom-ref": f"{component.ecosystem}:{safe_name}@{component.version}",
        "purl": f"pkg:{component.ecosystem}/{safe_name}@{component.version}",
    }


def generate_cyclonedx_sbom(
    output_path: Path,
    *,
    poetry_lock_path: Path | None = None,
    package_lock_path: Path | None = None,
    pyproject_path: Path | None = None,
) -> Path:
    """Generate a CycloneDX JSON SBOM and return the output path."""

    poetry_lock = poetry_lock_path or Path("poetry.lock")
    package_lock = package_lock_path or Path("frontend/package-lock.json")
    pyproject = pyproject_path or Path("pyproject.toml")

    all_components = _load_python_components(poetry_lock) + _load_frontend_components(package_lock)
    deduped = sorted({(c.ecosystem, c.name, c.version) for c in all_components})

    components_payload = [
        _component_to_cyclonedx(SBOMComponent(ecosystem=e, name=n, version=v))
        for (e, n, v) in deduped
    ]

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tools": [
                {
                    "vendor": "DocReview360",
                    "name": "docreview360-sbom-generator",
                    "version": "1",
                }
            ],
            "component": {
                "type": "application",
                "name": "docreview360",
                "version": _read_project_version(pyproject),
            },
        },
        "components": components_payload,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bom, indent=2, sort_keys=True), encoding="utf-8")
    return output_path
