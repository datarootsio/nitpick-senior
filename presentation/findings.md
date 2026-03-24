# Key Findings for Presentation

## 1. AI Code Review Feedback Loops

### The Whack-a-Mole Problem
When AI reviewers provide code suggestions, developers tend to:
- Apply fixes mechanically without understanding root cause
- Fix only the specific line mentioned, not the underlying pattern
- Create a feedback loop: fix → new review → new issue at same root cause

**Example from our PR:**
1. Reviewer: "Use `pr.get_files()` instead of `repo.compare()`" → Fixed
2. Reviewer: "Use `pr.get_files()` for `get_file_content()` too" → Fixed
3. Reviewer: "Fork detection still broken in collector" → Same root cause!

**Root cause:** `self.repo` always points to base repository, affecting ALL fork-related operations.

### The Solution
Reviewers should identify WHAT and WHY, not HOW:
- Forces developer to understand the problem
- Leads to comprehensive fixes, not patches
- Breaks the feedback loop

---

## 2. Suggestion-Driven vs Problem-Driven Reviews

| Aspect | Suggestion-Driven | Problem-Driven |
|--------|-------------------|----------------|
| Output | "Use X instead of Y" | "This breaks because Z" |
| Developer action | Copy-paste fix | Understand and design fix |
| Fix completeness | Surface-level | Architectural |
| Learning | Minimal | High |
| Review cycles | Many (whack-a-mole) | Fewer (complete fixes) |

---

## 3. Context Enrichment Value

Adding repository context (README, imported files) to reviews:
- Gives LLM understanding of project conventions
- Helps identify cross-file implications
- Matches capabilities of paid tools (Qodo, Greptile)

**Trade-off:** Token budget management is critical
- Context competes with diff for token space
- Need to prioritize most relevant files
- Sensitive file filtering is a security requirement

---

## 4. False Positives in AI Reviews

The reviewer flagged `truncate_diff(diff_content, max_tokens)` as an error 3 times, claiming the function doesn't accept 2 arguments.

**Reality:** The function signature is `def truncate_diff(diff_content: str, max_tokens: int = MAX_DIFF_TOKENS)`

**Lesson:** AI reviewers can be confidently wrong. The LLM doesn't actually verify claims against the codebase - it makes assumptions based on common patterns.

---

## 5. Prompt Engineering Insights

### What Worked
- Explicit "What NOT to Comment On" sections
- Category-based organization (Security, Bug, Reliability)
- Confidence scores for review quality signaling

### What Didn't Work (Initially)
- Simply saying "don't suggest fixes" - LLM still provided textual solutions
- Need stronger framing ("You are a diagnostic tool, not a surgeon")
- May need output schema changes to enforce behavior

---

## 6. Token Economics

| Component | Budget |
|-----------|--------|
| Total | 30,000 tokens |
| Context (README + imports) | 5,000 tokens (configurable) |
| Diff | 25,000 tokens (reduced when context used) |
| README max | 2,000 tokens |
| Per-file max | 1,000 tokens |

**Edge case found:** If context exceeds budget, diff gets 0 tokens → useless review. Fixed with `max(0, ...)` but should have minimum useful diff size.

---

## 7. Fork Support Complexity

GitHub API limitation: `repo.get_contents()` only works for the repository the client is authenticated against. For forked PRs:
- `pr.base` → base repo (where PR targets)
- `pr.head` → fork repo (where changes are)

To fetch fork content, need to either:
- Create separate client for fork repo
- Use raw git operations
- Accept degraded functionality for fork PRs

---

## Questions for Discussion

1. Should AI reviewers ever provide code suggestions?
2. How do we balance "helpful" vs "educational" feedback?
3. What's the right level of context for effective reviews?
4. How do we handle confident false positives?
