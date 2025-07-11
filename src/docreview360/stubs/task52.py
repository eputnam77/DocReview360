"""Terraform template generation utilities."""

from __future__ import annotations

import re

from . import record_task_completion

_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def generate_template(project_name: str) -> str:
    """Return a minimal Terraform template for ``project_name``.

    Parameters
    ----------
    project_name:
        Name used for resources. Must be a valid identifier consisting of
        letters, numbers, underscores or hyphens.

    Raises
    ------
    ValueError
        If ``project_name`` does not match the allowed pattern.
    """

    if not _NAME_RE.match(project_name):
        raise ValueError("project_name must be alphanumeric with optional -/_")

    template = f"""
    terraform {{
      required_version = ">=1.0"
    }}

    resource "aws_s3_bucket" "{project_name}_data" {{
      bucket = "{project_name}-data"
    }}

    resource "aws_db_instance" "{project_name}_db" {{
      engine      = "postgres"
      identifier  = "{project_name}-db"
      instance_class = "db.t3.micro"
    }}
    """

    return template.strip()


def task52(project_name: str = "docreview360") -> str:
    """Generate and return a Terraform template for ``project_name``."""

    record_task_completion(52)
    return generate_template(project_name)
