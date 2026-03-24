"""Git provider abstraction layer."""

from .factory import ProviderType, create_provider, detect_provider
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
    "detect_provider",
]
