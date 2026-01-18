"""ONNX Runtime helpers with lazy session caching."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

import numpy as np
import onnxruntime as ort

__all__ = [
    "ModelMetadata",
    "clear_session_cache",
    "get_model_metadata",
    "get_session",
    "infer",
    "metadata_to_context",
]


_DEFAULT_PROVIDERS: tuple[str, ...] = ("CPUExecutionProvider",)


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata summary extracted from an ONNX model."""

    path: Path
    sha256: str
    version: str | None
    custom_metadata: Mapping[str, str]


_SESSION_CACHE: MutableMapping[tuple[Path, tuple[str, ...]], ort.InferenceSession] = {}
_METADATA_CACHE: MutableMapping[Path, ModelMetadata] = {}
_LOCK = threading.Lock()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_custom_metadata(path: Path) -> dict[str, str]:
    try:
        import onnx
    except ModuleNotFoundError:
        return {}

    model = onnx.load_model(path)
    return {item.key: item.value for item in model.metadata_props}


def _prepare_providers(providers: Sequence[str] | None) -> list[str]:
    requested = list(providers) if providers else list(_DEFAULT_PROVIDERS)
    available = set(ort.get_available_providers())
    missing = [p for p in requested if p not in available]
    if missing:
        raise RuntimeError("Missing execution providers: " + ", ".join(missing))
    return requested


def get_session(
    path: str | Path, *, providers: Sequence[str] | None = None
) -> ort.InferenceSession:
    """Return a cached :class:`onnxruntime.InferenceSession` for ``path``."""

    model_path = Path(path).resolve()
    resolved_providers = _prepare_providers(providers)
    key = (model_path, tuple(resolved_providers))

    with _LOCK:
        session = _SESSION_CACHE.get(key)  # type: ignore[arg-type]
        if session is None:
            session = ort.InferenceSession(str(model_path), providers=resolved_providers)
            _SESSION_CACHE[key] = session  # type: ignore[index]
        return session


def clear_session_cache() -> None:
    """Drop all cached inference sessions."""

    with _LOCK:
        _SESSION_CACHE.clear()
        _METADATA_CACHE.clear()


def infer(
    session_or_path: ort.InferenceSession | str | Path,
    inputs: Mapping[str, np.ndarray],
) -> list[np.ndarray]:
    """Run inference using ``inputs`` returning the raw outputs."""

    if isinstance(session_or_path, ort.InferenceSession):
        session = session_or_path
    else:
        session = get_session(session_or_path)
    return session.run(None, dict(inputs))


def get_model_metadata(
    session_or_path: ort.InferenceSession | str | Path,
) -> ModelMetadata:
    """Return :class:`ModelMetadata` extracted from the ONNX artefact."""

    if isinstance(session_or_path, ort.InferenceSession):
        session = session_or_path
        path = Path(session._model_path).resolve()  # type: ignore[attr-defined]
    else:
        path = Path(session_or_path).resolve()
        session = get_session(path)

    with _LOCK:
        cached = _METADATA_CACHE.get(path)
        if cached is not None:
            return cached

    meta = session.get_modelmeta()
    custom_metadata = _read_custom_metadata(path)
    if not custom_metadata:
        custom_metadata = dict(meta.custom_metadata_map or {})

    info = ModelMetadata(
        path=path,
        sha256=_hash_file(path),
        version=meta.graph_name or meta.version,  # prefer descriptive names
        custom_metadata=custom_metadata,
    )

    with _LOCK:
        _METADATA_CACHE[path] = info
    return info


def metadata_to_context(meta: ModelMetadata | None) -> dict[str, str] | None:
    """Return a serialisable summary for ``meta`` including hash and version."""

    if meta is None:
        return None
    context: dict[str, str] = {"sha256": meta.sha256, "path": str(meta.path)}
    if meta.version:
        context["version"] = meta.version
    for key, value in meta.custom_metadata.items():
        context[key] = str(value)
    return context
