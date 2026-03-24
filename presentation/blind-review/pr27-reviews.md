# Blind Review: PR #27 - Fixed 401 Auth Bug on Expired JWT Token

**Context**: Bug fix PR adding JWT expiration handling with improved auth error detection and session validation. Adds comprehensive logging across endpoints.

**Key Code Snippets**:

```python
# backend/middleware/auth.py
async def get_current_user(request: Request, credentials: ...):
    route = request.url.path
    method = request.method

    if credentials is None:
        logger.warning("[auth] Missing bearer token for %s %s", method, route)
        raise HTTPException(status_code=401, detail="Authentication required")

    # ... token validation ...

    logger.info(
        "[auth] Authenticated %s for %s %s (session_id=%s client=%s)",
        username, method, route, session_id, client,
    )
```

```typescript
// frontend/src/context/AuthContext.tsx
useEffect(() => {
  apiGet<{...}>("/auth/me", storedToken)
    .then((res) => { /* validate session */ })
    .catch((error) => {
      if (isAuthError(error)) {
        logout("Your session is no longer valid.");
      }
    })
    .finally(() => {
      setIsReady(true);
    });
}, []);
```

---

## Reviewer A

### Issues Found

**1. Startup Can Render Forever-Null (Bug/Reliability)**

`AppRoutes`/`ProtectedRoute` return `null` until `isReady` becomes true, but `isReady` is only set in the `.finally()` of the persisted-session `/auth/me` validation. If that request hangs (no timeout/abort), the app can stay blank indefinitely.

**Fix Focus Areas:**
- Add an `AbortController` + timeout for the `/auth/me` validation request
- Ensure `setIsReady(true)` is reached even on timeout
- Alternatively, show a non-blocking "validating session" state while validation runs

**2. Sensitive Identifiers Logged (Bug/Security)**

Auth-related logs now include `username`, `session_id`, and client IP at INFO/WARNING levels. This increases exposure of stable user identifiers in logs and may violate privacy expectations/policies.

**Fix:**
- Downgrade per-request auth success logs to DEBUG or remove them
- Avoid logging full `session_id`; log a short prefix or one-way hash
- Sanitize user-derived values before logging

**3. 401 Missing Bearer Challenge (Bug/Correctness)**

`get_current_user` raises 401 errors manually (with `HTTPBearer(auto_error=False)`) but does not include a `WWW-Authenticate: Bearer` header. This is a standards gap for clients expecting an auth challenge.

**Fix:**
- Add `headers={"WWW-Authenticate": "Bearer"}` to 401 exceptions

---

## Reviewer B

*No review submitted for this PR*

---

## Reviewer C

### Issues Found

**1. Missing Request Timeout (Reliability)**

The auth validation request in `AuthContext` has no timeout. If the backend is slow or unreachable, users see a blank screen forever. Add an AbortController with a reasonable timeout (e.g., 5 seconds).

**2. PII in Logs (Privacy)**

Logging usernames, session IDs, and IP addresses at INFO level is a privacy concern. Consider:
- Moving to DEBUG level
- Truncating/hashing identifiers
- Ensuring log retention policies align with privacy requirements

**3. RFC 6750 Compliance (Standards)**

401 responses should include `WWW-Authenticate: Bearer` header per RFC 6750. This helps clients understand the auth scheme expected.

```python
raise HTTPException(
    status_code=401,
    detail="Authentication required",
    headers={"WWW-Authenticate": "Bearer"}
)
```

---

## Voting Questions

1. Which review found the most important issue?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

2. Which review was most actionable?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

3. Which review had the best signal-to-noise ratio?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

4. Overall, which review would you prefer on your PRs?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

---

## Reveal (DO NOT READ UNTIL VOTING COMPLETE)

<details>
<summary>Click to reveal reviewer identities</summary>

- **Reviewer A**: Qodo
- **Reviewer B**: Greptile (did not review this PR)
- **Reviewer C**: Nitpick Senior (Simulated)

</details>
