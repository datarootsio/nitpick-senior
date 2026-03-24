# AI Code Review Comparison Data

## Overview

- **Repository**: datarootsio/agentic-bi-demo
- **Tools Compared**: Qodo, Greptile, GitHub Copilot, Nitpick Senior (simulated)
- **PRs Analyzed**: #2-16 (period where both Qodo and Greptile were active)
- **Note**: Greptile's free trial ended after PR #16 (~March 11, 2026)

---

## PR #27: Fixed 401 Auth Bug on Expired JWT Token

### Summary
Bug fix PR adding comprehensive logging across auth, chat, admin, and quest endpoints. Improved frontend error handling with custom ApiError class and auth error detection.

### Qodo Review

**Found Issues (3):**
1. **Startup can render forever-null** (Bug/Reliability)
   - `AppRoutes`/`ProtectedRoute` return `null` until `isReady` becomes true
   - No timeout/abort for `/auth/me` validation request
   - App can stay blank indefinitely

2. **Sensitive identifiers logged** (Bug/Security)
   - Auth logs include username, session_id, and client IP at INFO/WARNING levels
   - May violate privacy expectations/policies

3. **401 missing Bearer challenge** (Bug/Correctness)
   - 401 responses missing `WWW-Authenticate: Bearer` header
   - Standards/interop gap for clients expecting auth challenge

**Format**: Comprehensive with code references, evidence, and agent prompts for remediation.

### Greptile Review
*No review present on this PR*

### Nitpick Senior Review (Simulated)

**Would Find:**
1. Missing timeout on auth validation could freeze UI
2. Logging PII (usernames, session IDs) at INFO level is a privacy concern
3. Consider adding WWW-Authenticate header for RFC compliance

**Format**: Concise inline comments with suggestions.

---

## PR #21: Feat/React UI Migration

### Summary
Complete migration from Streamlit to React frontend with FastAPI backend. ~2500 lines changed across 60 files. Major architectural change.

### Qodo Review

**Found Issues (5):**
1. **SPA path traversal** (Bug/Security) - CRITICAL
   - `serve_spa` concatenates user-controlled path without validation
   - Allows directory traversal reads outside frontend/dist
   - Can expose sensitive files (configs, env files)

2. **Admin login escalation** (Bug/Security) - CRITICAL
   - Any client can obtain admin token by using admin username
   - Admin status checked purely by username in ADMIN_USERNAMES set

3. **Default JWT secret** (Bug/Security) - CRITICAL
   - JWT_SECRET falls back to hard-coded default
   - Enables token forgery if deployments forget to set JWT_SECRET

4. **Executes LLM chart code** (Bug/Security)
   - Backend executes python_code via exec() with full builtins
   - Prompt injection could lead to server-side code execution

5. **State drops chat results** (Bug/Correctness)
   - Chat endpoint saves assistant messages with dataframes=[]
   - Breaks follow-up context reuse

**Format**: Very comprehensive with Mermaid diagrams, file change summaries, security analysis.

### Greptile Review
*No review present on this PR*

### Nitpick Senior Review (Simulated)

**Would Find:**
1. Path traversal vulnerability in SPA fallback route
2. Admin authorization based solely on username is insecure
3. Hardcoded JWT secret fallback is dangerous
4. exec() on LLM output is extremely risky

**Format**: Security-focused, actionable suggestions.

---

## PR #4: Add Logic to Maintain DataFrames in Chat History

### Summary
Small feature PR (8 lines changed) to persist dataframes in chat history and replay on page reload.

### Qodo Review

**Found Issues (2):**
1. **Unbounded dataframe rerender** (Bug/Performance)
   - Every Streamlit rerun re-displays all DataFrames
   - Can become slow and memory-heavy over time
   - Long sessions may cause OOM conditions

2. **message['dataframes'] not validated** (Rule Violation/Reliability)
   - UI renders dataframes without type/shape validation
   - Non-DataFrame objects could break UI

**Format**: Detailed with suggested implementation directions.

### Greptile Review

**Found Issues (1):**
1. **Inconsistent defensive programming**
   - Suggested using `.get("dataframes", [])` for consistency

