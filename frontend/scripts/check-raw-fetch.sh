#!/usr/bin/env bash
# Fail if any source file in pages/ contains a raw fetch("/api/ call.
# Use authenticatedFetch(`${API}/...`) from lib/api.ts instead.
set -euo pipefail

MATCHES=$(grep -rn --include="*.ts" --include="*.tsx" \
  'fetch\s*(\s*["'"'"'`]\s*/api/' \
  pages/ 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
  echo "ERROR: Raw fetch(\"/api/...\") calls found. Use authenticatedFetch() instead:"
  echo "$MATCHES"
  exit 1
fi

echo "OK: No raw fetch(\"/api/...\") calls found."
