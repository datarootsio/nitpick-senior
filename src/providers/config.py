"""Provider configuration dataclasses."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubConfig:
    """Configuration for GitHub provider."""

    repo_owner: str
    repo_name: str


@dataclass(frozen=True)
class AzureDevOpsConfig:
    """Configuration for Azure DevOps provider."""

    org_url: str
    project: str
    repository: str


@dataclass(frozen=True)
class GitLabConfig:
    """Configuration for GitLab provider."""

    url: str
    project: str


@dataclass(frozen=True)
class BitbucketConfig:
    """Configuration for Bitbucket provider."""

    workspace: str
    repo_slug: str
    username: str
