"""Configuration loading from environment variables."""

import contextlib
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Action configuration loaded from environment variables."""

    github_token: str
    model: str
    agent_spec_path: str
    post_summary: bool
    post_inline_comments: bool
    max_comments: int
    min_severity: str

    # Context settings
    context_enabled: bool
    context_max_tokens: int

    # GitHub context
    repo_owner: str
    repo_name: str
    pr_number: int

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from GitHub Actions environment variables."""
        github_token = os.environ.get("INPUT_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            raise ValueError("GitHub token is required. Set INPUT_GITHUB_TOKEN or GITHUB_TOKEN.")

        model = os.environ.get("INPUT_MODEL", "")
        if not model:
            raise ValueError("Model is required. Set INPUT_MODEL.")

        # Parse repository info
        github_repository = os.environ.get("GITHUB_REPOSITORY", "")
        if "/" not in github_repository:
            raise ValueError("GITHUB_REPOSITORY must be in format 'owner/repo'")
        repo_owner, repo_name = github_repository.split("/", 1)

        # Parse PR number from event
        pr_number_str = os.environ.get("PR_NUMBER", "")
        if not pr_number_str:
            # Try to get from GITHUB_REF (refs/pull/123/merge)
            github_ref = os.environ.get("GITHUB_REF", "")
            if "/pull/" in github_ref:
                with contextlib.suppress(IndexError):
                    pr_number_str = github_ref.split("/pull/")[1].split("/")[0]

        if not pr_number_str:
            raise ValueError(
                "Could not determine PR number. "
                "Set PR_NUMBER env var or ensure GITHUB_REF contains '/pull/<number>/'"
            )

        try:
            pr_number = int(pr_number_str)
        except ValueError as e:
            raise ValueError(f"Invalid PR number format: '{pr_number_str}' is not a number") from e

        min_severity = os.environ.get("INPUT_MIN_SEVERITY", "warning").lower()
        if min_severity not in ("error", "warning", "info"):
            min_severity = "warning"

        # Context settings
        context_enabled = os.environ.get("INPUT_CONTEXT_ENABLED", "true").lower() == "true"
        try:
            context_max_tokens = int(os.environ.get("INPUT_CONTEXT_MAX_TOKENS", "5000"))
        except ValueError:
            context_max_tokens = 5000

        try:
            max_comments = int(os.environ.get("INPUT_MAX_COMMENTS", "10"))
        except ValueError:
            max_comments = 10

        return cls(
            github_token=github_token,
            model=model,
            agent_spec_path=os.environ.get("INPUT_AGENT_SPEC_PATH", ".github/ai-reviewer.md"),
            post_summary=os.environ.get("INPUT_POST_SUMMARY", "true").lower() == "true",
            post_inline_comments=os.environ.get("INPUT_POST_INLINE_COMMENTS", "true").lower()
            == "true",
            max_comments=max_comments,
            min_severity=min_severity,
            context_enabled=context_enabled,
            context_max_tokens=context_max_tokens,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
        )
