# SPDX-License-Identifier: MIT
"""Runtime capability registry for optional DocReview360 features."""

from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Capability:
    """Describes whether a feature is installed and ready to configure."""

    id: str
    label: str
    category: str
    description: str
    core: bool
    installed: bool
    configured: bool
    install_extra: str | None = None
    blockers: tuple[str, ...] = field(default_factory=tuple)

    def asdict(self) -> dict[str, object]:
        """Return a JSON-serialisable capability mapping."""

        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _missing_modules(module_names: Iterable[str]) -> tuple[str, ...]:
    return tuple(name for name in module_names if not _has_module(name))


def _optional_capability(
    *,
    id: str,
    label: str,
    category: str,
    description: str,
    install_extra: str,
    modules: tuple[str, ...],
    configured: bool = False,
) -> Capability:
    missing = _missing_modules(modules)
    return Capability(
        id=id,
        label=label,
        category=category,
        description=description,
        core=False,
        installed=not missing,
        configured=configured and not missing,
        install_extra=install_extra,
        blockers=tuple(f"Missing Python module: {module}" for module in missing),
    )


def _packaged_editor_capability(*, id: str, label: str, description: str) -> Capability:
    return Capability(
        id=id,
        label=label,
        category="editor",
        description=description,
        core=False,
        installed=False,
        configured=False,
        blockers=("This editor is not included in the core frontend bundle.",),
    )


def _frontend_bundle_available() -> bool:
    try:
        from .frontend_assets import frontend_source_root

        frontend_source_root()
    except Exception:
        return False
    return True


def list_capabilities() -> list[Capability]:
    """Return all known core and optional runtime capabilities."""

    frontend_available = _frontend_bundle_available()
    core = [
        Capability(
            id="core_review",
            label="Core document review",
            category="core",
            description=(
                "Projects, documents, workflows, approvals, comments, audit logs, "
                "and reviewers."
            ),
            core=True,
            installed=True,
            configured=True,
        ),
        Capability(
            id="sqlite",
            label="SQLite database",
            category="database",
            description="Built-in single-database storage for lightweight deployments.",
            core=True,
            installed=True,
            configured=True,
        ),
        Capability(
            id="tiptap_editor",
            label="TipTap editor",
            category="editor",
            description="Default in-app document authoring and review experience.",
            core=True,
            installed=True,
            configured=True,
        ),
        Capability(
            id="notifications",
            label="Email, Slack, Teams, and webhook notifications",
            category="notification",
            description=(
                "Config-backed outbound notification channels using built-in HTTP/email "
                "helpers."
            ),
            core=True,
            installed=True,
            configured=True,
        ),
        Capability(
            id="frontend_bundle",
            label="Packaged frontend bundle",
            category="frontend",
            description="Built frontend artifact packaged with the Python distribution.",
            core=True,
            installed=frontend_available,
            configured=frontend_available,
            blockers=() if frontend_available else ("No built frontend bundle was packaged.",),
        ),
    ]
    optional = [
        _optional_capability(
            id="postgres",
            label="PostgreSQL database",
            category="database",
            description="Production database driver for PostgreSQL deployments.",
            install_extra="postgres",
            modules=("psycopg",),
        ),
        _optional_capability(
            id="mysql",
            label="MySQL database",
            category="database",
            description="Production database driver for MySQL deployments.",
            install_extra="mysql",
            modules=("pymysql",),
        ),
        _optional_capability(
            id="mssql",
            label="Microsoft SQL Server database",
            category="database",
            description="Production database driver for SQL Server deployments.",
            install_extra="mssql",
            modules=("pyodbc",),
        ),
        _optional_capability(
            id="oracle",
            label="Oracle database",
            category="database",
            description="Production database driver for Oracle deployments.",
            install_extra="oracle",
            modules=("oracledb",),
        ),
        _optional_capability(
            id="worker",
            label="Background worker",
            category="runtime",
            description="Celery and Redis support for scheduled/background jobs.",
            install_extra="worker",
            modules=("celery", "redis"),
        ),
        _optional_capability(
            id="ml_runtime",
            label="ML scoring runtime",
            category="ml",
            description=(
                "NumPy and ONNX Runtime for quality, compliance, routing, and "
                "signature scoring."
            ),
            install_extra="ml-cpu",
            modules=("numpy", "onnxruntime"),
        ),
        _optional_capability(
            id="ml_training",
            label="ML training and export",
            category="ml",
            description="Torch and ONNX tooling for training/exporting critic models.",
            install_extra="ml",
            modules=("numpy", "torch", "onnx"),
        ),
        _optional_capability(
            id="saml",
            label="SAML authentication",
            category="auth",
            description="Enterprise SAML service-provider authentication.",
            install_extra="saml",
            modules=("onelogin",),
        ),
        _optional_capability(
            id="ldap",
            label="LDAP authentication",
            category="auth",
            description="LDAP/Active Directory authentication support.",
            install_extra="ldap",
            modules=("ldap3",),
        ),
        _optional_capability(
            id="webauthn",
            label="WebAuthn MFA",
            category="auth",
            description="FIDO2/WebAuthn authentication support.",
            install_extra="webauthn",
            modules=("webauthn",),
        ),
        _optional_capability(
            id="sharepoint",
            label="SharePoint CMS",
            category="cms",
            description="SharePoint document storage integration.",
            install_extra="cms-sharepoint",
            modules=("requests",),
        ),
        _packaged_editor_capability(
            id="ckeditor_editor",
            label="CKEditor",
            description="Optional CKEditor document editing experience.",
        ),
        _packaged_editor_capability(
            id="onlyoffice_editor",
            label="OnlyOffice",
            description="Optional OnlyOffice document editing integration.",
        ),
        _packaged_editor_capability(
            id="oxygen_editor",
            label="Oxygen XML Web Author",
            description="Optional Oxygen XML Web Author integration.",
        ),
        _optional_capability(
            id="realtime_collaboration",
            label="Realtime collaboration",
            category="editor",
            description="Yjs-backed realtime collaboration server support.",
            install_extra="realtime",
            modules=("y_py", "ypy_websocket"),
        ),
    ]
    return [*core, *optional]


def capabilities_payload() -> dict[str, object]:
    """Return the registry payload exposed by CLI/API/UI surfaces."""

    capabilities = list_capabilities()
    return {
        "capabilities": [capability.asdict() for capability in capabilities],
        "summary": {
            "total": len(capabilities),
            "installed": sum(1 for capability in capabilities if capability.installed),
            "core_ready": all(
                capability.installed for capability in capabilities if capability.core
            ),
        },
    }