**Format**: Very concise, single inline suggestion.

### Nitpick Senior Review (Simulated)

**Would Find:**
1. Consider limiting dataframe size in session state
2. Add type checking before calling st.dataframe()
3. Use consistent .get() pattern for dictionary access

---

## Comparison Matrix

| Aspect | Qodo | Greptile | Copilot | Nitpick Senior |
|--------|------|----------|---------|----------------|
| **PR #27** | | | | |
| Issues Found | 3 | 0 (no review) | 3 | ~3 |
| Security Issues | 1 | - | 1 | 1 |
| Actionability | High | - | Medium | Medium |
| **PR #21** | | | | |
| Issues Found | 5 | 0 (no review) | 0 | ~4 |
| Security Issues | 4 | - | - | 4 |
| Actionability | Very High | - | - | High |
| **PR #13** | | | | |
| Issues Found | 6 | 12+ | 18+ | ~6 |
| Security Issues | 3 | 4 | 5 | ~4 |
| Unique Findings | 1 (file read) | 2 (import bypass, dict bypass) | 1 (isinstance) | - |
| Actionability | Very High | Very High | High | High |
| **PR #4** | | | | |
| Issues Found | 2 | 1 | 0 | ~3 |
| Security Issues | 0 | 0 | - | 0 |
| Actionability | High | Low | - | Medium |

**Full Coverage Summary (27 PRs):**
| Tool | PRs Reviewed | Coverage | Notes |
|------|-------------|----------|-------|
| Qodo | 26/27 | 96% | Consistent throughout |
| Greptile | 15/16 | **94%** (during trial) | Trial ended PR #17+ |
| Copilot | 19/27 | 70% | Free with GitHub |

