# CLI reference

DocReview360 installs a single command, `docreview360`. Run `docreview360 COMMAND --help` for details on any command.

| Command | Purpose |
| --- | --- |
| [`init`](#init) | Generate a configuration file |
| [`serve`](#serve) | Start the API server |
| [`migrate`](#migrate) | Apply migrations, or export and import instance data |
| [`capabilities`](#capabilities) | Show which optional features are installed |
| [`logs`](#logs) | Hash and verify the audit log |
| [`rbac`](#rbac) | Manage roles and permissions |
| [`verify-signatures`](#verify-signatures) | Verify document signatures |
| [`validate`](#validate) | Check configuration and ML artifacts |
| [`frontend`](#frontend) | Inspect or extract the bundled frontend build |
| [`ml`](#ml) | Train, export, and evaluate critic models |

## init

Generate `docreview360.yaml` with an interactive wizard.

```bash
docreview360 init [OPTIONS]
```

Every option is prompted, so press Enter to accept the defaults.

| Option | Description |
| --- | --- |
| `--database` | `postgres`, `mysql`, or `sqlite` |
| `--database-url TEXT` | SQLAlchemy connection string |
| `--editor` | `ckeditor5`, `tiptap`, `onlyoffice`, or `prosemirror`. Defaults to `tiptap` |
| `--cms` | `none`, `local`, `sharepoint`, `confluence`, or `gdrive` |
| `--auth` | `local`, `oidc`, `login.gov`, `auth0`, `pivcac`, `keycloak`, `okta`, `azure-ad`, or `saml` |
| `--host TEXT` | API host address |
| `--port INTEGER` | API port number |
| `--debug / --no-debug` | Toggle debug mode |
| `--seed / --no-seed` | Create sample document files after setup |
| `--config-path PATH` | Where to write the configuration file |

If you omit `--database-url`, the wizard uses a driver-specific default:

| Database | Default URL |
| --- | --- |
| PostgreSQL | `postgresql+psycopg://docreview360:docreview360@localhost:5432/docreview360` |
| MySQL | `mysql+pymysql://docreview360:docreview360@localhost:3306/docreview360` |
| SQLite | `sqlite:///docreview360.db` |

## serve

Start the API server.

```bash
docreview360 serve [--host HOST] [--port PORT] [--reload/--no-reload]
```

Release wheels bundle a built frontend asset. From a source checkout, run the Next.js dev server separately.

## migrate

Apply migrations, or move an instance between environments.

```bash
docreview360 migrate                                  # apply packaged migrations
docreview360 migrate --migrations-path DIRECTORY      # apply your own
docreview360 migrate export backup.gz                 # export all data
docreview360 migrate import backup.gz                 # import an export
```

The export is a gzip archive containing documents, logs, and document types. Migrations are forward-only; see [Migration policy](migration_policy.md).

## capabilities

Show which runtime capabilities are installed, configured, or need an optional extra.

```bash
docreview360 capabilities
```

Extras include `docreview360[postgres]`, `docreview360[worker]`, and `docreview360[ml-cpu]`.

## logs

Audit log utilities.

```bash
docreview360 logs hash-chain     # compute and store the hash chain
docreview360 logs verify-chain   # verify the stored chain
```

`verify-chain` exits non-zero if any entry was altered or is missing. See [Audit log schema](audit_log_schema.md).

## rbac

Manage role definitions stored in `settings.yaml`. `rbac-admin` is an alias for this command.

```bash
docreview360 rbac show                       # show the role-to-permission map
docreview360 rbac set-role ROLE PERMISSIONS  # create or update a role
```

See [RBAC configuration](rbac_configuration.md).

## verify-signatures

Verify document signatures. With no document IDs, every approval in `--scope` is processed.

```bash
docreview360 verify-signatures [OPTIONS]
```

| Option | Description |
| --- | --- |
| `--scope TEXT` | Approval scope filter. Defaults to `approved` |
| `--document-id TEXT` | Verify a specific document. Repeatable |
| `--parallel / --sequential` | Process concurrently or one at a time. Defaults to sequential |

## validate

Run validation checks across configuration and ML artifacts.

```bash
docreview360 validate [--ml FILE]
```

Pass `--ml` one or more times to inspect ONNX artifacts.

## frontend

Inspect or extract the frontend build bundled into release wheels.

```bash
docreview360 frontend path                  # print the bundled asset directory
docreview360 frontend extract DESTINATION   # copy the assets somewhere
```

Use `extract` to serve the frontend from your own web server or CDN.

## ml

Train, export, and evaluate the critic models. Artifacts are written to `artifacts/` so you can track models over time.

Requires an ML extra, such as `docreview360[ml]` or `docreview360[ml-cpu]`.

### train

```bash
docreview360 ml train [--epochs 5] [--lr 3e-5]
```

Fine-tunes the PyTorch classifier using the feature schema in `schemas/features.json`. Writes:

- `artifacts/models/latest.pt` — most recent checkpoint
- `artifacts/metrics/latest.json` — loss, accuracy, and confusion matrix

### export

```bash
docreview360 ml export [--opset 18] [--quantize dynamic|static] [--calibration-set PATH]
```

Converts the checkpoint to ONNX, optionally with quantization:

| Goal | Command |
| --- | --- |
| Floating-point graph | `docreview360 ml export` |
| INT8 graph tuned for CPU | `docreview360 ml export --quantize dynamic` |
| Calibrated INT8 graph | `docreview360 ml export --quantize static --calibration-set data/calibration/` |

Output lands in `artifacts/models/`, tagged with the export timestamp.

### package

```bash
docreview360 ml package [--include-tokenizer]
```

Bundles the ONNX model, feature schema, metrics, and optional tokenizer into `artifacts/packages/<timestamp>/`. Copy that folder into your image and point `DOCREVIEW360_ML_MODEL_DIR` at it.

### eval

```bash
docreview360 ml eval [--baseline scikit]
```

Runs evaluation suites against the exported ONNX graph. With `--baseline scikit`, also fits a scikit-learn baseline on the same features and prints a delta table for accuracy, precision, recall, and ROC AUC.

### test

```bash
docreview360 ml test --suite golden|regression
```

Golden tests check label stability. Regression tests stress varied document structures. Failures abort deployment.

### info

```bash
docreview360 ml info
```

Shows the packaged model, detected ONNX Runtime providers, and the expected input schema. Start here when troubleshooting provider errors or confirming a quantized graph loaded.

See [ML operations](ml/operations.md) for the full workflow.
