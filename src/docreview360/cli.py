# SPDX-License-Identifier: MIT
"""Command line interface for DocReview360 configuration wizard."""

from __future__ import annotations

from pathlib import Path

import click
import yaml

from . import ml, rbac
from .config import CONFIG_FILE, Config
from .database import default_url
from .migration import export_instance, import_instance
from .settings_manager import load_settings


@click.group()
def cli() -> None:
    """Main CLI entrypoint for all commands."""
    # The function body intentionally does nothing; ``click`` uses it as a
    # command group.  Having an explicit function makes the entry point clearer.
    return None


@cli.command()
@click.option(
    "--database",
    type=click.Choice(["postgres", "mysql", "sqlite"], case_sensitive=False),
    prompt=True,
)
@click.option(
    "--database-url",
    type=str,
    help="SQLAlchemy database URL. Defaults based on --database if omitted.",
)
@click.option(
    "--editor",
    type=click.Choice(["tiptap", "onlyoffice"], case_sensitive=False),
    default="tiptap",
    show_default=True,
    prompt=True,
)
@click.option(
    "--cms",
    type=click.Choice(
        ["none", "local", "sharepoint", "confluence", "gdrive"],
        case_sensitive=False,
    ),
    default="none",
    show_default=True,
    prompt=True,
)
@click.option(
    "--auth",
    type=click.Choice(
        [
            "oidc",
            "login.gov",
            "auth0",
            "pivcac",
        ],
        case_sensitive=False,
    ),
    default="oidc",
    show_default=True,
    prompt=True,
)
@click.option("--host", default="127.0.0.1", show_default=True, prompt=True)
@click.option("--port", type=int, default=8000, show_default=True, prompt=True)
@click.option("--debug/--no-debug", default=False, show_default=True)
@click.option(
    "--seed/--no-seed",
    default=False,
    help="Create sample document type files after writing config",
)
@click.option(
    "--config-path",
    type=click.Path(dir_okay=False, writable=True),
    default=str(CONFIG_FILE),
    show_default=True,
)
def init(
    database: str,
    editor: str,
    cms: str,
    auth: str,
    host: str,
    port: int,
    debug: bool,
    database_url: str | None,
    seed: bool,
    config_path: str,
) -> None:
    """Interactive configuration wizard.

    Parameters
    ----------
    database:
        Selected database backend.
    editor:
        Preferred document editor.
    cms:
        CMS integration option.
    auth:
        Authentication provider.
    seed:
        When ``True`` a sample Advisory Circular markdown file is created.
    """
    if not (0 < port < 65536):
        raise click.BadParameter("Port must be between 1 and 65535")

    if database_url is None:
        database_url = default_url(database)

    config = Config(
        database=database,
        database_url=database_url,
        editor=editor,
        cms=cms,
        auth=auth,
        host=host,
        port=port,
        debug=debug,
    )
    path = Path(config_path)
    try:
        config.save(path)
        click.echo(f"Configuration written to {path}")
        if seed:
            from .seeds import seed_sample_ac

            sample_path = seed_sample_ac()
            click.echo(f"Sample document written to {sample_path}")
    except OSError as exc:
        raise click.ClickException(f"Failed to write config: {exc}") from exc


@cli.group()
def migrate() -> None:
    """Export or import instance data for migration."""
    return None


@cli.group(name="ml")
def ml_group() -> None:
    """Machine learning utilities for critic models."""

    return None


