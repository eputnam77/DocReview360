# Fix GitHub push: remove `.dev/runtime-logs/` from history

GitHub rejected the push because `.dev/runtime-logs/backend.err.log` is 325 MB (limit 100 MB).

## What’s already done

- **`.gitignore`** – `.dev/runtime-logs/` was added so these logs are not committed again.
- **History rewrite** – A `git filter-branch` was started to remove `.dev/runtime-logs/` from all commits on `main` (2423 commits, ~10–11 minutes).

## After filter-branch finishes

1. **Restore the .gitignore change** (it was stashed):
   ```powershell
   cd "c:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360"
   git stash pop
   git add .gitignore
   git commit -m "chore: ignore .dev/runtime-logs to prevent large log commits"
   ```

2. **Force-push the rewritten history** (required because history changed):
   ```powershell
   git push --force-with-lease origin main
   ```
   If anyone else has pulled the old history, they must re-clone or reset their branch after you force-push.

3. **Optional – remove backup ref** (frees space; only after you’re sure the push is good):
   ```powershell
   git update-ref -d refs/original/refs/heads/main
   ```

## If you cancelled filter-branch and want a faster fix

Only the last few commits (from `5716a0e` onward) contain the large file. You can rewrite just those instead of all 2423 commits:

1. **Restore pre–filter-branch state** (if you cancelled mid-run):
   ```powershell
   git reset --hard refs/original/refs/heads/main
   ```

2. **Rewrite only the commits that introduced/contain the file** (5 commits, ~10 seconds):
   ```powershell
   $env:FILTER_BRANCH_SQUELCH_WARNING=1
   git filter-branch --force --index-filter "git rm -rf --cached --ignore-unmatch .dev/runtime-logs/" --prune-empty 5716a0e^..main
   ```

3. Then do **steps 1–3** from “After filter-branch finishes” above (stash pop, commit .gitignore, force-push).

## Summary

- **Cause:** `.dev/runtime-logs/` (including a 325 MB log) was committed; GitHub rejects files > 100 MB.
- **Fix:** Remove that path from history (filter-branch), add `.dev/runtime-logs/` to `.gitignore`, then force-push.
- **Prevention:** `.gitignore` is updated so these logs are not tracked again.
