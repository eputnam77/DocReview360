#!/usr/bin/env python3
"""Deprecated wrapper forwarding to the :mod:`docreview360` ML CLI."""

from __future__ import annotations

import sys

from docreview360.cli import cli

_MESSAGE = (
    "train_fann.py is deprecated and will be removed in a future release. "
    "Please use 'docreview360 ml train' instead."
)


def main() -> None:
    """Forward legacy invocations to ``docreview360 ml train``."""

    sys.stderr.write(_MESSAGE + "\n")
    cli.main(args=["ml", "train", *sys.argv[1:]], prog_name="train_fann")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
