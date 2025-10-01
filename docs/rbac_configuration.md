# Configuring role-based permissions

DocReview360 ships with a conservative default role matrix, but deployments
often need to tune the available permissions.  Role definitions are now loaded
from `settings.yaml` so that operators can customise them without modifying
code.

## settings.yaml structure

Add an `rbac.roles` section to `settings.yaml`.  Each entry maps a role name to a
list of permissions.  Roles not explicitly listed fall back to the built-in
defaults.

```yaml
rbac:
  roles:
    admin:
      - create
      - read
      - update
      - delete
      - view_audit_log
    reviewer:
      - read
    verifier:
      - verification_override
```

Role and permission names are normalised to lowercase.  Empty lists are valid
and effectively remove all permissions from a role.

## CLI helpers

The `docreview360` CLI exposes utilities for reviewing and updating the mapping:

```shell
docreview360 rbac-admin show
```

prints the current role matrix, while

```shell
docreview360 rbac-admin set-role manager --permission create --permission read
```

replaces the `manager` definition.  Pass `--merge` to append permissions without
removing existing ones and `--config-path` to update a non-standard settings
location.

## Runtime behaviour

Role permissions are cached and automatically reloaded when `settings.yaml`
changes.  Updates immediately influence authorisation checks and invalidate any
cached view of the mapping exposed by the CLI.
