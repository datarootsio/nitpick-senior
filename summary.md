# AI PR Reviewer - Session Summary

## Overview

Migrated the AI PR Reviewer from LiteLLM to Pydantic AI and improved the review quality and comment management.

---

## 1. Migration: LiteLLM to Pydantic AI

**Files changed:** `pyproject.toml`, `src/llm/client.py`, `src/review/analyzer.py`, `src/main.py`

### Before
- Used `litellm.completion()` with manual JSON parsing
- Regex-based extraction of JSON from LLM responses
- Separate validation step after parsing

### After
- Uses Pydantic AI `Agent` with `output_type=ReviewResponse`
- Native structured output (no JSON parsing needed)
- Built-in retry logic on validation failures
- Async pipeline (`async def analyze_pr`, `async def main`)

### Dependency Change
```diff
- "litellm>=1.40.0"
+ "pydantic-ai-slim[openai,anthropic]>=0.0.14"
```

Result: **159 → 57 packages** (removed 102 unnecessary dependencies)

---

## 2. Multi-Provider Support

Added support for multiple LLM providers via `OpenAIProvider`:

| Prefix | Provider | Env Var |
|--------|----------|---------|
| `anthropic/` | Anthropic | `ANTHROPIC_API_KEY` |
| `azure/` | Azure OpenAI | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` |
| `openrouter/` | OpenRouter | `OPENROUTER_API_KEY` |
| (none) | OpenAI | `OPENAI_API_KEY` |

**Example usage:**
```yaml
model: openrouter/stepfun/step-3.5-flash:free
```

---

## 3. Improved Review Prompts

**Problem:** Reviewer missed critical bugs (division by zero) and flagged linter-detectable issues.

**Solution:** Updated `src/prompts/defaults.py` and `src/llm/client.py`:

### System Prompt Changes
- Prioritized runtime errors (division by zero, index OOB) as #1
- Added "Input validation bugs" category
- Explicit "What NOT to Comment On" section (linter issues, unused variables)

### User Prompt Changes
- Added: "ALWAYS check: can user/environment input cause division by zero, index errors, or crashes?"
- Changed "Theoretical edge cases" → "Hypothetical issues unrelated to actual input paths"
- Explicit: "Unused variables or imports (linters catch these)"

**Result:** Review quality improved from 6/10 to 9/10 on test cases.

---

## 4. Comment Management: Delete vs Minimize

**Problem:** Minimized comments still cluttered PR history.

**Solution:** Changed from `minimize_comment()` to `delete_review_comment()`.

**Files changed:** `src/github/client.py`, `src/github/comments.py`

### New Behavior
- Old comments at locations not in new review → deleted
- Outdated comments (line=None, code changed) → deleted
- Comments at same location with different content → edited in place

---

## 5. Bug Fixes

| Issue | Fix |
|-------|-----|
| `result_type` not found | Changed to `output_type` (Pydantic AI API) |
| `result.data` not found | Changed to `result.output` |
| `base_url` not accepted | Use `OpenAIProvider(base_url=...)` instead |
| `get_pull_comment` not found | Pass comment object directly, call `.delete()` |
| Outdated comments not cleaned | Track comments with `line=None` separately |

---

## 6. Current Workflow Configuration

`.github/workflows/test-action.yml`:
```yaml
- name: Nitpick Senior
  uses: ./
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    model: openrouter/stepfun/step-3.5-flash:free
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

---

## 7. Test Results

Planted a **path traversal vulnerability** in `src/config.py`:
```python
cache_name = os.environ.get("INPUT_CACHE_NAME", "state")
cache_path = os.path.join(cache_dir, cache_name + ".json")
```

| Model | Found Path Traversal | Found Empty Dir Crash | Quality |
|-------|---------------------|----------------------|---------|
| Claude Sonnet 4.5 | Yes | Yes | 9/10 |
| stepfun/step-3.5-flash:free | Yes (on retry) | Yes | 7/10 |

---

## 8. Enhanced Review Output (Qodo/Greptile-style)

