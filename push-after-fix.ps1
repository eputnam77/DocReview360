# Run this script AFTER git filter-branch has finished (rewriting 2423 commits).
# It restores .gitignore, commits it, and force-pushes to resolve the large-file push failure.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1. Restore .gitignore change from stash
git stash pop
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Stash pop had conflicts or failed. If .gitignore already has .dev/runtime-logs/, add and commit it manually, then run: git push --force-with-lease origin main"
    exit 1
}

# 2. Commit .gitignore so runtime logs are never committed again
git add .gitignore
git commit -m "chore: ignore .dev/runtime-logs to prevent large log commits"

# 3. Force-push rewritten history (required because we rewrote history)
git push --force-with-lease origin main

Write-Host "Done. If you want to remove the filter-branch backup ref to free space, run: git update-ref -d refs/original/refs/heads/main"
