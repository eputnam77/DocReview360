# Nightly Test Workflows - Quick Start

## What Was Created

I've set up a **GitHub Actions workflow** for nightly testing of DocReview360:

### Nightly Tests Workflow (`nightly-tests.yml`)
- ✅ Runs tests every night at 2:00 AM EST (7:00 AM UTC)
- ✅ Tests both backend (Python/Pytest) and frontend (Node.js/Vitest)
- ✅ Runs security scans (Bandit, pip-audit)
- ✅ Creates a PR with failure details if tests fail
- ✅ No AI required - just documentation of failures
- ✅ Ready to use immediately

## Files Created

```
.github/
├── workflows/
│   └── nightly-tests.yml          # Nightly test workflow
└── scripts/
    └── handle_test_failures.py     # PR creation script
```

## Quick Setup

**No setup needed!** Just push these files and the workflow will:
- Run automatically every night at 2 AM EST
- Test backend, frontend, and security scans
- Create PRs when tests fail
- Work immediately

## How It Works

### Flow
```
Nightly Schedule (2 AM EST) → Run Backend Tests → Run Frontend Tests → Run Security Scans →
If Failures → Generate Summary → Create/Update PR with Logs
```

### What Gets Tested

1. **Backend Tests:**
   - Full pytest suite from `tests/` directory
   - Uses Poetry for dependency management
   - Captures all test output

2. **Frontend Tests:**
   - Vitest test suite from `frontend/` directory
   - Uses npm for dependency management
   - Captures all test output

3. **Security Scans:**
   - Bandit (Python code security scanning)
   - pip-audit (dependency vulnerability scanning)
   - Uses existing `scripts/run-pip-audit.py` wrapper

### Failure Handling

When tests fail:
1. Test output is captured and combined
2. Failure summary is generated in JSON format
3. Script checks for existing PR with same failures
4. Updates existing PR or creates new one
5. PR includes:
   - Failure summary (backend/frontend/security breakdown)
   - Full test logs
   - Failure signature for duplicate detection
   - Timestamp and commit information

## Customization

### Change Schedule

Edit the `cron` in `.github/workflows/nightly-tests.yml`:
```yaml
schedule:
  - cron: "0 7 * * *"  # Change this (7 AM UTC = 2 AM EST)
```

**Time Zone Notes:**
- EST (Eastern Standard Time) is UTC-5
- EDT (Eastern Daylight Time) is UTC-4
- Current setting: 7 AM UTC covers both (2 AM EST / 3 AM EDT)

### Change Test Commands

Edit the test steps in the workflow:
```yaml
- name: Run backend tests
  run: |
    poetry run pytest -q --tb=short -v tests > backend_test_output.log 2>&1
```

### Adjust Timeout

The workflow has a 60-minute timeout. Adjust if needed:
```yaml
timeout-minutes: 60  # Change this
```

## Testing

To test the workflows:

1. **Manual Trigger:**
   - Go to Actions tab in GitHub
   - Select "Nightly Tests"
   - Click "Run workflow" button

2. **Force a Failure:**
   - Temporarily break a test
   - Trigger workflow manually
   - Verify PR is created

3. **Check Logs:**
   - View workflow run logs
   - Check for any errors
   - Verify PR was created
   - Download artifacts (test logs)

## Important Notes

⚠️ **Dependencies:**
- The workflow uses Poetry for Python dependencies
- PyGithub is installed automatically during workflow execution
- No additional setup required

🔒 **Security:**
- Uses `GITHUB_TOKEN` (automatically provided by GitHub Actions)
- No additional secrets needed
- PRs are created with read-only access by default

📊 **Artifacts:**
- Test logs are uploaded as artifacts
- Available for 90 days
- Can be downloaded from workflow run page

## Troubleshooting

**PRs not created?**
- Check repository permissions (needs `contents: write` and `pull-requests: write`)
- Verify `GITHUB_TOKEN` is available (should be automatic)
- Check workflow logs for errors
- Ensure branch protection rules allow PR creation

**Tests timing out?**
- Increase `timeout-minutes` in workflow
- Check for hanging tests
- Review test execution logs

**Security scans failing?**
- Check if `scripts/run-pip-audit.py` exists
- Verify Poetry dependencies include security tools
- Review security scan output logs

**Need help?**
- See workflow logs in GitHub Actions
- Review `.github/scripts/handle_test_failures.py` for implementation details
- Check existing PRs created by the workflow

## Next Steps

1. **Push to repository:**
   ```bash
   git add .github/
   git commit -m "Add nightly test workflow"
   git push
   ```

2. **Verify it works:**
   - Check Actions tab
   - Manually trigger a test run
   - Wait for next scheduled run (2 AM EST)

3. **Monitor:**
   - Check for PRs created on failures
   - Review failure reports
   - Adjust schedule as needed

4. **Optional Enhancements:**
   - Add email notifications on failures
   - Integrate with Slack/Teams
   - Add coverage reporting
   - Include E2E tests in nightly run

---

**Ready to go!** The workflow is configured and ready to use. Just push the files and it will start running on schedule.