**PR:** [#10](https://github.com/datarootsio/github-reviewer/pull/10)

Added features to match paid tools like Qodo and Greptile:

### Confidence Score (1-5)
Reviews now include a confidence rating in the summary:
- 5: Safe to merge, no issues found
- 4: Minor issues only, safe to merge
- 3: Some concerns, review recommended
- 2: Significant issues, changes needed
- 1: Critical issues, do not merge

### File Overview Table
Summary includes a table of important files changed:
| File | Type | Overview |
|------|------|----------|
| `path/to/file.py` | Bug fix | Fixed null pointer in handler |

### Issue Categories
Comments are now categorized:
- Security (SQL injection, XSS, path traversal)
- Bug (runtime errors, logic errors)
- Reliability (missing error handling, unclosed resources)
- Performance (N+1 queries, memory leaks)
- Correctness (spec deviations, breaking changes)

### Inline Comment Format
Comments now show category badges:
```
:lock: **Security** | :x: **ERROR**

Path traversal vulnerability in cache_name parameter...
```

**Files changed:**
- `src/llm/response.py`: Added `FileOverview`, `confidence`, `important_files`, `category`
- `src/github/comments.py`: Enhanced formatting with confidence labels and category badges
- `src/prompts/defaults.py`: Added category and confidence instructions
- `src/llm/enhanced_response.py`: Future Mermaid diagram support
- `src/prompts/enhanced.py`: Enhanced prompt schema

---

## Files Modified

| File | Change |
|------|--------|
| `pyproject.toml` | litellm → pydantic-ai-slim |
| `src/llm/client.py` | Complete rewrite with Pydantic AI Agent |
| `src/llm/response.py` | Added FileOverview, confidence, category fields |
| `src/review/analyzer.py` | Made async |
| `src/main.py` | Made async, added asyncio.run() |
| `src/prompts/defaults.py` | Added categories, confidence, priority guidelines |
| `src/github/client.py` | Added delete_review_comment() |
| `src/github/comments.py` | Enhanced summary and comment formatting |
| `.github/workflows/test-action.yml` | OpenRouter + free model |
| `src/llm/enhanced_response.py` | New: Qodo/Greptile-style response models |
| `src/prompts/enhanced.py` | New: Enhanced prompt with diagram support |

---

## 9. Repository Context Collection

**PR:** [#12](https://github.com/datarootsio/github-reviewer/pull/12)

Added repository context to enhance code reviews, similar to paid tools like Qodo and Greptile.

### New Module: `src/context/`

| File | Purpose |
|------|---------|
| `models.py` | `RepoContext`, `RelatedFile` Pydantic models |
| `collector.py` | Orchestrates context collection with token budgeting |
| `extractors/imports.py` | Extract imports from Python, JS/TS, Go |
| `extractors/files.py` | Fetch README and file contents |

### Features
- Fetches README.md automatically
- Extracts imports from changed files and includes imported files
- Token budget management (default 5000 tokens for context)
- Sensitive file filtering (.env, .key, credentials, etc.)
- Multi-extension resolution for JS/TS imports

### Configuration
```yaml
context_enabled: 'true'      # default
context_max_tokens: '5000'   # default
```

### Files Changed
| File | Change |
|------|--------|
| `src/github/client.py` | Added `get_file_content()`, `get_changed_files()` |
| `src/config.py` | Added `context_enabled`, `context_max_tokens` |
| `src/review/analyzer.py` | Integrated context collection |
| `src/llm/client.py` | Updated prompt to include context sections |
| `action.yml` | Added context input parameters |

---

## 10. Reviewer Behavior: Identify Problems, Not Solutions

**Key Insight:** The reviewer was providing code suggestions, which led to surface-level fixes without understanding root causes. This created a "whack-a-mole" debugging pattern.

### The Problem
When the reviewer said:
> "This will fail for forks. Use `pr.get_files()` instead of `repo.compare()`"

The developer would apply the fix mechanically without asking: "Where else does this pattern exist?"

Result: The same root cause (using `self.repo` to access fork content) appeared 3 times across different review cycles.

### The Solution
Changed the reviewer to identify WHAT is wrong and WHY, without suggesting HOW to fix it.

**Before (bad):**
```
"This will fail for forks. Use pr.get_files() instead of repo.compare()"
```

**After (good):**
```
"This will fail for forked PRs. The underlying issue is that self.repo
always points to the base repository, so any method using it cannot
access content from a fork's branch."
```

### Changes Made
| File | Change |
|------|--------|
| `src/llm/response.py` | Replaced `suggestion` field with `why` field |
| `src/prompts/defaults.py` | Added "diagnostic not prescriptive" framing |
| `src/llm/client.py` | Removed "include a suggestion" instruction |
| `src/github/comments.py` | Shows "Why this matters" instead of code blocks |

### Result
Reviewer no longer outputs code suggestions, but still sometimes provides textual solutions. Further prompt refinement needed.

---

## 11. Multi-Git-Provider Support

**PR:** [#15](https://github.com/datarootsio/github-reviewer/pull/15)

Added support for multiple Git platforms beyond GitHub.

### Supported Providers

| Provider | Environment Detection | Config Variables |
|----------|----------------------|------------------|
| GitHub | Default | `GITHUB_REPOSITORY`, `GITHUB_TOKEN` |
| GitLab | `CI_SERVER_URL` or `GITLAB_URL` | `GITLAB_PROJECT`, `GITLAB_TOKEN` |
| Azure DevOps | `SYSTEM_TEAMPROJECT` or `AZURE_DEVOPS_ORG` | `AZURE_DEVOPS_*` or `SYSTEM_*` |
| Bitbucket | `BITBUCKET_WORKSPACE` | `BITBUCKET_*` |

### Architecture

```
src/providers/
├── protocol.py      # GitProvider protocol definition
├── factory.py       # Provider detection and creation
├── github.py        # GitHub implementation
├── gitlab.py        # GitLab implementation
├── azure_devops.py  # Azure DevOps implementation
└── bitbucket.py     # Bitbucket implementation
```

### Files Changed
| File | Change |
|------|--------|
| `src/providers/protocol.py` | New: GitProvider protocol, data models |
| `src/providers/factory.py` | New: detect_provider(), create_provider() |
| `src/providers/*.py` | New: Provider implementations |
| `src/config.py` | Added provider detection, multi-provider config |
| `src/main.py` | Uses provider factory |
| `action.yml` | Added provider input parameter |

---

## 12. Multi-Provider Code Cleanup

**PR:** [#16](https://github.com/datarootsio/github-reviewer/pull/16)

Refactored the multi-provider implementation for better maintainability.

### Changes

#### Priority 1: Eliminated Code Duplication
- Created `src/utils/env.py` with shared `resolve_token()` and `parse_int_env()`
- Removed duplicate 8-line token resolution from `config.py` and `factory.py`
- Cached Bitbucket repository object in `__init__` (eliminated 7 repeated API calls)

#### Priority 2: BaseProvider Class
Created `src/providers/base.py` with common functionality:
- `_pr_cache` initialization
- `_get_cached_pr()` / `_cache_pr()` methods
- `_safe_api_call()` for standardized error handling

All 4 providers now inherit from `BaseProvider`.

#### Priority 3: Moved Comments Module
- Moved `src/github/comments.py` to `src/review/comments.py` (provider-agnostic)
- Extracted formatting to `src/review/formatters.py`
- Updated imports in `src/main.py`
- Added backward-compatible re-exports in `src/github/__init__.py`

#### Priority 4: Variable Naming
- `commit_sha` → `head_commit_sha`
- `outdated_comments` → `stale_comments`
- `total_posted` → `total_synced`

#### Priority 5: Provider Config Objects
Created `src/providers/config.py` with frozen dataclasses:
- `GitHubConfig`, `AzureDevOpsConfig`, `GitLabConfig`, `BitbucketConfig`
- Added `create_provider_from_config()` as cleaner factory alternative

### Files Changed
| File | Change |
|------|--------|
| `src/utils/env.py` | New: shared env utilities |
| `src/providers/base.py` | New: BaseProvider class |
| `src/providers/config.py` | New: provider config dataclasses |
| `src/review/comments.py` | Moved from github/ |
| `src/review/formatters.py` | New: extracted formatting |
| `src/providers/*.py` | Inherit from BaseProvider |
| `src/config.py` | Use shared utilities |

### Verification
- All 107 tests pass (no test modifications)
- `ruff check` passes
- Import verification successful
