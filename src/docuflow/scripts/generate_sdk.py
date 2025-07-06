"""Generate SDK from the FastAPI schema."""

from __future__ import annotations

import subprocess
from pathlib import Path

from docuflow.stubs import record_task_completion


def generate(output: str = "packages/sdk-ts") -> None:
    """Generate the client SDK using openapi-python-client."""
    schema_path = Path("openapi.json")
    subprocess.run(
        [
            "openapi-python-client",
            "generate",
            "--path",
            str(schema_path),
            "--custom-template-path",
            "templates/sdk",
            "--output",
            output,
        ],
        check=True,
    )
    record_task_completion(138)


if __name__ == "__main__":
    generate()
