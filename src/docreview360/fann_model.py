# SPDX-License-Identifier: MIT
"""Deprecated legacy module replaced by :mod:`docreview360.ml.torch_models`."""

from __future__ import annotations

import warnings

warnings.warn(
    "docreview360.fann_model has been removed; use docreview360.ml.torch_models instead",
    DeprecationWarning,
    stacklevel=2,
)

raise RuntimeError(
    "docreview360.fann_model is no longer available. "
    "Import from docreview360.ml.torch_models instead."
)
