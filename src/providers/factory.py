"""Provider factory for creating Git providers."""

import logging
import os
from enum import StrEnum
from typing import TYPE_CHECKING

from src.utils.env import resolve_token

from .config import AzureDevOpsConfig, BitbucketConfig, GitHubConfig, GitLabConfig

if TYPE_CHECKING:
    from .protocol import GitProvider

ProviderConfig = GitHubConfig | AzureDevOpsConfig | GitLabConfig | BitbucketConfig

logger = logging.getLogger(__name__)


class ProviderType(StrEnum):
    """Supported Git provider types."""

    GITHUB = "github"
    AZURE_DEVOPS = "azure_devops"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


def detect_provider() -> ProviderType:
    """Auto-detect the Git provider from environment variables.

    Detection order:
    1. AZURE_DEVOPS_ORG or SYSTEM_TEAMPROJECT → Azure DevOps
    2. CI_SERVER_URL or GITLAB_URL → GitLab
    3. BITBUCKET_WORKSPACE → Bitbucket
    4. Default → GitHub

    Returns:
        Detected provider type
    """
    # Azure DevOps
    if os.environ.get("AZURE_DEVOPS_ORG") or os.environ.get("SYSTEM_TEAMPROJECT"):
        logger.info("Detected Azure DevOps environment")
        return ProviderType.AZURE_DEVOPS

    # GitLab
    if os.environ.get("CI_SERVER_URL") or os.environ.get("GITLAB_URL"):
        logger.info("Detected GitLab environment")
        return ProviderType.GITLAB

    # Bitbucket
    if os.environ.get("BITBUCKET_WORKSPACE"):
        logger.info("Detected Bitbucket environment")
        return ProviderType.BITBUCKET

    # Default to GitHub
    logger.info("Defaulting to GitHub provider")
    return ProviderType.GITHUB


