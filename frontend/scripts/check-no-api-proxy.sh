#!/usr/bin/env bash
# Fail if any source file imports from lib/apiProxy.
# apiProxy.ts was removed in R-17; use authenticatedFetch() from lib/api.ts instead.
set -euo pipefail

MATCHES=$(grep -rn --include="*.ts" --include="*.tsx" \
  'from.*lib/apiProxy\|from.*apiProxy' \
  . --exclude-dir=node_modules --exclude-dir=.next 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
  echo "ERROR: Import of apiProxy found. Use authenticatedFetch() from lib/api.ts instead:"
  echo "$MATCHES"
  exit 1
fi

echo "OK: No apiProxy imports found."
