"""Terraform module loader for optional infrastructure."""

from __future__ import annotations

from importlib.resources import files

VALID_MODULES = {"eks", "rds", "elasticache"}


def get_template(name: str) -> str:
    """Return the Terraform template named ``name``.

    Parameters
    ----------
    name:
        One of :data:`VALID_MODULES`.

    Raises
    ------
    ValueError
        If ``name`` is not a valid module name.
    """

    if name not in VALID_MODULES:
        raise ValueError(f"unknown module: {name}")
    return files(__name__).joinpath(f"{name}.tf").read_text()