@ml_group.command(name="train")
@click.argument("corpus", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--critic",
    type=click.Choice(sorted(ml.critic_builders.keys())),
    default="clarity",
    show_default=True,
    help="Critic architecture to train.",
)
@click.option(
    "--update",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Existing torch weights to fine-tune instead of fresh training.",
)
@click.option(
    "--validation",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Optional CSV corpus used to report validation accuracy.",
)
@click.option(
    "--min-accuracy",
    type=float,
    default=0.0,
    show_default=True,
    help="Minimum acceptable validation accuracy (0-1).",
)
@click.option("--quantize/--no-quantize", default=False, show_default=True)
@click.option(
    "--metadata",
    type=(str, str),
    multiple=True,
    help="Extra metadata key/value pairs to embed in the ONNX artefact.",
)
def ml_train(
    corpus: Path,
    output: Path,
    critic: str,
    update: Path | None,
    validation: Path | None,
    min_accuracy: float,
    quantize: bool,
    metadata: tuple[tuple[str, str], ...],
) -> None:
    """Train or update a critic model from labelled CSV data."""

    if not 0.0 <= min_accuracy <= 1.0:
        raise click.BadParameter(
            "--min-accuracy must be between 0 and 1", param_hint="--min-accuracy"
        )

    extra_metadata = {key: value for key, value in metadata}
    try:
        result = ml.train_critic_from_csv(
            corpus,
            output,
            critic_name=critic,
            update_path=update,
            quantize=quantize,
            metadata=extra_metadata,
            validation_path=validation,
        )
    except (RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Saved torch weights to {result.weights_path}")
    click.echo(f"Saved ONNX model to {result.onnx_path} (sha256={result.onnx_sha256})")

    if result.validation is not None:
        message = ml.format_validation_report(result.validation)
        click.echo(message)
        if result.validation.accuracy < min_accuracy:
            raise click.ClickException(
                (
                    f"Validation accuracy {result.validation.accuracy:.2%} "
                    f"is below --min-accuracy {min_accuracy:.2%}"
                )
            )


@ml_group.command(name="benchmark")
@click.argument("model", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--runs", type=int, default=10, show_default=True)
@click.option("--batch-size", type=int, default=32, show_default=True)
def ml_benchmark(model: Path, runs: int, batch_size: int) -> None:
    """Run a quick CPU benchmark against an exported ONNX critic."""

    try:
        result = ml.benchmark_onnx_cpu(model, runs=runs, batch_size=batch_size)
    except ValueError as exc:
        raise click.BadParameter(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise click.ClickException(str(exc)) from exc

    click.echo(
        (
            "Average latency: "
            f"{result.average_ms:.3f} ms (min={result.min_ms:.3f} ms, "
            f"max={result.max_ms:.3f} ms) over {result.runs} run(s) "
            f"@ batch_size={result.batch_size}"
        )
    )


@cli.command()
@click.option(
    "--ml",
    "ml_models",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    multiple=True,
    help="Path(s) to ONNX artefacts to inspect.",
)
def validate(ml_models: tuple[Path, ...]) -> None:
    """Run validation checks across configuration and ML artefacts."""

    if not ml_models:
        click.echo("No validation checks requested.")
        return

    for model_path in ml_models:
        try:
            summary = ml.summarize_model(model_path)
        except Exception as exc:  # pragma: no cover - defensive
            raise click.ClickException(str(exc)) from exc
        click.echo(ml.format_model_summary(summary))


@migrate.command()
@click.argument("path")
def export(path: str) -> None:
    """Export all data to ``path``."""
    target = export_instance(path)
    click.echo(f"Exported data to {target}")


@migrate.command(name="import")
@click.argument("path")
def import_cmd(path: str) -> None:  # "import" is a keyword
    """Import data from ``path`` generated by :func:`export`."""
    try:
        import_instance(path)
        click.echo("Import completed")
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.group()
def rbac_admin() -> None:
    """Manage role definitions stored in ``settings.yaml``."""

    return None


@rbac_admin.command("show")
def rbac_show() -> None:
    """Display the current role to permission mapping."""

    rbac.reload_role_permissions(force=True)
    mapping = rbac.get_role_permissions()
    if not mapping:
        click.echo("No roles defined")
        return
    for role in sorted(mapping):
        permissions = ", ".join(sorted(mapping[role])) or "(no permissions)"
        click.echo(f"{role}: {permissions}")


@rbac_admin.command("set-role")
@click.argument("role")
@click.option(
    "--permission",
    "permissions",
    multiple=True,
    help="Permission to assign to the role (repeat for multiple).",
)
@click.option(
    "--config-path",
    default=lambda: str(rbac.settings_manager.SETTINGS_FILE),
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to the settings file storing role definitions.",
)
@click.option(
    "--merge/--replace",
    default=False,
    show_default=True,
    help="Merge with existing permissions instead of replacing them.",
)
def rbac_set_role(
    role: str,
    permissions: tuple[str, ...],
    config_path: Path,
    merge: bool,
) -> None:
    """Update or create ``role`` with the supplied permissions."""

    normalized_role = role.strip().lower()
    if not normalized_role:
        raise click.BadParameter("Role name must not be empty", param_hint="role")

    normalized_permissions = {perm.strip().lower() for perm in permissions if perm.strip()}

    settings = load_settings(config_path)
    rbac_config = settings.setdefault("rbac", {})
    roles_config = rbac_config.setdefault("roles", {})
    existing: list[str] = []
    if merge and normalized_role in roles_config:
        current = roles_config[normalized_role]
        if isinstance(current, dict):
            candidate = current.get("permissions", [])
        else:
            candidate = current
        if isinstance(candidate, str):
            existing = [candidate]
        elif isinstance(candidate, list):
            existing = [str(item) for item in candidate]
        elif isinstance(candidate, tuple):
            existing = [str(item) for item in candidate]
    normalized_permissions.update(perm.strip().lower() for perm in existing if perm)
    roles_config[normalized_role] = sorted(normalized_permissions)

    try:
        config_path.write_text(yaml.safe_dump(settings, sort_keys=True))
    except OSError as exc:  # pragma: no cover - defensive
        raise click.ClickException(f"Failed to update settings: {exc}") from exc

    rbac.reload_role_permissions(force=True)
    click.echo(f"Updated role '{normalized_role}' with {len(normalized_permissions)} permission(s)")


@cli.group()
def logs() -> None:
    """Audit log utilities."""
    return None


@logs.command("hash-chain")
@click.option("--bucket", default="tamper_proof_store", show_default=True)
@click.option("--key", default="log_chain.json", show_default=True)
@click.option("--batch-size", default=100, show_default=True)
def hash_chain(bucket: str, key: str, batch_size: int) -> None:
    """Compute and store a hash chain of audit logs."""

    from .log_hash_chain import batch_hash_logs

    try:
        batch_hash_logs(bucket=bucket, key=key, batch_size=batch_size)
    except (FileExistsError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("Stored log hash chain")


@logs.command("verify-chain")
@click.option("--bucket", default="tamper_proof_store", show_default=True)
@click.option("--key", default="log_chain.json", show_default=True)
@click.option("--batch-size", default=100, show_default=True)
def verify_chain(bucket: str, key: str, batch_size: int) -> None:
    """Verify the stored audit log hash chain."""

    from .log_hash_chain import verify_hash_chain

    if verify_hash_chain(bucket=bucket, key=key, batch_size=batch_size):
        click.echo("Log integrity verified")
    else:
        raise click.ClickException("Log integrity check failed")


@cli.command("verify-signatures")
@click.option("--scope", default="approved", show_default=True)
@click.option("--document-id", "document_ids", multiple=True)
@click.option("--parallel/--sequential", default=False, show_default=True)
def verify_signatures(scope: str, document_ids: tuple[str, ...], parallel: bool) -> None:
    """Verify document signatures for the given documents.

    When no document IDs are supplied, all approvals in ``scope`` are
    processed. Set ``--parallel`` to process concurrently.
    """

    from services import signature_verifier

    processed = signature_verifier.verify_document_signatures.run(  # type: ignore[attr-defined]
        scope=scope, document_ids=list(document_ids) or None, parallel=parallel
    )
    click.echo(f"Processed {processed} approvals")


# Provide a short alias for the RBAC admin group to match documentation.
cli.add_command(rbac_admin, "rbac")

if __name__ == "__main__":
    cli()
