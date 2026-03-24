"""Git provider abstraction layer."""

from .config import AzureDevOpsConfig, BitbucketConfig, GitHubConfig, GitLabConfig
from .factory import (
    ProviderType,
    create_provider,
    create_provider_from_config,
    detect_provider,
)
from .protocol import (
    GitProvider,
    IssueCommentInfo,
    PullRequestInfo,
    ReviewCommentInfo,
)

__all__ = [
    "GitProvider",
    "PullRequestInfo",
    "ReviewCommentInfo",
    "IssueCommentInfo",
    "ProviderType",
    "create_provider",
    "create_provider_from_config",
    "detect_provider",
    # Config objects
    "GitHubConfig",
    "AzureDevOpsConfig",
    "GitLabConfig",
    "BitbucketConfig",
]
