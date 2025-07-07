# CLI Reference

DocuFlow ships with a single entry point called `docuflow`. The command wraps a few sub‑commands implemented with a friendly wizard style.

## init

```
docuflow init [OPTIONS]
```

Interactive wizard that generates `docuflow.yml`.

### Options

| Option | Description |
| ------ | ----------- |
| `--database [postgres|mysql|sqlite]` | Choose the database backend. |
| `--editor [tiptap]` | Select the default editor. |
| `--cms [none|local]` | CMS integration option. |
| `--auth [oidc]` | Authentication provider. |
| `--host TEXT` | API host address. |
| `--port INTEGER` | API port number. |
| `--debug / --no-debug` | Toggle debug mode. |
| `--config-path PATH` | Where to write the configuration file. |

All options are prompted interactively so you can simply press Enter to accept the defaults. The resulting file records your choices and can be modified later.
