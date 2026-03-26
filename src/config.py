"""Configuration loading from environment variables."""

import contextlib
import os
from dataclasses import dataclass

from src.providers import ProviderType, detect_provider
from src.utils.env import parse_int_env, resolve_token


@dataclass
class Config:
    """Action configuration loaded from environment variables."""

    # Authentication
    token: str

    # Provider settings
    provider: ProviderType

    # Model settings
    model: str
    agent_spec_path: str

    # Review settings
    post_summary: bool
    post_inline_comments: bool
    max_comments: int
    min_severity: str
    resolve_outdated: bool

    # Context settings
    context_enabled: bool
    context_max_tokens: int

    # GitHub context (backward compatible)
    repo_owner: str
    repo_name: str
    pr_number: int

    # Azure DevOps settings
    azure_org_url: str | None
    azure_project: str | None
    azure_repository: str | None

    # GitLab settings
    gitlab_url: str | None
    gitlab_project: str | None

    # Bitbucket settings
    bitbucket_workspace: str | None
    bitbucket_repo_slug: str | None
    bitbucket_username: str | None

    # Static analysis settings
    static_analysis_file: str | None

    # Backward compatible alias
    @property
    def github_token(self) -> str:
        """Backward compatible alias for token."""
        return self.token

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Detect provider
        provider_str = os.environ.get("INPUT_PROVIDER", "")
        provider = ProviderType(provider_str.lower()) if provider_str else detect_provider()

        # Get token (support multiple env var names for backward compat)
        token = resolve_token()
        if not token:
            raise ValueError(
                "Authentication token is required. "
                "Set INPUT_TOKEN, INPUT_GITHUB_TOKEN, or provider-specific token env var."
            )

        model = os.environ.get("INPUT_MODEL", "")
        if not model:
            raise ValueError("Model is required. Set INPUT_MODEL.")

        # Parse repository info based on provider
        repo_owner = ""
        repo_name = ""
        pr_number = 0

        if provider == ProviderType.GITHUB:
            repo_owner, repo_name = _parse_github_repo()
            pr_number = _parse_github_pr_number()

        elif provider == ProviderType.AZURE_DEVOPS:
            pr_number = _parse_azure_pr_number()

        elif provider == ProviderType.GITLAB:
            pr_number = _parse_gitlab_mr_number()

        elif provider == ProviderType.BITBUCKET:
            pr_number = _parse_bitbucket_pr_number()

        min_severity = os.environ.get("INPUT_MIN_SEVERITY", "warning").lower()
        if min_severity not in ("error", "warning", "info"):
            min_severity = "warning"

        # Context settings
        context_enabled = os.environ.get("INPUT_CONTEXT_ENABLED", "true").lower() == "true"
        context_max_tokens = parse_int_env("INPUT_CONTEXT_MAX_TOKENS", 5000)
        max_comments = parse_int_env("INPUT_MAX_COMMENTS", 10)
        resolve_outdated = os.environ.get("INPUT_RESOLVE_OUTDATED", "true").lower() == "true"

        return cls(
            token=token,
            provider=provider,
            model=model,
            agent_spec_path=os.environ.get("INPUT_AGENT_SPEC_PATH", ".github/ai-reviewer.md"),
            post_summary=os.environ.get("INPUT_POST_SUMMARY", "true").lower() == "true",
            post_inline_comments=os.environ.get("INPUT_POST_INLINE_COMMENTS", "true").lower()
            == "true",
            max_comments=max_comments,
            min_severity=min_severity,
            resolve_outdated=resolve_outdated,
            context_enabled=context_enabled,
            context_max_tokens=context_max_tokens,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            # Azure DevOps
            azure_org_url=os.environ.get("AZURE_DEVOPS_ORG")
            or os.environ.get("SYSTEM_COLLECTIONURI"),
            azure_project=os.environ.get("AZURE_DEVOPS_PROJECT")
            or os.environ.get("SYSTEM_TEAMPROJECT"),
            azure_repository=os.environ.get("AZURE_DEVOPS_REPOSITORY")
            or os.environ.get("BUILD_REPOSITORY_NAME"),
            # GitLab
            gitlab_url=os.environ.get("GITLAB_URL") or os.environ.get("CI_SERVER_URL"),
            gitlab_project=os.environ.get("GITLAB_PROJECT") or os.environ.get("CI_PROJECT_PATH"),
            # Bitbucket
            bitbucket_workspace=os.environ.get("BITBUCKET_WORKSPACE"),
            bitbucket_repo_slug=os.environ.get("BITBUCKET_REPO_SLUG"),
            bitbucket_username=os.environ.get("BITBUCKET_USERNAME"),
            # Static analysis
            static_analysis_file=os.environ.get("INPUT_STATIC_ANALYSIS_FILE") or None,
        )


def _parse_github_repo() -> tuple[str, str]:
    """Parse GitHub repository owner and name."""
    github_repository = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in github_repository:
        raise ValueError("GITHUB_REPOSITORY must be in format 'owner/repo'")
    return github_repository.split("/", 1)


def _parse_github_pr_number() -> int:
    """Parse GitHub PR number."""
    pr_number_str = os.environ.get("PR_NUMBER", "")
    if not pr_number_str:
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
        return int(pr_number_str)
    except ValueError as e:
        raise ValueError(f"Invalid PR number format: '{pr_number_str}' is not a number") from e


def _parse_azure_pr_number() -> int:
    """Parse Azure DevOps PR number."""
    pr_number_str = os.environ.get("SYSTEM_PULLREQUESTID", "")
    if not pr_number_str:
        pr_number_str = os.environ.get("PR_NUMBER", "")

    if not pr_number_str:
        raise ValueError(
            "Could not determine PR number. "
            "Set SYSTEM_PULLREQUESTID or PR_NUMBER env var."
        )

    try:
        return int(pr_number_str)
    except ValueError as e:
        raise ValueError(f"Invalid PR number format: '{pr_number_str}' is not a number") from e


def _parse_gitlab_mr_number() -> int:
    """Parse GitLab MR number."""
    mr_number_str = os.environ.get("CI_MERGE_REQUEST_IID", "")
    if not mr_number_str:
        mr_number_str = os.environ.get("PR_NUMBER", "")

    if not mr_number_str:
        raise ValueError(
            "Could not determine MR number. "
            "Set CI_MERGE_REQUEST_IID or PR_NUMBER env var."
        )

    try:
        return int(mr_number_str)
    except ValueError as e:
        raise ValueError(f"Invalid MR number format: '{mr_number_str}' is not a number") from e


def _parse_bitbucket_pr_number() -> int:
    """Parse Bitbucket PR number."""
    pr_number_str = os.environ.get("BITBUCKET_PR_ID", "")
    if not pr_number_str:
        pr_number_str = os.environ.get("PR_NUMBER", "")

    if not pr_number_str:
        raise ValueError(
            "Could not determine PR number. "
            "Set BITBUCKET_PR_ID or PR_NUMBER env var."
        )

    try:
        return int(pr_number_str)
    except ValueError as e:
        raise ValueError(f"Invalid PR number format: '{pr_number_str}' is not a number") from e
