#!/usr/bin/env bash
set -euo pipefail

NEXT_AGENT=""
if [[ -n "${GITHUB_EVENT_NAME:-}" ]]; then
  echo "Detecting next agent from commit message"
  message=$(git log -1 --pretty=%B)
  if [[ $message =~ ready-for:([a-zA-Z-]+) ]]; then
    NEXT_AGENT="${BASH_REMATCH[1]}"
  fi
fi

echo "NEXT_AGENT=$NEXT_AGENT" >> "$GITHUB_ENV"
