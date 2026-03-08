# JWT Secret Key Rotation Runbook

## Overview

DocReview360 uses HS256 JWT tokens signed with `DOCREVIEW360_SECRET_KEY`. If this
key is compromised, all active tokens must be invalidated immediately by rotating
the key. The server supports a *previous-key* fallback (`DOCREVIEW360_SECRET_KEY_PREVIOUS`)
so that tokens signed with the old key remain valid during the rotation window — avoiding
a hard logout of all users.

---

## Pre-rotation Checklist

- [ ] Generate a new secret key: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Record the *current* key value (you will need it for `DOCREVIEW360_SECRET_KEY_PREVIOUS`)
- [ ] Confirm that `DOCREVIEW360_ACCESS_EXPIRE_MINUTES` is set to the desired TTL (default: 30)
- [ ] Plan the rotation window: `SECRET_KEY_PREVIOUS` must remain set until all old tokens expire

---

## Rotation Steps

### Step 1 — Deploy the new key with the old key as fallback

Set both environment variables before restarting:

```
DOCREVIEW360_SECRET_KEY=<new-key>
DOCREVIEW360_SECRET_KEY_PREVIOUS=<old-key>
```

Restart the API server. All new tokens will be signed with the new key. Existing
tokens signed with the old key will still be accepted because `get_current_user()`
tries `SECRET_KEY` first and falls back to `SECRET_KEY_PREVIOUS` on failure.

### Step 2 — Wait for the rotation window to expire

The rotation window is `DOCREVIEW360_ACCESS_EXPIRE_MINUTES` (default: 30 minutes).
After this period, all tokens signed with the old key will have expired.

For safety, wait **2× the token TTL** before proceeding.

### Step 3 — Remove the previous key

```
DOCREVIEW360_SECRET_KEY=<new-key>
# Remove DOCREVIEW360_SECRET_KEY_PREVIOUS entirely
```

Restart the API server. Old-key tokens are now fully rejected.

### Step 4 — Verify

```bash
# All new logins should succeed
curl -X POST http://localhost:8000/token -d "username=alice&password=password"

# Tokens issued before Step 1 should now be rejected (401)
```

---

## Emergency Rotation (Immediate Invalidation)

If the old key is confirmed compromised and **all active sessions must be invalidated immediately**:

1. Set only the new key — do NOT set `SECRET_KEY_PREVIOUS`:
   ```
   DOCREVIEW360_SECRET_KEY=<new-key>
   # Do not set DOCREVIEW360_SECRET_KEY_PREVIOUS
   ```
2. Restart all API workers simultaneously.
3. All existing tokens are immediately invalid. Users must log in again.

---

## Notes

- The in-memory token blacklist (`revoke_token`) is cleared on server restart.
  Use emergency rotation (above) rather than relying on the blacklist for
  long-lived compromised keys.
- Audit log entries for the rotation event should be created manually using
  `log_event("key_rotation", user_id="ops", reason="scheduled|emergency")`.
- For OIDC tokens, use the analogous `DOCREVIEW360_OIDC_SECRET_KEY` and
  `DOCREVIEW360_OIDC_SECRET_KEY_PREVIOUS` variables (not yet implemented; track
  in the backlog).
