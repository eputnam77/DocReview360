#!/usr/bin/env bash
# Compatibility wrapper for the maintained Node implementation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "${SCRIPT_DIR}/check-raw-fetch.mjs"