def create_provider(
    provider_type: ProviderType | str | None = None,
    token: str | None = None,
    # GitHub-specific
    repo_owner: str | None = None,
    repo_name: str | None = None,
    # Azure DevOps-specific
    azure_org_url: str | None = None,
    azure_project: str | None = None,
    azure_repository: str | None = None,
    # GitLab-specific
    gitlab_url: str | None = None,
    gitlab_project: str | None = None,
    # Bitbucket-specific
    bitbucket_workspace: str | None = None,
    bitbucket_repo_slug: str | None = None,
    bitbucket_username: str | None = None,
) -> "GitProvider":
    """Create a Git provider instance.

    Args:
        provider_type: Provider type (auto-detected if not specified)
        token: Authentication token
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name
        azure_org_url: Azure DevOps organization URL
        azure_project: Azure DevOps project name
        azure_repository: Azure DevOps repository name
        gitlab_url: GitLab instance URL
        gitlab_project: GitLab project path
        bitbucket_workspace: Bitbucket workspace
        bitbucket_repo_slug: Bitbucket repository slug
        bitbucket_username: Bitbucket username

    Returns:
        Configured GitProvider instance
    """
    # Determine provider type
    if provider_type is None:
        provider_type = detect_provider()
    elif isinstance(provider_type, str):
        provider_type = ProviderType(provider_type)

    # Get token from env if not provided
    if not token:
        token = resolve_token()

    if not token:
        raise ValueError("Authentication token is required")

    if provider_type == ProviderType.GITHUB:
        from .github import GitHubProvider

        if not repo_owner or not repo_name:
            # Try to get from environment
            github_repository = os.environ.get("GITHUB_REPOSITORY", "")
            if "/" in github_repository:
                repo_owner, repo_name = github_repository.split("/", 1)
            else:
                raise ValueError(
                    "GitHub requires repo_owner and repo_name, "
                    "or GITHUB_REPOSITORY env var"
                )

        return GitHubProvider(
            token=token,
            repo_owner=repo_owner,
            repo_name=repo_name,
        )

    elif provider_type == ProviderType.AZURE_DEVOPS:
        from .azure_devops import AzureDevOpsProvider

        org_url = (
            azure_org_url
            or os.environ.get("AZURE_DEVOPS_ORG")
            or os.environ.get("SYSTEM_COLLECTIONURI", "")
        )
        project = (
            azure_project
            or os.environ.get("AZURE_DEVOPS_PROJECT")
            or os.environ.get("SYSTEM_TEAMPROJECT", "")
        )
        repository = (
            azure_repository
            or os.environ.get("AZURE_DEVOPS_REPOSITORY")
            or os.environ.get("BUILD_REPOSITORY_NAME", "")
        )

        if not org_url or not project or not repository:
            raise ValueError(
                "Azure DevOps requires org_url, project, and repository. "
                "Set AZURE_DEVOPS_ORG, AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_REPOSITORY "
                "or SYSTEM_COLLECTIONURI, SYSTEM_TEAMPROJECT, BUILD_REPOSITORY_NAME"
            )

        return AzureDevOpsProvider(
            token=token,
            org_url=org_url,
            project=project,
            repository=repository,
        )

    elif provider_type == ProviderType.GITLAB:
        from .gitlab import GitLabProvider

        url = gitlab_url or os.environ.get("GITLAB_URL") or os.environ.get(
            "CI_SERVER_URL", "https://gitlab.com"
        )
        project = (
            gitlab_project
            or os.environ.get("GITLAB_PROJECT")
            or os.environ.get("CI_PROJECT_PATH", "")
        )

        if not project:
            raise ValueError(
                "GitLab requires project path. "
                "Set GITLAB_PROJECT or CI_PROJECT_PATH"
            )

        return GitLabProvider(
            token=token,
            project_path=project,
            gitlab_url=url,
        )

    elif provider_type == ProviderType.BITBUCKET:
        from .bitbucket import BitbucketProvider

        workspace = bitbucket_workspace or os.environ.get("BITBUCKET_WORKSPACE", "")
        repo_slug = bitbucket_repo_slug or os.environ.get("BITBUCKET_REPO_SLUG", "")
        username = bitbucket_username or os.environ.get("BITBUCKET_USERNAME", "")

        if not workspace or not repo_slug or not username:
            raise ValueError(
                "Bitbucket requires workspace, repo_slug, and username. "
                "Set BITBUCKET_WORKSPACE, BITBUCKET_REPO_SLUG, BITBUCKET_USERNAME"
            )

        return BitbucketProvider(
            username=username,
            app_password=token,
            workspace=workspace,
            repo_slug=repo_slug,
        )

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def create_provider_from_config(
    config: ProviderConfig,
    token: str | None = None,
) -> "GitProvider":
    """Create a Git provider instance from a config object.

    This is a cleaner alternative to create_provider() with fewer parameters.

    Args:
        config: Provider-specific configuration object
        token: Authentication token (resolved from env if not provided)

    Returns:
        Configured GitProvider instance

    Example:
        >>> config = GitHubConfig(repo_owner="owner", repo_name="repo")
        >>> provider = create_provider_from_config(config, token="ghp_xxx")
    """
    if not token:
        token = resolve_token()
    if not token:
        raise ValueError("Authentication token is required")

    if isinstance(config, GitHubConfig):
        from .github import GitHubProvider

        return GitHubProvider(
            token=token,
            repo_owner=config.repo_owner,
            repo_name=config.repo_name,
        )

    elif isinstance(config, AzureDevOpsConfig):
        from .azure_devops import AzureDevOpsProvider

        return AzureDevOpsProvider(
            token=token,
            org_url=config.org_url,
            project=config.project,
            repository=config.repository,
        )

    elif isinstance(config, GitLabConfig):
        from .gitlab import GitLabProvider

        return GitLabProvider(
            token=token,
            project_path=config.project,
            gitlab_url=config.url,
        )

    elif isinstance(config, BitbucketConfig):
        from .bitbucket import BitbucketProvider

        return BitbucketProvider(
            username=config.username,
            app_password=token,
            workspace=config.workspace,
            repo_slug=config.repo_slug,
        )

    else:
        raise ValueError(f"Unknown config type: {type(config)}")
