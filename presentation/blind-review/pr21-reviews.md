# Blind Review: PR #21 - React UI Migration

**Context**: Major migration from Streamlit to React/FastAPI. ~2500 lines across 60 files. New authentication system, API endpoints, and frontend.

**Key Code Snippets**:

```python
# backend/main.py - SPA serving
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    file_path = _STATIC_DIR / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))
    return FileResponse(str(_STATIC_DIR / "index.html"))
```

```python
# backend/config.py
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
ADMIN_USERNAMES = {"ramiro", "ryoko", "ali"}
```

```python
# backend/routers/auth.py
@router.post("/login")
async def login(req: LoginRequest):
    token = create_token(req.session_id, req.username.strip())
    return LoginResponse(
        token=token,
        user={"isAdmin": req.username.strip().lower() in ADMIN_USERNAMES}
    )
```

---

## Reviewer A

### Critical Security Issues Found

**1. SPA Path Traversal (Security)**

`serve_spa` concatenates user-controlled `full_path` onto `_STATIC_DIR` and serves it when `is_file()` returns true, allowing directory traversal reads outside `frontend/dist` in production builds. This can expose sensitive files from the container filesystem.

**Fix**: Resolve the candidate path and validate `resolved.relative_to(_STATIC_DIR.resolve())` before serving.

**2. Admin Login Escalation (Security)**

POST `/api/auth/login` issues a JWT for any username/session_id and sets admin status purely by username membership in `ADMIN_USERNAMES`. Any client can obtain admin access by logging in as "ramiro".

**3. Default JWT Secret (Security)**

`JWT_SECRET` falls back to a hard-coded default when the environment variable is missing, enabling token forgery if deployments forget to set `JWT_SECRET`.

**4. Executes LLM Chart Code (Security)**

Backend executes `python_code` via `exec()` with full builtins when `action=="chart"`. Not safe even with regex filters - can lead to server-side code execution under prompt injection.

**5. State Drops Chat Results (Correctness)**

Chat endpoint saves assistant messages with `dataframes=[]` and never records tables from the streamed response, breaking the `previous_dfs` feature.

---

## Reviewer B

*No review submitted for this PR*

---

## Reviewer C

### Security Review

**1. Path Traversal in SPA Fallback (CRITICAL)**

The `serve_spa` endpoint doesn't validate that the resolved path stays within the static directory. An attacker could request `../../etc/passwd` to read arbitrary files.

**Fix**: Use `Path.resolve()` and check `is_relative_to()` before serving.

**2. Admin Authorization is Broken (CRITICAL)**

Anyone can become admin by simply choosing an admin username during login. There's no password, no email verification - just pick "ramiro" and you're in.

**Fix**: Implement proper authentication with password verification or OAuth.

**3. Hardcoded JWT Secret (HIGH)**

The fallback secret `"dev-secret-change-in-production"` will be used in production if JWT_SECRET isn't set. This allows anyone to forge valid tokens.

**Fix**: Fail fast if JWT_SECRET is not set in production.

**4. Code Execution via exec() (HIGH)**

Executing LLM-generated Python code with `exec()` is inherently dangerous. Prompt injection could lead to RCE.

**Fix**: Use a sandboxed environment or switch to a declarative chart specification.

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