**Important Note:** Greptile's free trial ended on ~March 11, 2026 (after PR #16).
- During active trial (PRs #2-16): **100% coverage**
- After trial ended (PRs #17-27): 0% (shows "free trial ended" message)

**Greptile PRs with full reviews:** #2, #3, #4, #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16

### Additional Greptile Findings (from full repo analysis)

**PR #14 (Adjustments selfmade option):**
- Anti-cheat bypass: only checks `summary`, not `question` field
- IndentationError would crash app on startup
- `python_code` rendered as text AND executed
- Migration issue silently discards user history

**PR #8 (big update):**
- Path traversal in `save_chat_state()`, `load_chat_state()`, dataframe paths
- Hardcoded admin usernames (suggested env var)
- Session state tampering bypasses `_safe_df_path()`

**PR #5 (treasure hunt questions):**
- Query only searches `fact_sales` but question asks for "all operational sales channels"
- Missing `fact_online_sales` UNION

---

## PR #13: Replace Genie with Multi-Agent BI Pipeline (NEW DATA)

### Summary
Major architectural PR replacing Databricks Genie with a self-hosted multi-agent pipeline. ~2768 additions, 20 files changed. Includes LLM code execution, Terraform changes, and CI updates.

### Qodo Review

**Found Issues (6):**
1. **LLM code execution** (Security) - CRITICAL
   - UI executes LLM-supplied `python_code` via `exec()` with full `__builtins__`
   - Regex-based validation is not sufficient to sandbox Python

2. **PR image push + secrets** (Security)
   - Deploy workflow triggers on `pull_request` and logs into ACR using secrets
   - Exposes registry credentials to untrusted PR code

3. **Terraform env missing** (Reliability)
   - Missing `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`
   - App will fail `validate_env()` and stop at startup

4. **SQL state handling** (Reliability)
   - `execute_sql()` raises for any state other than `SUCCEEDED`
   - Long-running queries return RUNNING state and fail

5. **Arbitrary file read path** (Security)
   - String dataframe entries loaded with `pd.read_csv()` if path exists
   - Tampered saved state can trigger local file reads

6. **Agent context not persisted** (Reliability)
   - `agent_history` reconstructed without hidden context fields
   - Degrades routing across sessions

### Greptile Review

**Found Issues (12+):**
1. **`from X import Y` bypasses blocklist** (Security) - CRITICAL
   - Every forbidden pattern only matches `import X` form
   - `from os import system` is not blocked

2. **Full builtins exposed enables bypass** (Security) - CRITICAL
   - `__builtins__['__import__']('os').system('whoami')` bypasses all regex checks
   - Suggested safe builtins whitelist

3. **Real infrastructure IDs committed** (Security)
   - Azure subscription ID, Databricks workspace URL, AI Foundry endpoint in tfvars

4. **Missing Terraform env vars** (Reliability)
   - Same as Qodo finding

5. **RUNNING/PENDING state after timeout** (Reliability)
   - Misleading error message, needs polling

6. **PR trigger exposes secrets** (Security)
   - Fork PRs can exfiltrate ACR credentials

7. **pre-commit and pytest in production deps** (Quality)
   - Increases image size and attack surface

8. **Debug print() statements left** (Quality)
   - Will leak tool inputs/internal state to stdout

9. **import importlib not blocked** (Security)
   - Can dynamically load any blocked module

10. **assert stripped by -O flag** (Reliability)
    - Runtime guards disappear in optimized mode

11. **anthropic minimum version too low** (Reliability)
    - `AnthropicFoundry` not available in `>=0.42.0`

12. **Sequence diagram + confidence score** (Format)
    - Provided Mermaid diagram and 1/5 confidence rating

### GitHub Copilot Review

**Found Issues (18+):**
1. exec() with __builtins__ exposed
2. Missing Terraform env vars
3. RUNNING state polling needed
4. isinstance() doesn't accept PEP604 union
5. agent_history loses context on reload
6. Debug print() statements
7. PR trigger will push images
8. Dev tfvars contains real infrastructure
9. Regex blacklist not robust
10. LLM_PROVIDER validation missing
11. CSV re-read overhead
... and more

### Analysis

This PR shows **Greptile performing at its best**:
- Deep security analysis with exploit examples
- Found bypass patterns Qodo missed (`from X import Y`, `__builtins__` dict access)
- Provided working code fixes
- Comprehensive summary with confidence score

**Why the difference from other PRs?**
- Larger, more security-critical changes
- Greptile may have selective review triggers
- Complex PRs get more attention

---

## Key Observations

### Qodo Strengths
- Found critical security vulnerabilities (path traversal, admin escalation, JWT default)
- Comprehensive structured format with diagrams
- Provides "agent prompts" for AI-assisted remediation
- High signal, low noise

### Qodo Weaknesses
- Can be verbose (full walkthrough for every PR)
- Requires paid subscription

### Greptile Strengths
- **Strong security analysis** across multiple PRs
- Found path traversal vulnerabilities (PR #8, #13, #14)
- Found bypass patterns others missed (`from X import`, `__builtins__` dict access)
- Catches logic errors (PR #5: query missing online sales table)
- Catches crash bugs (PR #14: IndentationError would crash on startup)
- Provides working code fixes with suggestions
- Writes comprehensive PR summaries with sequence diagrams
- Confidence scoring (1-5 scale)
- 52% coverage (14/27 PRs)

### Greptile Weaknesses
- **Inconsistent coverage** - doesn't review every PR
- Heavier on large/security-critical PRs, lighter on small changes
- ~$20/user/month cost

### Nitpick Senior (DIY) Potential
- Can be tuned for security focus
- Cost: ~$0.01-0.10 per review
- Full control over prompts
- Would need codebase context for architecture-level issues

---

## Actual Pricing (March 2026)

### Qodo
- **Free**: 30 PRs/month, 75 IDE/CLI credits
- **Teams**: $30/user/month (discounted from $38)
  - Unlimited PRs (promo) or 20 PRs/user normally
  - 2,500 IDE/CLI credits
- **Enterprise**: Custom pricing

### Greptile
- **Cloud**: $30/seat/month
  - 50 reviews included
  - $1 per additional review
  - Unlimited repos and users
- **Enterprise**: Custom (self-hosted option)
- **Open Source**: 100% discount (free)
- **Startups**: 50% off
- 20% off for annual contracts

### Nitpick Senior (DIY)
- **API costs only**: ~$0.01-0.10 per review
- Can use free models via OpenRouter
- Self-hosted, open source
