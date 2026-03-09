# CLI Reference

DocReview360 ships with a single entry point called `docreview360`. The command wraps a few sub-commands implemented with a friendly wizard style.

## init

```
docreview360 init [OPTIONS]
```

Interactive wizard that generates `docreview360.yaml`.

### Options

| Option | Description |
| ------ | ----------- |
| `--database [postgres|mysql|sqlite]` | Choose the database backend. |
| `--database-url TEXT` | SQLAlchemy connection string. |
| `--editor [tiptap]` | Select the document editor (TipTap by default). |
| `--cms [none|local|sharepoint|confluence|gdrive]` | CMS integration option. |
| `--auth [oidc]` | Authentication provider. |
| `--host TEXT` | API host address. |
| `--port INTEGER` | API port number. |
| `--debug / --no-debug` | Toggle debug mode. |
| `--seed / --no-seed` | Create sample document files after setup. |
| `--config-path PATH` | Where to write the configuration file. |

All options are prompted interactively so you can simply press Enter to accept the defaults. The resulting file records your choices and can be modified later.

If `--database-url` is omitted the wizard uses driver-specific defaults:

- Postgres -> `postgresql+psycopg://docreview360:docreview360@localhost:5432/docreview360`
- MySQL -> `mysql+pymysql://docreview360:docreview360@localhost:3306/docreview360`
- SQLite -> `sqlite:///docreview360.db`

## migrate

```
docreview360 migrate [export|import] PATH
```

Export or import an entire instance for migration. The command writes a gzip
archive containing documents, logs and document types which can be restored on
another environment.

## logs

```
docreview360 logs [hash-chain|verify-chain]
```

Audit log utilities.

### hash-chain

```
docreview360 logs hash-chain
```

Compute and store a tamper-evident hash chain over all audit log entries.

### verify-chain

```
docreview360 logs verify-chain
```

Verify the stored audit log hash chain. Exits non-zero if any entry has been
tampered with or is missing.

---

## rbac

```
docreview360 rbac [show|set-role]
```

Manage role definitions stored in `docreview360.yaml`.

### show

```
docreview360 rbac show
```

Display the current role-to-permission mapping.

### set-role

```
docreview360 rbac set-role ROLE PERMISSIONS...
```

Update or create `role` with the supplied permission list.

---

## validate

```
docreview360 validate [--ml FILE...]
```

Run validation checks across configuration and ML artifacts. Pass one or more
`--ml FILE` paths to inspect ONNX artifacts.

---

## verify-signatures

```
docreview360 verify-signatures [OPTIONS]
```

Verify document signatures. When no document IDs are supplied, all approvals
in `--scope` are processed.

### Options

| Option | Description |
| ------ | ----------- |
| `--scope TEXT` | Approval scope filter (default: `approved`). |
| `--document-id TEXT` | Verify a specific document (repeatable). |
| `--parallel / --sequential` | Process concurrently or sequentially (default: sequential). |

---

## ml

Machine-learning helpers live under the `ml` namespace. Each command writes
artifacts to `artifacts/` so you can track models over time.

### train

```
docreview360 ml train [--epochs 5] [--lr 3e-5]
```

Fine-tunes the PyTorch classifier using the feature schema defined in
`schemas/features.json`. Outputs include:

- `artifacts/models/latest.pt` -- most recent checkpoint.
- `artifacts/metrics/latest.json` -- training loss, accuracy, and confusion
  matrix snapshots.

### export

```
docreview360 ml export [--opset 18] [--quantize dynamic|static] [--calibration-set PATH]
```

Converts the PyTorch checkpoint to ONNX and optionally applies quantisation.
Common patterns:

1. `docreview360 ml export` -- emit a floating-point ONNX graph.
2. `docreview360 ml export --quantize dynamic` -- generate an INT8 graph optimised
   for CPUs.
3. `docreview360 ml export --quantize static --calibration-set data/calibration/`
   -- calibrate with held-out samples.

Outputs land in `artifacts/models/` and are tagged with the export timestamp.

### package

```
docreview360 ml package [--include-tokenizer]
```

Bundles the ONNX model, feature schema, metrics, and optional tokenizer files
into `artifacts/packages/<timestamp>/`. Use the resulting folder for container
deployments--copy it to your image and set `DOCREVIEW360_ML_MODEL_DIR`.

### eval

```
docreview360 ml eval [--baseline scikit]
```

Runs evaluation suites against the exported ONNX graph. When `--baseline scikit`
is present the CLI also fits a scikit-learn baseline on the same features and
prints a delta table covering accuracy, precision, recall, and ROC AUC.

### test

```
docreview360 ml test --suite [golden|regression]
```

Executes deterministic test suites. Golden tests validate label stability while
regression tests stress varied document structures. Failures abort deployment so
you can investigate before promoting the model.

### info

```
docreview360 ml info
```

Displays the currently packaged model, detected ONNX Runtime providers, and
expected input schema. Useful when troubleshooting provider errors or verifying
that a quantised graph loaded correctly.

